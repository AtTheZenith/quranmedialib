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
from typing import Any, Iterator

from PIL import Image, ImageFont

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.exceptions import ValidationError, WorkflowError
from quranmedialib.modules.annotation import annotate_words
from quranmedialib.modules.framer import frame
from quranmedialib.modules.timage import LazyTranslationImages
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import (
    HorizontalAlignment,
    VerticalAlignment,
    WordItem,
    _ensure_within_working_dir,
)
from quranmedialib.utils.io import async_image_saver
from quranmedialib.utils.memory import (
    DEFAULT_PROCESS_LIMIT_MB,
    MEMORY_FLUSH_THRESHOLD_RATIO,
    clear_rendering_caches,
    get_current_rss_mb,
)
from quranmedialib.utils.parallel import ExecutionMode, ParallelRenderer, worker_heartbeat
from quranmedialib.workflows.base import BaseWorkflow

# Logger setup
logger = logging.getLogger(__name__)

__all__ = ["VerseRangeWorkflow"]


class VerseRangeWorkflow(BaseWorkflow):
    """Workflow for processing a range of verses.

    Handles data retrieval, image generation, and layout orchestration for multiple
    verses. Supports 'combined' and 'separate' translation rendering modes.
    """

    def _render_separate_translation_pages(
        self,
        translation_images: list[Image.Image | None],
    ) -> list[Image.Image]:
        """Creates dedicated full-size pages for each translation image.

        Args:
            translation_images: List of translation images (or None for empty slots).

        Returns:
            list[Image.Image]: List of canvas images with translations centered.
        """
        pages = []
        for trans_img in translation_images:
            if not trans_img:
                continue

            canvas = Image.new(
                "RGBA",
                (self.layout_config.max_width, self.layout_config.image_height),
                (0, 0, 0, 0),
            )

            # Vertical placement
            ty = self.layout_config.padding.top + self.layout_config.timage_y_offset
            if self.layout_config.timage_vertical_align == VerticalAlignment.CENTER:
                ty = self.layout_config.padding.top + (self.layout_config.available_height - trans_img.height) // 2 + self.layout_config.timage_y_offset
            elif self.layout_config.timage_vertical_align == VerticalAlignment.BOTTOM:
                ty = self.layout_config.padding.top + self.layout_config.available_height - trans_img.height + self.layout_config.timage_y_offset

            tx = (self.layout_config.max_width - trans_img.width) // 2 + self.layout_config.timage_x_offset

            canvas.paste(trans_img, (tx, ty), mask=trans_img if trans_img.mode == "RGBA" else None)
            pages.append(canvas)

        return pages

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

        if parallel and total_verses > 1:
            renderer = ParallelRenderer(mode=ExecutionMode.PROCESS)
            tasks = [(ayah, translations[i]) for i, ayah in enumerate(range(start_verse, end_verse + 1))]

            worker_fn = functools.partial(
                _render_verse_worker,
                surah=surah,
                layout_cfg=self.layout_config,
                text_cfg=self.text_config,
                word_cfg=self.word_config,
                annotate=annotate,
                separate_translations=separate_translations,
                output_dir=output_dir,
                filename_prefix=filename_prefix,
            )

            for result in renderer.map_batches(worker_fn, tasks):
                if output_dir:
                    yield result
                else:
                    # result is list of byte-data tuples
                    yield [Image.frombytes(m, s, d) for m, s, d in result]
        else:
            # OPTIM: Direct rendering without IPC byte overhead
            task_list = [(ayah, translations[i]) for i, ayah in enumerate(range(start_verse, end_verse + 1))]
            for result in _render_verse_worker(
                task_list,
                surah,
                self.layout_config,
                self.text_config,
                self.word_config,
                annotate,
                separate_translations,
                output_dir,
                filename_prefix,
                use_bytes=False,
            ):
                yield result


