from __future__ import annotations

from typing import Iterator, TYPE_CHECKING

from PIL import Image

from src.modules.annotation import annotate_word
from src.modules.framer import frame
from src.modules.timage import get_timage
from src.modules.verse_number import verse_number
from src.modules.wimage import get_wimage
from src.workflows.base import VerseWorkflow

if TYPE_CHECKING:
    from src.modules.framer import LayoutConfig
    from src.modules.timage import TextConfig


class VerseRangeWorkflow(VerseWorkflow):
    """
    Workflow for processing a range of verses, imitating the workflow of main.py.
    """

    def process_range(
        self,
        start_verse: int,
        end_verse: int,
        translations: list[list[str]],
        arabic_verses: list[str],
        **kwargs,
    ) -> Iterator[list[tuple[Image.Image, str]]]:
        """
        Processes a range of verses and yields lists of (image, suffix) tuples.

        Args:
            start_verse: The starting verse number.
            end_verse: The ending verse number.
            translations: List of verse translations, each verse being a list of page strings.
            arabic_verses: List of Arabic verse texts (one string per verse).
            **kwargs:
                - surah: int (default: 1)
                - annotate: bool (default: True)
                - separate_translations: bool (default: False)

        Yields:
            list[tuple[Image.Image, str]]: A list of (image, suffix) for each verse iteration.
        """
        surah_number = kwargs.get("surah", 1)
        annotate = kwargs.get("annotate", True)
        separate_translations = kwargs.get("separate_translations", False)

        # Iterate through each verse
        for i, verse_text in enumerate(arabic_verses):
            current_verse_num = start_verse + i
            
            # Split verse text into words (as requested: "split in function")
            words = verse_text.split()
            
            # 1. Generate Arabic images (words + verse number)
            word_images = []
            for j, word in enumerate(words):
                # Generate base word image
                w_img = get_wimage(word)

                # Annotate word image (fetches WBW from DB if not provided)
                if annotate:
                    ann_img = annotate_word(w_img, surah_number, current_verse_num, j + 1)
                else:
                    ann_img = w_img
                
                word_images.append(ann_img)

            # Add verse number image after the verse's words
            v_num_img = verse_number(current_verse_num, font_size=110, padding=(1, 71, 1, 1))
            word_images.append(v_num_img)

            # 2. Prepare translation images (drawn separately in the frame area)
            # translations[i] is a list of strings, each string representing a page of translation
            verse_pages_translations = translations[i]
            translation_images = [
                get_timage(text, self.layout_config.content_width, self.text_config)
                for text in verse_pages_translations
            ]

            # 3. Frame this verse iteration's images
            if separate_translations:
                # Arabic pages only (limit rows to 2)
                import dataclasses
                arabic_config = dataclasses.replace(self.layout_config, max_rows_per_page=2)
                
                arabic_pages = frame(
                    word_images,
                    words_text=words + [""],
                    translation_images=None,
                    config=arabic_config,
                )
                
                # Yield Arabic pages
                pages = [(img, "a") for img in arabic_pages]
                
                # Each translation image should be bottom-aligned on its own full-sized canvas
                # matching the Y position in combined mode.
                trans_y = self.layout_config.image_height - self.layout_config.padding - self.layout_config.bottom_offset
                for trans_img in translation_images:
                    if trans_img:
                        # Create a transparent canvas of the standard size
                        canvas = Image.new(
                            "RGBA", 
                            (self.layout_config.max_width, self.layout_config.image_height), 
                            (0, 0, 0, 0)
                        )
                        # Center the translation image horizontally and place at trans_y
                        tx = (self.layout_config.max_width - trans_img.width) // 2
                        canvas.paste(trans_img, (tx, trans_y), mask=trans_img if trans_img.mode == "RGBA" else None)
                        pages.append((canvas, "t"))
                
                yield pages
            else:
                # Combined pages (default behavior)
                combined_pages = frame(
                    word_images,
                    words_text=words + [""],
                    translation_images=translation_images,
                    config=self.layout_config,
                )
                yield [(img, "a") for img in combined_pages]

    def process_verse(
        self,
        verse_data: dict,
        translation_data: list[str],
        **kwargs,
    ) -> Iterator[list[tuple[Image.Image, str]]]:
        """
        Implementation of the abstract base method for a single verse.
        Wraps process_range for compatibility.
        """
        start_verse = verse_data.get("ayah", 1)
        arabic_verses = [verse_data.get("text", " ".join(verse_data.get("words", [])))]
        # Wrap translation_data into a list of list of strings (one verse, list of page strings)
        translations = [translation_data] if isinstance(translation_data, list) else [[translation_data]]

        return self.process_range(
            start_verse=start_verse,
            end_verse=start_verse,
            translations=translations,
            arabic_verses=arabic_verses,
            surah=verse_data.get("surah", 1),
            **kwargs,
        )
