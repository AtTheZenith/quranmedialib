"""Verse range workflow for processing ranges of verses.

This module provides the VerseRangeWorkflow class, which handles rendering multiple
verses in sequence, supporting optional translation separation and batch annotation.
"""

from __future__ import annotations

import dataclasses
import functools
import gc
import logging
import os
import re
from pathlib import Path
from typing import Callable, Iterator

from PIL import Image

from quranmedialib.config import (
    DEFAULT_PROCESS_LIMIT_MB,
    MEMORY_FLUSH_THRESHOLD_RATIO,
)
from quranmedialib.database_manager import DatabaseManager
from quranmedialib.exceptions import ValidationError
from quranmedialib.modules.annotation import annotate_words
from quranmedialib.modules.frame import Frame
from quranmedialib.modules.layout_engine import LayoutGuide
from quranmedialib.modules.sidecar import build_sidecar, serialize_sidecar
from quranmedialib.modules.timage import LazyTranslationImages, _render_timage
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.vimage import VImage
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.presets import arabic_vertical_alignment, build_layout_guide, translation_placement
from quranmedialib.types import (
    FrameConfig,
    TextConfig,
    VerseConfig,
    WordConfig,
    WordItem,
    _ensure_within_working_dir,
)
from quranmedialib.utils.io import async_image_saver
from quranmedialib.utils.memory import (
    clear_rendering_caches,
    get_current_rss_mb,
)
from quranmedialib.utils.parallel import ExecutionMode, ParallelRenderer, worker_heartbeat
from quranmedialib.workflows.base import BaseWorkflow

type OutputItem = str | tuple[str, tuple[int, int], bytes] | Image.Image
logger = logging.getLogger(__name__)

# Allowed characters in output filename prefixes. Blocks path separators so a
# hostile prefix cannot escape output_dir (which is the only path boundary
# enforced by the workflow).
_FILENAME_PREFIX_RE = re.compile(r"[^A-Za-z0-9_\-\.]+")


def _sanitize_filename_prefix(prefix: str) -> str:
    """Return a filesystem-safe output filename prefix.

    Replaces any character that is not alphanumeric, underscore, hyphen or
    dot, then strips leading/trailing dots. This neutralizes path traversal
    (``..``, separators) in a single pass.

    Args:
        prefix: The raw user-supplied prefix.

    Returns:
        The sanitized prefix.
    """
    cleaned = _FILENAME_PREFIX_RE.sub("_", prefix).strip(".")
    return cleaned or "output"


def _bytes_mode_max_batch(chunk: int, frame_cfg: FrameConfig) -> int:
    """Max verses per batch in bytes mode to stay under per-process RSS limit.

    Each page serializes to frame_width * frame_height * 4 bytes (RGBA).
    Assume worst-case 3 pages per verse. Target 80% of per-process limit
    to leave headroom for base Python + caches.

    Args:
        chunk: Natural chunk size (ceil(tasks / workers)).
        frame_cfg: Frame dimensions for page byte calculation.

    Returns:
        Safe batch size for bytes mode.
    """
    frame_bytes = frame_cfg.max_width * frame_cfg.image_height * 4
    budget = 0.8 * DEFAULT_PROCESS_LIMIT_MB * 1024 * 1024
    max_verses = max(1, int(budget / (frame_bytes * 3)))
    return min(chunk, max_verses)


__all__ = ["VerseRangeWorkflow"]


