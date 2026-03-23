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
        surah: int,
        annotate: bool = True,
        separate_translations: bool = False,
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """
        Processes an entire surah and yields lists of generated images.

        Args:
            surah: The Surah number.
            annotate: Whether to annotate the words.
            separate_translations: Whether to separate the translations.

        Yields:
            Iterator[list[Image.Image]]: A list of pages for each verse iteration.
        """
        db = DatabaseManager()

        # Get Arabic verses from Quran database (always uses "quran" database)
        arabic_verses = db.get_verses_from_surah(surah)
        start_verse = 1
        end_verse = len(arabic_verses)

        if not arabic_verses:
            raise ValueError(f"No verses found for Surah {surah}")

        # Get English translations from translation database
        raw_translations = db.get_translation_from_surah(surah)
        translations = [[t] for t in raw_translations]

        return self._process_range(
            surah=surah,
            start_verse=start_verse,
            end_verse=end_verse,
            translations=translations,
            annotate=annotate,
            separate_translations=separate_translations,
        )
