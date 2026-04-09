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
from quranmedialib.modules.timage import TextConfig, get_timage
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import WordItem
from quranmedialib.workflows.base import BaseWorkflow

# Logger setup
logger = logging.getLogger(__name__)

__all__ = ["VerseWorkflow"]


class _LazyTranslationImages:
    """Lazy list that defers get_timage() calls until items are accessed.

    This avoids rendering translation images that are never used (e.g., when
    a verse fits on fewer pages than translations prepared).
    """

    __slots__ = ("_texts", "_config", "_cache")

    def __init__(self, texts: list[str], config: TextConfig) -> None:
        self._texts = texts
        self._config = config
        self._cache: list[Image.Image | None] = [None] * len(texts)

    def __len__(self) -> int:
        return len(self._texts)

    def __getitem__(self, index: int) -> Image.Image | None:
        if self._cache[index] is None and self._texts[index]:
            self._cache[index] = get_timage(self._texts[index], self._config)
        return self._cache[index]


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

    def _prepare_translation_images(self, translations: list[str]) -> _LazyTranslationImages:
        """Creates a lazy wrapper that defers get_timage() calls until accessed."""
        return _LazyTranslationImages(translations, self.text_config)

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
        """
        db = DatabaseManager()

        # 1. Data Retrieval
        verse_text = db.get_verse(surah, ayah)
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
