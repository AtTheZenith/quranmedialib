"""Surah workflow for processing entire surahs."""

from __future__ import annotations

from typing import Iterator

from PIL import Image

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.workflows.verse_range import VerseRangeWorkflow


class SurahWorkflow(VerseRangeWorkflow):
    """
    Workflow for processing an entire Surah.
    """

    def get_iterator(
        self,
        surah_data: dict,
        annotate: bool = True,
        separate_translations: bool = False,
    ) -> Iterator[list[tuple[Image.Image, str]]]:
        """
        Processes an entire surah and yields lists of generated images.
        Each page is a tuple of (Image, suffix).
        Args:
            surah_data: Dictionary containing 'surah' number.
            annotate: Whether to annotate the words.
            separate_translations: Whether to separate the translations.

        Yields:
            Iterator[list[tuple[Image.Image, str]]]: A list of pages for each verse iteration, where each page is a tuple of (Image, suffix).
        """
        surah_number = surah_data.get("surah")
        if not surah_number:
            raise ValueError("Surah number is required in surah_data")

        db = DatabaseManager()

        # Get Arabic verses from Quran database
        db.set_active_translation("quran")
        arabic_verses = db.get_verses_from_surah(surah_number)
        start_verse = 1
        end_verse = len(arabic_verses)

        if not arabic_verses:
            raise ValueError(f"No verses found for Surah {surah_number}")

        # Get English translations from translation database
        db.set_active_translation("translation")
        raw_translations = db.get_translation_from_surah(surah_number)
        translations = [[t] for t in raw_translations]

        # Set back to Quran for the verse range processing
        db.set_active_translation("quran")

        return self._process_range(
            surah=surah_number,
            start_verse=start_verse,
            end_verse=end_verse,
            translations=translations,
            annotate=annotate,
            separate_translations=separate_translations,
        )
