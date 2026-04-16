"""Surah workflow for processing entire surahs.

This module provides the SurahWorkflow class, which specialized VerseRangeWorkflow
to process all verses of a given surah with their default translations.
"""

from __future__ import annotations

import logging
import warnings
from typing import Iterator

from PIL import Image

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.workflows.verse_range import VerseRangeWorkflow

# Logger setup
logger = logging.getLogger(__name__)

__all__ = ["SurahWorkflow"]


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
            **kwargs:
                - parallel: bool (default: True for |verses| > 10)
                - output_dir: Optional path to save images directly.

        Yields:
            list[Image.Image]: List of page images for each verse in the surah.

        Raises:
            ValueError: If no verses are found for the given surah.
        """
        if not (1 <= surah <= 114):
            raise ValueError(f"Surah must be between 1 and 114, got {surah}")

        # Warn about unrecognized kwargs to catch typos early
        known_kwargs = {"annotate", "separate_translations", "parallel", "output_dir", "filename_prefix"}
        unrecognized = set(kwargs.keys()) - known_kwargs
        if unrecognized:
            warnings.warn(
                f"Unknown kwargs ignored by SurahWorkflow.get_iterator: {unrecognized}",
                UserWarning,
                stacklevel=2,
            )

        db = DatabaseManager()

        # Retrieve Arabic verses and translations
        arabic_verses = db.get_verses_from_surah(surah)
        if not arabic_verses:
            raise ValueError(f"No verses found for Surah {surah}")

        raw_translations = db.get_translation_from_surah(surah)

        # Wrap each translation in a list to match VerseRangeWorkflow's expectation
        # (One page of translation per verse by default).
        translations = [[t] for t in raw_translations]

        # Enable parallel processing by default for surahs with more than 10 verses
        parallel = kwargs.get("parallel", len(arabic_verses) > 10)

        return self._process_range(
            surah=surah,
            start_verse=1,
            end_verse=len(arabic_verses),
            translations=translations,
            annotate=annotate,
            separate_translations=separate_translations,
            parallel=parallel,
            **kwargs,
        )
