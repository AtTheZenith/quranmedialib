"""Workflow for rendering a single verse with Arabic text and translation.

This module provides the VerseWorkflow class for generating multi-page layouts
of individual Quranic verses with accompanying translations.
"""

from typing import Iterator

from PIL import Image

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.modules.annotation import annotate_word
from quranmedialib.modules.framer import frame
from quranmedialib.modules.timage import get_timage
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import WordItem
from quranmedialib.workflows.base import BaseWorkflow


class VerseWorkflow(BaseWorkflow):
    """Workflow for rendering a single verse with Arabic text and translation.

    This workflow fetches verse data from the database, generates word images,
    optionally annotates them with word-by-word translations, and frames everything
    with user-provided translation strings.

    Example:
        from quranmedialib import VerseWorkflow, LANDSCAPE_PRESET

        layout, text, word = LANDSCAPE_PRESET["default"]["1080p"]
        workflow = VerseWorkflow(layout, text, word)

        # User determines translation split based on framer output
        translations = ["Page 1 translation", "Page 2 translation"]

        for page_images in workflow.get_iterator(
            surah=1,
            ayah=1,
            translations=translations,
            annotate=True,
        ):
            for img in page_images:
                img.save("output.png")
    """

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
                The user determines the split based on how the framer divides
                Arabic verses across pages.
            annotate: Whether to annotate words with word-by-word translations.
                Defaults to True.

        Yields:
            list[Image.Image]: A list of pages containing the verse layout.
                Each page is a list of PIL Image objects.
        """
        db = DatabaseManager()

        # Fetch Arabic verse text and split into words
        verse_text = db.get_verse(surah, ayah)
        verse_words = verse_text.split()

        # Fetch word-by-word translations for annotation
        wbw_translations = db.get_wbw_from_verse(surah, ayah)

        # Generate word images
        word_images = [get_wimage(word, self.word_config) for word in verse_words]

        # Annotate words if requested
        if annotate:
            annotated_images = [
                annotate_word(
                    image=img,
                    surah=surah,
                    ayah=ayah,
                    word_index=i + 1,
                    translation=wbw_translations[i] if i < len(wbw_translations) else None,
                    word_config=self.word_config,
                )
                for i, img in enumerate(word_images)
            ]
        else:
            annotated_images = word_images

        # Add verse number image
        verse_number_image = verse_number(ayah, self.word_config)
        annotated_images.append(verse_number_image)

        # Create WordItems for layout
        items_text = list(verse_words) + [""]
        word_items = [WordItem(image=img, text=text) for img, text in zip(annotated_images, items_text)]

        # Convert translation strings to images
        translation_images = [
            get_timage(translation, self.text_config) if translation else None
            for translation in translations
        ]

        # Frame with translation pages
        yield frame(
            words=word_items,
            translation_images=translation_images,
            config=self.layout_config,
            word_config=self.word_config,
        )
