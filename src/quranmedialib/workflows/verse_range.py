"""Verse range workflow for processing ranges of verses.

This module provides the VerseRangeWorkflow class, which handles rendering multiple
verses in sequence, supporting optional translation separation and batch annotation.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import TYPE_CHECKING, Iterator

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.modules.annotation import annotate_word
from quranmedialib.modules.framer import frame
from quranmedialib.modules.timage import get_timage
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import WordItem
from quranmedialib.workflows.base import BaseWorkflow

from PIL import Image

if TYPE_CHECKING:
    pass

# Logger setup
logger = logging.getLogger(__name__)


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
        db: DatabaseManager,
    ) -> list[Image.Image]:
        """Generates and optionally annotates word images for a specific verse."""
        word_images = [get_wimage(word, self.word_config) for word in verse_words]

        if not annotate:
            return word_images

        wbw_translations = db.get_wbw_from_verse(surah, ayah)
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
        """Creates dedicated full-size pages for each translation image."""
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

            tx = (
                (self.layout_config.max_width - trans_img.width) // 2
                + self.layout_config.timage_x_offset
            )

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
        """Processes a range of verses and yields lists of generated images (pages)."""
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
        """Internal iterator implementation for processing a verse range."""
        db = DatabaseManager()
        arabic_verses = db.get_verses_from_surah(surah)

        for i, verse_text in enumerate(arabic_verses[start_verse - 1 : end_verse]):
            current_ayah = start_verse + i
            verse_words = verse_text.split()

            # 1. Image Generation
            annotated_images = self._prepare_verse_images(
                surah, current_ayah, verse_words, annotate, db
            )

            # Add verse number marker
            vn_image = verse_number(current_ayah, self.word_config)
            annotated_images.append(vn_image)

            # 2. Translation Preparation
            verse_trans_texts = translations[i]
            translation_images = [
                get_timage(text, self.text_config) for text in verse_trans_texts
            ]

            # 3. Layout Rendering
            all_text = list(verse_words) + [""]
            word_items = [
                WordItem(image=img, text=text) for img, text in zip(annotated_images, all_text)
            ]

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

                # Dedicated translation pages
                trans_pages = self._render_separate_translation_pages(translation_images)
                yield arabic_pages + trans_pages
            else:
                # Combined rendering (Arabic + Translation on same page)
                combined_pages = frame(
                    words=word_items,
                    translation_images=translation_images,
                    config=self.layout_config,
                    word_config=self.word_config,
                )
                yield list(combined_pages)
