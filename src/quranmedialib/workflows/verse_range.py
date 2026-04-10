"""Verse range workflow for processing ranges of verses.

This module provides the VerseRangeWorkflow class, which handles rendering multiple
verses in sequence, supporting optional translation separation and batch annotation.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Iterator

from PIL import Image

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.modules.annotation import annotate_word
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

    def _prepare_verse_images(
        self,
        surah: int,
        ayah: int,
        verse_words: list[str],
        annotate: bool,
        wbw_translations: list[str],
    ) -> list[Image.Image]:
        """Generates and optionally annotates word images for a specific verse.

        Args:
            surah: Surah number (1-114).
            ayah: Ayah (verse) number (1-indexed).
            verse_words: List of Arabic word strings in the verse.
            annotate: Whether to annotate words with word-by-word translations.
            wbw_translations: Pre-fetched WBW translations for this verse.

        Returns:
            list[Image.Image]: List of word images (annotated or plain).
        """
        word_images = [get_wimage(word, self.word_config) for word in verse_words]

        if not annotate:
            return word_images

        annotated = []
        for i, img in enumerate(word_images):
            translation = wbw_translations[i] if i < len(wbw_translations) else None
            ann_img = annotate_word(
                image=img,
                surah=surah,
                ayah=ayah,
                word_index=i + 1,
                translation=translation,
                word_config=self.word_config,
            )
            annotated.append(ann_img)

        return annotated

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
        """
        if end_ayah is None:
            end_ayah = start_ayah

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
    ) -> Iterator[list[Image.Image]]:
        """Internal iterator implementation for processing a verse range.

        Args:
            surah: Surah number (1-114).
            start_verse: Starting verse number (1-indexed).
            end_verse: Ending verse number (inclusive).
            translations: Nested list of translation texts [verse_index][page_index].
            annotate: Whether to annotate words with word-by-word translations.
            separate_translations: If True, render translations on separate pages.

        Yields:
            list[Image.Image]: List of page images for each verse in the range.
        """
        db = DatabaseManager()
        arabic_verses = db.get_verses_from_surah(surah)

        # Fetch all WBW data once for the entire surah if annotating
        all_wbw = db.get_wbw_grouped_by_verse(surah) if annotate else {}

        for i, verse_text in enumerate(arabic_verses[start_verse - 1 : end_verse]):
            current_ayah = start_verse + i
            verse_words = verse_text.split()

            # Get pre-fetched WBW data for this verse
            wbw_translations = all_wbw.get(current_ayah, []) if annotate else []

            # 1. Image Generation
            annotated_images = self._prepare_verse_images(surah, current_ayah, verse_words, annotate, wbw_translations)

            # Add verse number marker
            vn_image = verse_number(current_ayah, self.word_config)
            annotated_images.append(vn_image)

            # 2. Translation Preparation (lazy - renders on demand)
            verse_trans_texts = translations[i]
            lazy_trans_images = LazyTranslationImages(verse_trans_texts, self.text_config)

            # 3. Layout Rendering
            all_text = list(verse_words) + [""]
            word_items = [WordItem(image=img, text=text) for img, text in zip(annotated_images, all_text)]

            if separate_translations:
                # Arabic-only rendering (restricted row count)
                arabic_word_cfg = dataclasses.replace(self.word_config, max_rows_per_page=2)
                arabic_pages = list(
                    frame(
                        words=word_items,
                        translation_images=None,
                        config=self.layout_config,
                        word_config=arabic_word_cfg,
                    )
                )

                # Dedicated translation pages (need all translations rendered)
                trans_pages = self._render_separate_translation_pages(lazy_trans_images.render_all())
                yield arabic_pages + trans_pages
            else:
                # Combined rendering (Arabic + Translation on same page)
                # Translation images are rendered lazily as pages are generated
                combined_pages = frame(
                    words=word_items,
                    translation_images=lazy_trans_images,
                    config=self.layout_config,
                    word_config=self.word_config,
                )
                yield list(combined_pages)
