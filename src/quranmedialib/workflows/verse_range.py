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
from quranmedialib.modules.timage import LazyTranslationImages
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.vimage import VImage
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.presets import build_layout_guide
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

        filename_prefix = kwargs.get("filename_prefix", f"surah_{surah:03d}")
        total_verses = end_verse - start_verse + 1

        guide = build_layout_guide(
            self.frame_cfg.aspect_ratio,
            self.frame_cfg.max_width,
            self.frame_cfg.image_height,
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
            )


def _fetch_worker_data(surah: int, annotate: bool) -> tuple[dict[int, str], dict[int, list[str]]]:
    """Fetch and map surah data for the worker."""
    db = DatabaseManager()
    arabic_verses = db.get_verses_from_surah(surah)
    all_wbw = db.get_wbw_grouped_by_verse(surah) if annotate else {}
    arabic_map = {i + 1: txt for i, txt in enumerate(arabic_verses)}
    return arabic_map, all_wbw


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
        annotated_images, annotated_text = annotate_words(
            images=word_images,
            surah=surah,
            ayah=ayah,
            start=1,
            word_config=word_cfg,
            wbw_translations=wbw_translations,
            texts=verse_words,
        )
    else:
        annotated_images, annotated_text = word_images, verse_words

    vn_img = verse_number(ayah, word_cfg)
    annotated_images.append(vn_img)
    annotated_text.append("")

    return [WordItem(image=img, text=txt) for img, txt in zip(annotated_images, annotated_text)]


def _render_pages(
    word_items: list[WordItem],
    verse_translations: list[str],
    frame_cfg: FrameConfig,
    guide: LayoutGuide,
    word_cfg: WordConfig,
    verse_cfg: VerseConfig,
    text_cfg: TextConfig,
    separate_translations: bool,
) -> list[Image.Image]:
    """Render the verse pages using resolved layout guide."""
    trans_images = LazyTranslationImages(verse_translations, text_cfg)

    frame_w = frame_cfg.max_width
    frame_h = frame_cfg.image_height
    bg = frame_cfg.background_color

    if not separate_translations:
        vimage = VImage(word_items, verse_cfg, guide.arabic.width)
        pages = []
        page_index = 0
        current_index = 0
        total_items = len(word_items)

        while current_index < total_items:
            current_rows, items_consumed = vimage.get_page_chunk(current_index, verse_cfg.max_rows_per_page)
            frame_obj = Frame(frame_w, frame_h, bg)

            frame_obj.layer_at(
                vimage,
                guide.arabic,
                word_config=word_cfg,
                rows_to_render=current_rows,
                center=True,
                content_height=guide.arabic.height,
            )

            if trans_images and page_index < len(trans_images):
                if t_image := trans_images[page_index]:
                    frame_obj.layer_at(
                        t_image,
                        guide.translation,
                        text_color=text_cfg.color,
                        keep_bottom=True,
                    )

            pages.append(frame_obj.render())
            current_index += items_consumed
            page_index += 1
        return pages

    modified_verse_cfg = dataclasses.replace(verse_cfg, max_rows_per_page=2)
    vimage = VImage(word_items, modified_verse_cfg, guide.arabic.width)
    pages = []
    current_index = 0
    total_items = len(word_items)

    while current_index < total_items:
        current_rows, items_consumed = vimage.get_page_chunk(current_index, modified_verse_cfg.max_rows_per_page)
        frame_obj = Frame(frame_w, frame_h, bg)

        frame_obj.layer_at(
            vimage,
            guide.arabic,
            word_config=word_cfg,
            rows_to_render=current_rows,
            center=True,
            content_height=guide.arabic.height,
        )
        pages.append(frame_obj.render())
        current_index += items_consumed

    for t_img in trans_images:
        if not t_img:
            continue
        frame_obj = Frame(frame_w, frame_h, bg)
        frame_obj.layer_at(
            t_img,
            guide.translation,
            text_color=text_cfg.color,
            keep_bottom=True,
        )
        pages.append(frame_obj.render())
    return pages


def _handle_output(
    pages: list[Image.Image],
    ayah: int,
    output_dir: str | None,
    filename_prefix: str,
    save_fn: Callable[[Image.Image, str, str, int], None],
    use_bytes: bool,
) -> list[OutputItem]:
    """Save pages to disk or convert to bytes for IPC."""
    if output_dir:
        paths = []
        for j, p in enumerate(pages):
            path = os.path.join(output_dir, f"{filename_prefix}_verse_{ayah:03d}_page_{j + 1}.png")
            save_fn(p, path, format="PNG", compress_level=1)
            paths.append(path)
        return paths
    elif use_bytes:
        return [(p.mode, p.size, p.tobytes()) for p in pages]
    else:
        return pages


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
            pages = _render_pages(
                word_items,
                verse_translations,
                frame_cfg,
                guide,
                word_cfg,
                verse_cfg,
                text_cfg,
                separate_translations,
            )

            result = _handle_output(pages, ayah, output_dir, filename_prefix, save, use_bytes)
            batch_results.append(result)

    return batch_results
