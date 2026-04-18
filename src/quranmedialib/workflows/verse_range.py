"""Verse range workflow for processing ranges of verses.

This module provides the VerseRangeWorkflow class, which handles rendering multiple
verses in sequence, supporting optional translation separation and batch annotation.
"""

from __future__ import annotations

import dataclasses
import io
import logging
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Iterator

from PIL import Image, ImageFont

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.modules.annotation import annotate_words
from quranmedialib.modules.framer import frame
from quranmedialib.modules.lazy_image import LazyTranslationImages
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import WordItem
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

        Args:
            surah: Surah number (1-114).
            start_verse: Starting verse number (1-indexed).
            end_verse: Ending verse number (inclusive).
            translations: Nested list of translation texts [verse_index][page_index].
            annotate: Whether to annotate words with word-by-word translations.
            separate_translations: If True, render translations on separate pages.
            parallel: Whether to use parallel processing for rendering.
            **kwargs:
                - output_dir: Optional path to save images directly in parallel.
                - filename_prefix: Optional prefix for saved filenames.
        """
        db = DatabaseManager()
        arabic_verses = db.get_verses_from_surah(surah)
        verse_slice = arabic_verses[start_verse - 1 : end_verse]

        # Fetch all WBW translations for the requested range to avoid DB contention in workers
        all_wbw = {}
        if annotate:
            all_wbw = db.get_wbw_grouped_by_verse(surah)
            # Filter to specific range to optimize memory during parallel distribution
            all_wbw = {k: v for k, v in all_wbw.items() if start_verse <= k <= end_verse}

        # Prepare tasks for workers. All required data is passed as arguments to avoid sub-process DB access.
        tasks = []
        for i, verse_text in enumerate(verse_slice):
            current_ayah = start_verse + i
            wbw_translations = all_wbw.get(current_ayah, []) if annotate else []
            verse_trans_texts = translations[i]

            tasks.append(
                (
                    surah,
                    current_ayah,
                    verse_text,
                    wbw_translations,
                    verse_trans_texts,
                    self.layout_config,
                    self.text_config,
                    self.word_config,
                    annotate,
                    separate_translations,
                )
            )

        output_dir = kwargs.get("output_dir")
        filename_prefix = kwargs.get("filename_prefix", f"surah_{surah:03d}")

        if parallel and len(tasks) > 1:
            # Parallel execution using process pool for CPU-bound rendering tasks
            with ProcessPoolExecutor() as executor:
                # Add output_dir and prefix to task arguments for worker-level I/O
                p_tasks = [(t + (output_dir, filename_prefix)) for t in tasks]
                for result in executor.map(_render_verse_worker, p_tasks, chunksize=5):
                    if isinstance(result, list) and result and isinstance(result[0], str):
                        # Result contains file paths (direct-to-disk mode)
                        yield result
                    else:
                        # Result contains PNG byte streams; materialize back to PIL Images
                        yield [Image.open(io.BytesIO(b)) for b in result]
        else:
            # Serial execution for small ranges or single-process environments
            for t in tasks:
                p_task = t + (output_dir, filename_prefix)
                result = _render_verse_worker(p_task)
                if isinstance(result, list) and result and isinstance(result[0], str):
                    yield result
                else:
                    yield [Image.open(io.BytesIO(b)) for b in result]


# process-local cache for fonts to avoid redundant re-initialization in workers.
_WORKER_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _get_worker_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Retrieves a font instance from the process-local cache."""
    key = (path, size)
    if key not in _WORKER_FONT_CACHE:
        _WORKER_FONT_CACHE[key] = ImageFont.truetype(path, size)
    return _WORKER_FONT_CACHE[key]


def _render_verse_worker(args: tuple) -> list[bytes] | list[str]:
    """Worker function for rendering individual verses in parallel.

    This function is executed in sub-processes. It avoids database access by
    receiving all required data (verse text, WBW, translations) as arguments.
    Results are returned as PNG byte streams to minimize IPC overhead.
    """
    (
        surah,
        ayah,
        verse_text,
        wbw_translations,
        translations,
        layout_config,
        text_config,
        word_config,
        annotate,
        separate_translations,
        output_dir,
        filename_prefix,
    ) = args

    # Resolve DB manager internally if needed (singleton startup)
    # Actually, we don't need it if we have all data.

    verse_words = verse_text.split()
    word_images = [get_wimage(word, word_config) for word in verse_words]

    if annotate:
        # Genius: use Plural version for batching + Plural version uses Cache V2 (text-based)
        annotated_images, annotated_text = annotate_words(
            images=word_images,
            surah=surah,
            ayah=ayah,
            start=1,
            word_config=word_config,
            wbw_translations=wbw_translations,
            texts=verse_words,
        )
    else:
        annotated_images = word_images
        annotated_text = verse_words

    # Add verse number marker
    vn_image = verse_number(ayah, word_config)
    annotated_images.append(vn_image)
    annotated_text.append("")

    # Prepare WordItems
    word_items = [WordItem(image=img, text=txt) for img, txt in zip(annotated_images, annotated_text)]

    # Prepare Translation Images (materialize for pickling)
    lazy_trans = LazyTranslationImages(translations, text_config)
    translation_images = list(lazy_trans)

    if separate_translations:
        # Arabic-only rendering
        arabic_word_cfg = dataclasses.replace(word_config, max_rows_per_page=2)
        pages = list(
            frame(
                words=word_items,
                translation_images=None,
                config=layout_config,
                word_config=arabic_word_cfg,
            )
        )

        # Dedicated translation pages
        for trans_img in translation_images:
            if not trans_img:
                continue

            canvas = Image.new("RGBA", (layout_config.max_width, layout_config.image_height), (0, 0, 0, 0))
            if layout_config.timage_y_offset > 0:
                ty = layout_config.timage_y_offset - trans_img.height // 2
            else:
                ty = layout_config.image_height - layout_config.padding.bottom - trans_img.height // 2
            tx = (layout_config.max_width - trans_img.width) // 2 + layout_config.timage_x_offset
            canvas.paste(trans_img, (tx, ty), mask=trans_img if trans_img.mode == "RGBA" else None)
            pages.append(canvas)
    else:
        # Combined rendering
        pages = list(
            frame(
                words=word_items,
                translation_images=translation_images,
                config=layout_config,
                word_config=word_config,
            )
        )

    if output_dir:
        # Genius: Save directly in the worker to bypass IPC and main-process I/O bottleneck
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for i, p in enumerate(pages):
            filename = f"{filename_prefix}_verse_{ayah:03d}_page_{i + 1}.png"
            full_path = os.path.join(output_dir, filename)
            p.save(full_path, format="PNG")
            paths.append(full_path)
        return paths

    # Genius Serialization: Convert PIL Images to PNG Bytes for IPC efficiency
    results = []
    for p in pages:
        buf = io.BytesIO()
        p.save(buf, format="PNG", optimize=False)
        results.append(buf.getvalue())
    return results
