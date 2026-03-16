from __future__ import annotations

from typing import Iterator

from PIL import Image

from src.modules.database_manager import DatabaseManager
from src.workflows.base import SurahWorkflow as BaseSurahWorkflow
from src.workflows.verse_range import VerseRangeWorkflow


class SurahWorkflow(VerseRangeWorkflow, BaseSurahWorkflow):
    """
    Workflow for processing an entire Surah.
    """

    def process_surah(
        self,
        surah_data: dict,
        **kwargs,
    ) -> Iterator[list[tuple[Image.Image, str]]]:
        """
        Processes an entire surah and yields lists of generated images.
        Each page is a tuple of (Image, suffix).
        Args:
            surah_data: Dictionary containing 'surah' number.
            **kwargs: Additional arguments passed to process_range.

        Yields:
            Iterator[list[tuple[Image.Image, str]]]: A list of pages for each verse iteration, where each page is a tuple of (Image, suffix).
        """
        surah_number = surah_data.get("surah")
        if not surah_number:
            raise ValueError("Surah number is required in surah_data")

        # Use the existing DatabaseManager instance if available, otherwise create a new one
        db = DatabaseManager()

        # Fetch Arabic verses
        # db.get_verses_from_surah returns list[str] (verses -> text)
        arabic_verses = db.get_verses_from_surah(surah_number)

        if not arabic_verses:
            raise ValueError(f"No verses found for Surah {surah_number}")

        # Fetch translations
        # process_range expects list[list[str]] (verses -> pages -> text)
        # db.get_translation_from_surah returns list[str] (verses -> text)
        raw_translations = db.get_translation_from_surah(surah_number)

        # Each verse translation is currently a single string.
        # Since we don't have page splitting logic for translations here yet (it might be handled in frame() or elsewhere),
        # we wrap each translation string in a list, effectively treating it as a single page translation per verse.
        translations = [[t] for t in raw_translations]

        start_verse = 1
        end_verse = len(arabic_verses)

        # Delegate to VerseRangeWorkflow's process_range
        return self.process_range(
            start_verse=start_verse,
            end_verse=end_verse,
            translations=translations,
            arabic_verses=arabic_verses,
            surah=surah_number,
            **kwargs,
        )
