"""Surah workflow for processing entire surahs.

This module provides the SurahWorkflow class, which specialized VerseRangeWorkflow
to process all verses of a given surah with their default translations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterator

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.workflows.verse_range import VerseRangeWorkflow

from PIL import Image

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
        """Processes an entire surah and yields lists of generated images (pages)."""
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
