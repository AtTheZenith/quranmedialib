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
from typing import Any, Iterator

from PIL import Image, ImageFont

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.modules.annotation import annotate_words
from quranmedialib.modules.framer import frame
from quranmedialib.modules.timage import LazyTranslationImages
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import WordItem
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

            # Calculate Y position: use explicit offset or default to bottom-padding alignment
            if self.layout_config.timage_y_offset > 0:
                ty = self.layout_config.timage_y_offset - trans_img.height // 2
            else:
                padding_bottom = self.layout_config.padding.bottom
                ty = self.layout_config.image_height - padding_bottom - trans_img.height // 2

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
            ValueError: If start_ayah > end_ayah (reversed range) or surah/ayah out of range.
        """
        if not (1 <= surah <= 114):
            raise ValueError(f"Surah must be between 1 and 114, got {surah}")
        if end_ayah is None:
            end_ayah = start_ayah

        if not (1 <= start_ayah <= 286):
            raise ValueError(f"Ayah must be between 1 and 286, got start_ayah={start_ayah}")
        if not (1 <= end_ayah <= 286):
            raise ValueError(f"Ayah must be between 1 and 286, got end_ayah={end_ayah}")

        if start_ayah > end_ayah:
            raise ValueError(
                f"Invalid verse range: start_ayah ({start_ayah}) cannot be greater than end_ayah ({end_ayah})."
            )

        return self._process_range(
            surah=surah,
            start_verse=start_ayah,
            end_verse=end_ayah,
            translations=translations,
            annotate=kwargs.get("annotate", True),
            separate_translations=kwargs.get("separate_translations", False),
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

        Logic:
        - If parallel=True, divides the range into N batches based on CPU count.
        - Each batch is processed by a worker that fetches its own data from the DB.
        - This minimizes IPC overhead (serialization) by orders of magnitude.
        """
        output_dir = kwargs.get("output_dir")
        filename_prefix = kwargs.get("filename_prefix", f"surah_{surah:03d}")

        total_verses = end_verse - start_verse + 1

        if parallel and total_verses > 1:
            renderer = ParallelRenderer(mode=ExecutionMode.PROCESS)

            # Prepare flat list of tasks (ayah, translations)
            tasks = []
            for i, ayah in enumerate(range(start_verse, end_verse + 1)):
                tasks.append((ayah, translations[i]))

            # Inject static configurations into worker
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

            # Map in optimal batches based on hardware
            for verse_pages in renderer.map_batches(worker_fn, tasks):
                if output_dir:
                    yield verse_pages
                else:
                    yield [Image.frombytes(m, s, d) for m, s, d in verse_pages]
        else:
            # Serial execution (uses the worker function for code reuse)
            task_list = []
            for i, ayah in enumerate(range(start_verse, end_verse + 1)):
                task_list.append((ayah, translations[i]))

            for verse_pages in _render_verse_worker(
                task_list,
                surah,
                self.layout_config,
                self.text_config,
                self.word_config,
                annotate,
                separate_translations,
                output_dir,
                filename_prefix,
            ):
                if output_dir:
                    yield verse_pages
                else:
                    yield [Image.frombytes(m, s, d) for m, s, d in verse_pages]


# process-local cache for fonts to avoid redundant re-initialization in workers.
_WORKER_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _get_worker_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Retrieves a font instance from the process-local cache."""
    key = (path, size)
    if key not in _WORKER_FONT_CACHE:
        _WORKER_FONT_CACHE[key] = ImageFont.truetype(path, size)
    return _WORKER_FONT_CACHE[key]


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
) -> list[list[Any]]:
    """Worker function for rendering a batch of verses.

    Args:
        verse_data: List of (ayah_number, translation_list) tuples.
        surah: Surah number.
        layout_cfg: Layout configuration.
        text_cfg: Text configuration.
        word_cfg: Word configuration.
        annotate: Whether to annotate words.
        separate_translations: Whether to use separate pages for translations.
        output_dir: Optional directory to save images.
        filename_prefix: Prefix for output filenames.

    Returns:
        list[list[Any]]: List of pages (paths or byte data) for each verse.
    """
    if not verse_data:
        return []

    # Initialize process-local database manager
    db = DatabaseManager()

    # Determine range for fetching
    ayahs = [v[0] for v in verse_data]
    start_ayah = min(ayahs)
    end_ayah = max(ayahs)

    # Fetch data once for the batch range
    arabic_verses = db.get_verses_from_range(surah, start_ayah, end_ayah)
    # Re-index to handle non-contiguous ranges (though usually they are contiguous)
    arabic_map = {ayah: txt for ayah, txt in zip(range(start_ayah, end_ayah + 1), arabic_verses)}

    all_wbw = db.get_wbw_grouped_by_verse_range(surah, start_ayah, end_ayah) if annotate else {}

    batch_results = []

    # Pre-calculate flush trigger
    flush_trigger = DEFAULT_PROCESS_LIMIT_MB * MEMORY_FLUSH_THRESHOLD_RATIO

    # Overlap I/O and Rendering
    with async_image_saver() as save:
        for i, (ayah, verse_translations) in enumerate(verse_data):
            if get_current_rss_mb() > flush_trigger:
                clear_rendering_caches()
                gc.collect()

            worker_heartbeat()

            verse_text = arabic_map.get(ayah, "")
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
                annotated_images = word_images
                annotated_text = verse_words

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
                    ty = (
                        layout_cfg.timage_y_offset or layout_cfg.image_height - layout_cfg.padding.bottom
                    ) - t_img.height // 2
                    tx = (layout_cfg.max_width - t_img.width) // 2 + layout_cfg.timage_x_offset
                    
                    # Manual composite for separate pages (L mode handled)
                    if t_img.mode == "L":
                        canvas.paste(text_cfg.color, (tx, ty), mask=t_img)
                    else:
                        canvas.alpha_composite(t_img, (tx, ty))
                    pages.append(canvas)
            else:
                pages = list(frame(word_items, trans_images, layout_cfg, word_cfg, text_color=text_cfg.color))

            # Result handling
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                paths = []
                for j, p in enumerate(pages):
                    path = os.path.join(output_dir, f"{filename_prefix}_verse_{ayah:03d}_page_{j + 1}.png")
                    save(p, path, format="PNG", compress_level=1)
                    paths.append(path)
                batch_results.append(paths)
            else:
                batch_results.append([(p.mode, p.size, p.tobytes()) for p in pages])
                for p in pages:
                    del p

            del word_items, trans_images, pages
            if i % 10 == 0:
                gc.collect()

    return batch_results
