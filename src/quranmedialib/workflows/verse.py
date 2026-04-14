"""Workflow for rendering a single verse with Arabic text and translation.

This module provides the VerseWorkflow class for generating multi-page layouts
of individual Quranic verses with accompanying translations.
"""

from __future__ import annotations

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
        word_images = [get_wimage(word, self.word_config) for word in verse_words]

        if not annotate:
            return word_images

        # Annotate words with word-by-word translations
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

    def _prepare_translation_images(self, translations: list[str]) -> LazyTranslationImages:
        """Creates a lazy wrapper that defers get_timage() calls until accessed."""
        return LazyTranslationImages(translations, self.text_config)

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
            ValueError: If surah/ayah are out of range or no verse text found.
        """
        if not (1 <= surah <= 114):
            raise ValueError(f"Surah must be between 1 and 114, got {surah}")
        if not (1 <= ayah <= 286):
            raise ValueError(f"Ayah must be between 1 and 286, got {ayah}")

        db = DatabaseManager()

        # 1. Data Retrieval
        verse_text = db.get_verse(surah, ayah)
        if not verse_text.strip():
            raise ValueError(f"No verse text found for surah {surah}, ayah {ayah}")
        verse_words = verse_text.split()
        wbw_translations = db.get_wbw_from_verse(surah, ayah) if annotate else []

        # 2. Image Generation
        annotated_images = self._prepare_word_images(surah, ayah, verse_words, wbw_translations, annotate)

        # 3. Add verse number marker
        vn_image = verse_number(ayah, self.word_config)
        annotated_images.append(vn_image)

        # 4. Prepare WordItems for layout
        # We append an empty string for the verse number marker's text
        all_text = list(verse_words) + [""]
        word_items = [WordItem(image=img, text=text) for img, text in zip(annotated_images, all_text)]

        # 5. Prepare Translation Images (lazy - renders on demand)
        translation_images = self._prepare_translation_images(translations)

        # 6. Render Layout
        yield frame(
            words=word_items,
            translation_images=translation_images,
            config=self.layout_config,
            word_config=self.word_config,
        )