def _render_verse_worker(
    verse_data: list[tuple[int, list[str]]],
    surah: int,
    layout_cfg: Any,
    text_cfg: Any,
    word_cfg: Any,
    annotate: bool,
    separate_translations: bool,
    output_dir: str | None,
    filename_prefix: str,
    use_bytes: bool = True,
) -> list[list[Any]]:
    """Worker function for rendering a batch of verses. Returns pickle-safe data.

    Args:
        verse_data: List of (ayah_number, translation_list) tuples.
        surah: Surah number.
        layout_cfg, text_cfg, word_cfg: Configurations.
        annotate: Whether to annotate words.
        separate_translations: Separate translation pages.
        output_dir: Optional directory to save images.
        filename_prefix: Prefix for output filenames.
        use_bytes: If True, convert images to bytes for IPC.

    Returns:
        list[list[Any]]: List of pages (paths or byte data tuples) for each verse.
    """
    if not verse_data:
        return []

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Initialize process-local database manager
    db = DatabaseManager()

    # Determine range for fetching
    ayahs = [v[0] for v in verse_data]
    start_ayah, end_ayah = min(ayahs), max(ayahs)

    # Fetch surah-level data once (cached in the manager instance)
    arabic_verses = db.get_verses_from_surah(surah)
    all_wbw = db.get_wbw_grouped_by_verse(surah) if annotate else {}

    # Re-index to ayah number (1-based)
    arabic_map = {i + 1: txt for i, txt in enumerate(arabic_verses)}

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

            wbw_translations = all_wbw.get(ayah, [])
            verse_words = verse_text.split()
            word_images = [get_wimage(word, word_cfg) for word in verse_words]

            if annotate:
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

            # Add verse number marker
            vn_img = verse_number(ayah, word_cfg)
            annotated_images.append(vn_img)
            annotated_text.append("")

            word_items = [WordItem(image=img, text=txt) for img, txt in zip(annotated_images, annotated_text)]
            trans_images = LazyTranslationImages(verse_translations, text_cfg)

            if separate_translations:
                arabic_word_cfg = dataclasses.replace(word_cfg, max_rows_per_page=2)
                pages = list(frame(word_items, None, layout_cfg, arabic_word_cfg))
                for t_img in trans_images:
                    if not t_img:
                        continue
                    canvas = Image.new("RGBA", (layout_cfg.max_width, layout_cfg.image_height), (0, 0, 0, 0))

                    # Vertical placement
                    ty = layout_cfg.padding.top + layout_cfg.timage_y_offset
                    if layout_cfg.timage_vertical_align == "center" or layout_cfg.timage_vertical_align == VerticalAlignment.CENTER:
                        ty = layout_cfg.padding.top + (layout_cfg.available_height - t_img.height) // 2 + layout_cfg.timage_y_offset
                    elif layout_cfg.timage_vertical_align == "bottom" or layout_cfg.timage_vertical_align == VerticalAlignment.BOTTOM:
                        ty = layout_cfg.padding.top + layout_cfg.available_height - t_img.height + layout_cfg.timage_y_offset

                    tx = (layout_cfg.max_width - t_img.width) // 2 + layout_cfg.timage_x_offset
                    
                    if t_img.mode == "L":
                        canvas.paste(text_cfg.color, (tx, ty), mask=t_img)
                    else:
                        # Ensure RGBA for alpha_composite
                        if canvas.mode != "RGBA":
                            canvas = canvas.convert("RGBA")
                        canvas.alpha_composite(t_img.convert("RGBA"), (tx, ty))
                    pages.append(canvas)
            else:
                pages = list(frame(word_items, trans_images, layout_cfg, word_cfg, text_color=text_cfg.color))

            if output_dir:
                paths = []
                for j, p in enumerate(pages):
                    path = os.path.join(output_dir, f"{filename_prefix}_verse_{ayah:03d}_page_{j + 1}.png")
                    save(p, path, format="PNG", compress_level=1)
                    paths.append(path)
                batch_results.append(paths)
            elif use_bytes:
                # Convert PIL images to picklable byte data for IPC
                batch_results.append([(p.mode, p.size, p.tobytes()) for p in pages])
            else:
                # Direct Image objects (for serial execution)
                batch_results.append(pages)

    return batch_results
