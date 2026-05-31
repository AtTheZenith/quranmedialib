"""Base workflow abstract class for QuranMediaLib workflows.

This module defines the interface for all generation workflows, ensuring consistent
configuration handling and iteration patterns.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterator

from PIL import Image

from quranmedialib.exceptions import ValidationError
from quranmedialib.types import MAX_AYAH, MAX_SURAH, MIN_AYAH, MIN_SURAH

if TYPE_CHECKING:
    from quranmedialib.types import Preset

# Logger setup
logger = logging.getLogger(__name__)


class BaseWorkflow(ABC):
    """Abstract base class for workflows that process Quranic content.

    All workflows must implement get_iterator to yield rendered pages.
    """

    def __init__(
        self,
        preset: Preset,
    ):
        """Initializes the workflow with a preset configuration.

        Raises:
            ValidationError: If preset is None.
        """
        if preset is None:
            raise ValidationError("Preset configuration must not be None.")
        self.frame_cfg = preset.frame
        self.word_cfg = preset.word
        self.verse_cfg = preset.verse
        self.text_cfg = preset.text

    def _validate_surah(self, surah: int) -> int:
        """Validates surah number (1-114)."""
        if not (MIN_SURAH <= surah <= MAX_SURAH):
            raise ValidationError(f"Surah must be between {MIN_SURAH} and {MAX_SURAH}, got {surah}")
        return surah

    def _validate_ayah(self, ayah: int) -> int:
        """Validates ayah number (1-286)."""
        if not (MIN_AYAH <= ayah <= MAX_AYAH):
            raise ValidationError(f"Ayah must be between {MIN_AYAH} and {MAX_AYAH}, got {ayah}")
        return ayah

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(frame={self.frame_cfg}, word={self.word_cfg}, "
            f"verse={self.verse_cfg}, text={self.text_cfg})"
        )

    @abstractmethod
    def get_iterator(
        self,
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """Processes data and yields lists of generated images (pages).

        Args:
            **kwargs: Workflow-specific parameters (e.g., surah, ayah, range).

        Yields:
            Iterator[list[Image.Image]]: Lists of PIL images, where each list
                represents a single page's layers.
        """
        pass