class VerseRangeWorkflow(BaseWorkflow):
    """Workflow for processing a range of verses.

    Handles data retrieval, image generation, and layout orchestration for multiple
    verses. Supports 'combined' and 'separate' translation rendering modes.
    """

    def get_iterator(
        self,
        surah: int,
        translations: list[list[str]],
        start_ayah: int = 1,
        end_ayah: int | None = None,
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """Processes a range of verses and yields lists of generated images (pages).

        Args:
            surah: Surah number (1-114).
            translations: Nested list of translation texts [verse_index][page_index].
            start_ayah: Starting verse number (1-indexed).
            end_ayah: Ending verse number (inclusive). If None, equals start_ayah.
            **kwargs:
                - annotate: bool (default: True) - Whether to annotate words.
                - separate_translations: bool (default: False) - Separate translation pages.
                - parallel: bool (default: True) - Parallel processing for multi-verse ranges.
                - output_dir: Optional path to save images directly.
                - filename_prefix: Prefix for output filenames.
                - emit_sidecar: bool (default: False) - Write a spatial sidecar JSON
                  beside each PNG (requires ``output_dir``).

        Yields:
            list[Image.Image]: List of page images for each verse in the range.

        Raises:
            ValidationError: If range is invalid.
        """
        surah = self._validate_surah(surah)
        if end_ayah is None:
            end_ayah = start_ayah

        self._validate_ayah(start_ayah)
        self._validate_ayah(end_ayah)

        if start_ayah > end_ayah:
            raise ValidationError(
                f"Invalid verse range: start_ayah ({start_ayah}) cannot be greater than end_ayah ({end_ayah})."
            )

        return self._process_range(
            surah=surah,
            start_verse=start_ayah,
            end_verse=end_ayah,
            translations=translations,
            annotate=kwargs.get("annotate", True),
            separate_translations=kwargs.get("separate_translations", False),
            parallel=kwargs.get("parallel", True),
            output_dir=kwargs.get("output_dir"),
            filename_prefix=kwargs.get("filename_prefix", f"surah_{surah:03d}"),
            emit_sidecar=kwargs.get("emit_sidecar", False),
        )

    def _process_range(
        self,
        surah: int,
        start_verse: int,
        end_verse: int,
        translations: list[list[str]],
        annotate: bool = True,
        separate_translations: bool = False,
        parallel: bool = True,
        **kwargs,
    ) -> Iterator[list[Image.Image] | list[str]]:
        """Internal iterator implementation for processing a verse range.

        If output_dir is provided, yields lists of paths. Otherwise yields lists of images.
        """
        output_dir = kwargs.get("output_dir")
        if output_dir:
            _ensure_within_working_dir(Path(output_dir))

        emit_sidecar = kwargs.get("emit_sidecar", False)
        if emit_sidecar and not output_dir:
            raise ValidationError("emit_sidecar=True requires output_dir")

        filename_prefix = kwargs.get("filename_prefix", f"surah_{surah:03d}")
        filename_prefix = _sanitize_filename_prefix(str(filename_prefix))
        total_verses = end_verse - start_verse + 1

        guide = build_layout_guide(
            self.frame_cfg.aspect_ratio,
            self.frame_cfg.max_width,
            self.frame_cfg.image_height,
            self.frame_cfg.mode,
        )

        if parallel and total_verses > 1:
            renderer = ParallelRenderer(mode=ExecutionMode.PROCESS)
            tasks = [(ayah, translations[i]) for i, ayah in enumerate(range(start_verse, end_verse + 1))]

            worker_fn = functools.partial(
                _render_verse_worker,
                surah=surah,
                frame_cfg=self.frame_cfg,
                guide=guide,
                text_cfg=self.text_cfg,
                word_cfg=self.word_cfg,
                verse_cfg=self.verse_cfg,
                annotate=annotate,
                separate_translations=separate_translations,
                output_dir=output_dir,
                filename_prefix=filename_prefix,
                emit_sidecar=emit_sidecar,
            )

            # Each batch = natural chunk (ceil(tasks/workers)) for even distribution.
            chunk = max(1, (len(tasks) + renderer.max_workers - 1) // renderer.max_workers)
            if output_dir:
                max_batch = min(chunk, 20)
            else:
                max_batch = _bytes_mode_max_batch(chunk, self.frame_cfg)
            for result in renderer.map_batches(worker_fn, tasks, max_batch_size=max_batch):
                if output_dir:
                    yield result
                else:
                    # result is list of byte-data tuples
                    yield [Image.frombytes(m, s, d) for m, s, d in result]
        else:
            # OPTIM: Direct rendering without IPC byte overhead
            task_list = [(ayah, translations[i]) for i, ayah in enumerate(range(start_verse, end_verse + 1))]
            yield from _render_verse_worker(
                task_list,
                surah,
                self.frame_cfg,
                guide,
                self.text_cfg,
                self.word_cfg,
                self.verse_cfg,
                annotate,
                separate_translations,
                output_dir,
                filename_prefix,
                use_bytes=False,
                emit_sidecar=emit_sidecar,
            )


def _fetch_worker_data(surah: int, annotate: bool) -> tuple[dict[int, str], dict[int, list[str]]]:
    """Fetch and map surah data for the worker."""
    db = DatabaseManager()
    arabic_verses = db.get_verses_from_surah(surah)
    all_wbw = db.get_wbw_grouped_by_verse(surah) if annotate else {}
    arabic_map = {i + 1: txt for i, txt in enumerate(arabic_verses)}
    return arabic_map, all_wbw


def _build_wbw_index(wbw_list: list[str]) -> dict[int, str]:
    """Build a WordIndex-keyed map of word-by-word translations.

    wbw translations are 1-based per-word strings from the database; the map
    keys match the ``WordItem.index`` values set by ``_generate_word_items``.

    Args:
        wbw_list: Per-word wbw translation strings for one verse.

    Returns:
        dict[int, str]: Map of word index (1-based) to its wbw translation.
    """
    return {i + 1: wbw for i, wbw in enumerate(wbw_list)}


def _generate_word_items(
    verse_text: str,
    ayah: int,
    surah: int,
    word_cfg: WordConfig,
    annotate: bool,
    all_wbw: dict[int, list[str]],
) -> list[WordItem]:
    """Generate the list of WordItems for a verse, including annotations and verse number."""
    verse_words = verse_text.split()
    word_images = [get_wimage(word, word_cfg) for word in verse_words]

    if annotate:
        wbw_translations = all_wbw.get(ayah, [])
        annotated_images, annotated_text, batch_map = annotate_words(
            images=word_images,
            surah=surah,
            ayah=ayah,
            start=1,
            word_config=word_cfg,
            wbw_translations=wbw_translations,
            texts=verse_words,
            return_batch_map=True,
        )
        # Each output image carries the verse-relative start index of the words
        # it covers (1 for a single word; the batch start for a combined block).
        word_items = [
            WordItem(image=img, text=txt, index=batch_start)
            for (img, txt), (batch_start, _count) in zip(zip(annotated_images, annotated_text), batch_map)
        ]
    else:
        word_items = [
            WordItem(image=img, text=txt, index=idx)
            for idx, (img, txt) in enumerate(zip(word_images, verse_words), start=1)
        ]

    vn_img = verse_number(ayah, word_cfg)
    word_items.append(WordItem(image=vn_img, text="", class_type="verse_number"))

    return word_items


def _render_pages(
    word_items: list[WordItem],
    verse_translations: list[str],
    frame_cfg: FrameConfig,
    guide: LayoutGuide,
    word_cfg: WordConfig,
    verse_cfg: VerseConfig,
    text_cfg: TextConfig,
    separate_translations: bool,
    emit_sidecar: bool = False,
    surah: int | None = None,
    ayah: int | None = None,
    wbw_by_index: dict[int, str] | None = None,
) -> list[Image.Image] | list[tuple[Image.Image, dict]]:
    """Render the verse pages using resolved layout guide.

    When ``emit_sidecar`` is True, each page is returned as a
    ``(page_image, sidecar_dict)`` tuple instead of a bare page image. The
    sidecar captures the word geometry via the VImage ``geometry_sink`` and the
    translation paragraph via ``_render_timage`` + ``translation_placement``.

    Args:
        word_items: The verse words to render.
        verse_translations: Translation texts, one per page.
        frame_cfg: Canvas configuration.
        guide: Resolved layout positions.
        word_cfg: Word rendering configuration.
        verse_cfg: Verse layout configuration.
        text_cfg: Translation text configuration.
        separate_translations: Render translations on separate pages.
        emit_sidecar: Whether to collect sidecar geometry alongside pages.
        surah: Surah number, required when ``emit_sidecar``.
        ayah: Ayah number, required when ``emit_sidecar``.
        wbw_by_index: Map of word index to word-by-word translation, joined at
            emission. Required for annotated sidecars.

    Returns:
        list[Image.Image] | list[tuple[Image.Image, dict]]: The rendered pages,
            or (page_image, sidecar) pairs when ``emit_sidecar``.
    """
    trans_images = LazyTranslationImages(verse_translations, text_cfg)

    frame_w = frame_cfg.max_width
    frame_h = frame_cfg.image_height
    bg = frame_cfg.background_color

    def _sidecar(
        page_num: int,
        rows: list[tuple[list[WordItem], int, int]],
        translation_geo: dict | None,
        geometry: list[tuple[WordItem, int, int]],
    ) -> dict:
        """Build the sidecar for one rendered page."""
        assert surah is not None and ayah is not None
        return build_sidecar(
            surah=surah,
            ayah=ayah,
            page=page_num,
            dimensions=(frame_w, frame_h),
            rows=rows,
            translation_geo=translation_geo,
            word_items_with_geometry=geometry,
            wbw_by_index=wbw_by_index,
        )

    if not separate_translations:
        vimage = VImage(word_items, verse_cfg, guide.arabic.width)
        pages = []
        page_index = 0
        current_index = 0
        total_items = len(word_items)

        while current_index < total_items:
            current_rows, items_consumed = vimage.get_page_chunk(current_index, verse_cfg.max_rows_per_page)
            frame_obj = Frame(frame_w, frame_h, bg)

            geometry: list[tuple[WordItem, int, int]] = []

            def _geometry_sink(item: WordItem, x: int, y: int) -> None:
                geometry.append((item, x, y))

            frame_obj.layer_at(
                vimage,
                guide.arabic,
                word_config=word_cfg,
                rows_to_render=current_rows,
                center=True,
                content_height=guide.arabic.height,
                vertical_alignment=arabic_vertical_alignment(frame_cfg.aspect_ratio, frame_cfg.mode),
                **({"geometry_sink": _geometry_sink} if emit_sidecar else {}),
            )

            translation_geo = None
            if trans_images and page_index < len(trans_images):
                if emit_sidecar:
                    t_image, exceeded_bounds = _render_timage(verse_translations[page_index], text_cfg)
                else:
                    t_image, exceeded_bounds = trans_images[page_index], False
                if t_image:
                    place_rect, keep_bottom = translation_placement(
                        guide.translation,
                        t_image.width,
                        t_image.height,
                        frame_cfg.aspect_ratio,
                        frame_cfg.mode,
                    )
                    frame_obj.layer_at(
                        t_image,
                        place_rect,
                        text_color=text_cfg.color,
                        keep_bottom=keep_bottom,
                    )
                    if emit_sidecar:
                        translation_geo = {
                            "bbox": {"x": 0, "y": 0, "w": t_image.width, "h": t_image.height},
                            "position": {"x": place_rect.left, "y": place_rect.top},
                            "exceeded_bounds": exceeded_bounds,
                        }

            page_image = frame_obj.render()
            if emit_sidecar:
                pages.append(
                    (page_image, _sidecar(page_index + 1, current_rows, translation_geo, geometry))
                )
            else:
                pages.append(page_image)
            current_index += items_consumed
            page_index += 1
        return pages

    modified_verse_cfg = dataclasses.replace(verse_cfg, max_rows_per_page=2)
    vimage = VImage(word_items, modified_verse_cfg, guide.arabic.width)
    pages = []
    current_index = 0
    total_items = len(word_items)
    page_index = 0

    while current_index < total_items:
        current_rows, items_consumed = vimage.get_page_chunk(current_index, modified_verse_cfg.max_rows_per_page)
        frame_obj = Frame(frame_w, frame_h, bg)

        geometry: list[tuple[WordItem, int, int]] = []

        def _geometry_sink(item: WordItem, x: int, y: int) -> None:
            geometry.append((item, x, y))

        frame_obj.layer_at(
            vimage,
            guide.arabic,
            word_config=word_cfg,
            rows_to_render=current_rows,
            center=True,
            content_height=guide.arabic.height,
            vertical_alignment=arabic_vertical_alignment(frame_cfg.aspect_ratio, frame_cfg.mode),
            **({"geometry_sink": _geometry_sink} if emit_sidecar else {}),
        )
        page_image = frame_obj.render()
        if emit_sidecar:
            pages.append((page_image, _sidecar(page_index + 1, current_rows, None, geometry)))
        else:
            pages.append(page_image)
        current_index += items_consumed
        page_index += 1

    translation_iter: Iterator[tuple[Image.Image | None, bool]]
    if emit_sidecar:
        translation_iter = (_render_timage(text, text_cfg) for text in verse_translations)
    else:
        translation_iter = ((t, False) for t in trans_images)
    for t_img, exceeded_bounds in translation_iter:
        if not t_img:
            continue
        frame_obj = Frame(frame_w, frame_h, bg)
        place_rect, keep_bottom = translation_placement(
            guide.translation,
            t_img.width,
            t_img.height,
            frame_cfg.aspect_ratio,
            frame_cfg.mode,
        )
        frame_obj.layer_at(
            t_img,
            place_rect,
            text_color=text_cfg.color,
            keep_bottom=keep_bottom,
        )
        page_image = frame_obj.render()
        if emit_sidecar:
            translation_geo = {
                "bbox": {"x": 0, "y": 0, "w": t_img.width, "h": t_img.height},
                "position": {"x": place_rect.left, "y": place_rect.top},
                "exceeded_bounds": exceeded_bounds,
            }
            pages.append((page_image, _sidecar(page_index + 1, [], translation_geo, [])))
            page_index += 1
        else:
            pages.append(page_image)
    return pages


def _handle_output(
    pages: list[Image.Image] | list[tuple[Image.Image, dict]],
    ayah: int,
    output_dir: str | None,
    filename_prefix: str,
    save_fn: Callable[[Image.Image, str, str, int], None],
    use_bytes: bool,
    emit_sidecar: bool = False,
) -> list[OutputItem]:
    """Save pages to disk or convert to bytes for IPC.

    When ``emit_sidecar`` is True, ``pages`` holds ``(page_image, sidecar)``
    tuples and each PNG is written alongside a ``{stem}.json`` sidecar via the
    saver's ``save_data``.

    Args:
        pages: Page images, or (page_image, sidecar) pairs when ``emit_sidecar``.
        ayah: Ayah number for filename construction.
        output_dir: Optional directory to save images.
        filename_prefix: Prefix for output filenames.
        save_fn: The saver callable with a ``save_data`` attribute.
        use_bytes: If True, convert images to bytes for IPC.
        emit_sidecar: Whether pages carry sidecar dicts to persist.

    Returns:
        list[OutputItem]: Paths, byte data tuples, or page images.
    """
    if output_dir:
        paths = []
        safe_prefix = _sanitize_filename_prefix(filename_prefix)
        for j, p in enumerate(pages):
            page = p[0] if emit_sidecar else p
            path = os.path.join(output_dir, f"{safe_prefix}_verse_{ayah:03d}_page_{j + 1}.png")
            save_fn(page, path, format="PNG", compress_level=1)
            if emit_sidecar:
                stem = os.path.splitext(path)[0]
                save_fn.save_data(stem + ".json", serialize_sidecar(p[1]))
            paths.append(path)
        return paths
    elif use_bytes:
        pages_flat = [p[0] if emit_sidecar else p for p in pages]
        return [(p.mode, p.size, p.tobytes()) for p in pages_flat]
    else:
        return [p[0] if emit_sidecar else p for p in pages]


def _render_verse_worker(
    verse_data: list[tuple[int, list[str]]],
    surah: int,
    frame_cfg: FrameConfig,
    guide: LayoutGuide,
    text_cfg: TextConfig,
    word_cfg: WordConfig,
    verse_cfg: VerseConfig,
    annotate: bool,
    separate_translations: bool,
    output_dir: str | None,
    filename_prefix: str,
    use_bytes: bool = True,
    emit_sidecar: bool = False,
) -> list[list[OutputItem]]:
    """Worker function for rendering a batch of verses. Returns pickle-safe data.

    Args:
        verse_data: List of (ayah_number, translation_list) tuples.
        surah: Surah number.
        frame_cfg: Canvas configuration.
        guide: Resolved layout positions.
        text_cfg, word_cfg, verse_cfg: Configurations.
        annotate: Whether to annotate words.
        separate_translations: Separate translation pages.
        output_dir: Optional directory to save images.
        filename_prefix: Prefix for output filenames.
        use_bytes: If True, convert images to bytes for IPC.
        emit_sidecar: Whether to persist a spatial sidecar JSON beside each PNG.

    Returns:
        list[list[OutputItem]]: List of pages (paths or byte data tuples) for each verse.
    """
    if not verse_data:
        return []

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Initialize data for this batch
    arabic_map, all_wbw = _fetch_worker_data(surah, annotate)

    batch_results = []
    flush_trigger = DEFAULT_PROCESS_LIMIT_MB * MEMORY_FLUSH_THRESHOLD_RATIO

    with async_image_saver() as save:
        for i, (ayah, verse_translations) in enumerate(verse_data):
            # Throttled memory check and heartbeat (every 10 verses)
            if i % 10 == 0:
                if get_current_rss_mb() > flush_trigger:
                    clear_rendering_caches()
                    gc.collect()
                worker_heartbeat()

            verse_text = arabic_map.get(ayah, "")
            if not verse_text:
                continue

            word_items = _generate_word_items(verse_text, ayah, surah, word_cfg, annotate, all_wbw)
            wbw_by_index = _build_wbw_index(all_wbw.get(ayah, [])) if emit_sidecar and annotate else None
            pages = _render_pages(
                word_items,
                verse_translations,
                frame_cfg,
                guide,
                word_cfg,
                verse_cfg,
                text_cfg,
                separate_translations,
                emit_sidecar=emit_sidecar,
                surah=surah,
                ayah=ayah,
                wbw_by_index=wbw_by_index,
            )

            result = _handle_output(
                pages, ayah, output_dir, filename_prefix, save, use_bytes, emit_sidecar=emit_sidecar
            )
            batch_results.append(result)

    return batch_results
