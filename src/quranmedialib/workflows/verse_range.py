"""Verse range workflow for processing ranges of verses."""

from __future__ import annotations

import dataclasses
from typing import Iterator

from PIL import Image

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.modules.annotation import annotate_words
from quranmedialib.modules.framer import frame
from quranmedialib.modules.timage import get_timage
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import WordItem
from quranmedialib.workflows.base import BaseWorkflow


def _get_db() -> DatabaseManager:
    """Get a fresh DatabaseManager instance."""
    return DatabaseManager()


class VerseRangeWorkflow(BaseWorkflow):
    """
    Workflow for processing a range of verses.
    """

    def get_iterator(
        self,
        surah: int,
        translations: list[list[str]],
        start_ayah: int = 1,
        end_ayah: int | None = None,
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """
        Processes a range of verses and yields lists of generated images (pages).
        
        Args:
            surah: The surah number.
            translations: List of verse translations, each verse being a list of page strings.
            start_ayah: The starting verse number (inclusive).
            end_ayah: The ending verse number (inclusive). If None, defaults to start_ayah.
            **kwargs: Additional arguments passed to _process_range.

        Yields:
            Iterator[list[Image.Image]]: A list of images for each verse iteration.
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
        """
        Processes a range of verses and yields lists of images.

        Args:
            surah: The surah number.
            start_verse: The starting verse number.
            end_verse: The ending verse number.
            translations: List of verse translations, each verse being a list of page strings.
            annotate: Whether to annotate the words.
            separate_translations: Whether to separate the translations.

        Yields:
            list[Image.Image]: A list of images for each verse iteration.
        """
        db = _get_db()

        arabic_verses = db.get_verses_from_surah(surah)

        # Iterate through each verse
        for i, verse_text in enumerate(arabic_verses[start_verse - 1 : end_verse]):
            current_verse_num = start_verse + i

            # Split verse text into words
            words = verse_text.split()

            # 1. Generate Arabic images (words + verse number)
            word_images = [get_wimage(word, self.word_config) for word in words]
            if annotate:
                wbw_images, wbw_texts = annotate_words(
                    word_images,
                    surah=surah,
                    ayah=current_verse_num,
                    start=1,
                    db=db,
                    word_config=self.word_config,
                    texts=list(words),
                )
            else:
                wbw_images = word_images
                wbw_texts = list(words)

            # Add verse number image after the verse's words
            v_num_img = verse_number(current_verse_num, self.word_config)
            wbw_images.append(v_num_img)
            wbw_texts.append(str(current_verse_num))

            # 2. Prepare translation images (drawn separately in the frame area)
            # translations[i] is a list of strings, each string representing a page of translation
            verse_pages_translations = translations[i]
            translation_images = [get_timage(text, self.text_config) for text in verse_pages_translations]

            # 3. Frame this verse iteration's images
            if separate_translations:
                # Arabic pages only (limit rows to 2)
                arabic_word_config = dataclasses.replace(self.word_config, max_rows_per_page=2)

                # Bundle into WordItems for layout
                arabic_items = [WordItem(img, text) for img, text in zip(wbw_images, wbw_texts)]

                arabic_pages = frame(
                    arabic_items,
                    translation_images=None,
                    config=self.layout_config,
                    word_config=arabic_word_config,
                )

                # Yield Arabic pages
                pages = list(arabic_pages)

                # Each translation image should be bottom-aligned on its own full-sized canvas
                for trans_img in translation_images:
                    if trans_img:
                        canvas = Image.new(
                            "RGBA", (self.layout_config.max_width, self.layout_config.image_height), (0, 0, 0, 0)
                        )
                        if self.layout_config.timage_y_offset > 0:
                            ty = self.layout_config.timage_y_offset - trans_img.height // 2
                        else:
                            ty = self.layout_config.image_height - self.layout_config.padding[1] - trans_img.height // 2

                        tx = (self.layout_config.max_width - trans_img.width) // 2 + self.layout_config.timage_x_offset
                        canvas.paste(trans_img, (tx, ty), mask=trans_img if trans_img.mode == "RGBA" else None)
                        pages.append(canvas)

                yield pages
            else:
                # Combined pages (default behavior)
                # Bundle into WordItems for layout
                word_items = [WordItem(img, text) for img, text in zip(wbw_images, wbw_texts)]

                combined_pages = frame(
                    word_items,
                    translation_images=translation_images,
                    config=self.layout_config,
                    word_config=self.word_config,
                )
                yield list(combined_pages)
