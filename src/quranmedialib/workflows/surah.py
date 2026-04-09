"""Surah workflow for processing entire surahs.

This module provides the SurahWorkflow class, which specialized VerseRangeWorkflow
to process all verses of a given surah with their default translations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterator

from PIL import Image

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.workflows.verse_range import VerseRangeWorkflow

if TYPE_CHECKING:
    pass

# Logger setup
logger = logging.getLogger(__name__)


class SurahWorkflow(VerseRangeWorkflow):
    """Workflow for processing an entire Surah.

    Fetches all verses and their corresponding translations from the database
    and orchestrates the rendering process using the VerseRangeWorkflow logic.
    """

    def get_iterator(
        self,
        surah: int,
        annotate: bool = True,
        separate_translations: bool = False,
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """Processes an entire surah and yields lists of generated images (pages).

        Args:
            surah: Surah number (1-114).
            annotate: Whether to annotate words with word-by-word translations.
            separate_translations: If True, render translations on separate pages.
            **kwargs: Additional keyword arguments (currently unused).

        Yields:
            list[Image.Image]: List of page images for each verse in the surah.

        Raises:
            ValueError: If no verses are found for the given surah.
        """
        db = DatabaseManager()

        # Retrieve Arabic verses and translations
        arabic_verses = db.get_verses_from_surah(surah)
        if not arabic_verses:
            raise ValueError(f"No verses found for Surah {surah}")

        raw_translations = db.get_translation_from_surah(surah)

        # Wrap each translation in a list to match VerseRangeWorkflow's expectation
        # (One page of translation per verse by default).
        translations = [[t] for t in raw_translations]

        return self._process_range(
            surah=surah,
            start_verse=1,
            end_verse=len(arabic_verses),
            translations=translations,
            annotate=annotate,
            separate_translations=separate_translations,
        )
