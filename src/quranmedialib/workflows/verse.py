"""Workflow for rendering a single verse with Arabic text and translation.

This module provides the VerseWorkflow class for generating multi-page layouts
of individual Quranic verses with accompanying translations.
"""

from __future__ import annotations

import logging
from typing import Iterator

from PIL import Image

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.exceptions import WorkflowError
from quranmedialib.modules.annotation import annotate_words
from quranmedialib.modules.vimage import VImage
from quranmedialib.modules.frame import Frame
from quranmedialib.modules.timage import LazyTranslationImages
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import WordItem
from quranmedialib.workflows.base import BaseWorkflow

# Logger setup
logger = logging.getLogger(__name__)

__all__ = ["VerseWorkflow"]


class VerseWorkflow(BaseWorkflow):
    """Workflow for rendering a single verse with Arabic text and translation.

    This workflow fetches verse data from the database, generates word images,
    optionally annotates them with word-by-word translations, and frames everything
    with user-provided translation strings.
    """

    def _prepare_word_images(
        self,
        surah: int,
        ayah: int,
        verse_words: list[str],
        wbw_translations: list[str | None],
        annotate: bool,
    ) -> list[Image.Image]:
        """Generates and optionally annotates word images for the verse."""
        # Generate base word images
        word_images = [get_wimage(word, self.word_cfg) for word in verse_words]

        if annotate:
            # annotate_words returns a tuple (images, texts) when texts are provided
            annotated_images, _ = annotate_words(
                images=word_images,
                surah=surah,
                ayah=ayah,
                start=1,
                word_config=self.word_cfg,
                texts=verse_words,
            )
        else:
            annotated_images = word_images

        return annotated_images

    def _prepare_translation_images(self, translations: list[str]) -> LazyTranslationImages:
        """Creates a lazy wrapper that defers get_timage() calls until accessed."""
        return LazyTranslationImages(translations, self.text_cfg)

    def get_iterator(
        self,
        surah: int,
        ayah: int,
        translations: list[str],
        annotate: bool = True,
    ) -> Iterator[list[Image.Image]]:
        """Render a single verse with Arabic text and translation.

        Args:
            surah: Surah number (1-114).
            ayah: Ayah (verse) number within the surah.
            translations: List of translation strings, one per page.
            annotate: Whether to annotate words with word-by-word translations.

        Yields:
            list[Image.Image]: A list of rendered page images for the verse.

        Raises:
            ValidationError: If surah/ayah are out of range.
            WorkflowError: If no verse text found.
        """
        surah = self._validate_surah(surah)
        ayah = self._validate_ayah(ayah)

        db = DatabaseManager()

        # 1. Data Retrieval
        verse_text = db.get_verse(surah, ayah)
        if not verse_text.strip():
            raise WorkflowError(f"No verse text found for surah {surah}, ayah {ayah}")
        verse_words = verse_text.split()
        wbw_translations = db.get_wbw_from_verse(surah, ayah) if annotate else []

        # 2. Image Generation
        annotated_images = self._prepare_word_images(surah, ayah, verse_words, wbw_translations, annotate)

        # 3. Add verse number marker
        vn_image = verse_number(ayah, self.word_cfg)
        annotated_images.append(vn_image)

        # 4. Prepare WordItems for layout
        # We append an empty string for the verse number marker's text
        all_text = list(verse_words) + [""]
        word_items = [WordItem(image=img, text=text) for img, text in zip(annotated_images, all_text)]

        # 5. Prepare Translation Images (lazy - renders on demand)
        translation_images = self._prepare_translation_images(translations)

        # 6. Render Layout
        vimage = VImage(word_items, self.verse_cfg, self.frame_cfg)
        pages = []
        page_index = 0
        current_index = 0
        total_items = len(word_items)

        while current_index < total_items:
            current_rows, items_consumed = vimage.get_page_chunk(current_index, self.verse_cfg.max_rows_per_page)
            frame_obj = Frame(self.frame_cfg)
            v_img = vimage.render(self.word_cfg, rows_to_render=current_rows)
            frame_obj.layer(
                v_img,
                alignment=(self.frame_cfg.wimage_horizontal_align, self.frame_cfg.wimage_vertical_align),
                offset=(self.frame_cfg.wimage_x_offset, self.frame_cfg.wimage_y_offset),
            )

            if translation_images and page_index < len(translation_images):
                if t_image := translation_images[page_index]:
                    frame_obj.layer(
                        t_image,
                        alignment=(self.frame_cfg.timage_horizontal_align, self.frame_cfg.timage_vertical_align),
                        offset=(self.frame_cfg.timage_x_offset, self.frame_cfg.timage_y_offset),
                        text_color=self.text_cfg.color,
                    )

            pages.append(frame_obj.render())
            current_index += items_consumed
            page_index += 1

        yield pages
