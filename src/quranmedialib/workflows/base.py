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

if TYPE_CHECKING:
    from quranmedialib.types import LayoutConfig, TextConfig, WordConfig

# Logger setup
logger = logging.getLogger(__name__)


class BaseWorkflow(ABC):
    """Abstract base class for workflows that process Quranic content.

    All workflows must implement get_iterator to yield rendered pages.
    """

    def __init__(
        self,
        layout_config: LayoutConfig,
        text_config: TextConfig,
        word_config: WordConfig,
    ):
        """Initializes the workflow with shared configurations.

        Raises:
            ValidationError: If any config object is None.
        """
        if layout_config is None or text_config is None or word_config is None:
            raise ValidationError(
                f"Configuration objects must not be None. "
                f"Got layout_config={layout_config}, text_config={text_config}, word_config={word_config}"
            )
        self.layout_config = layout_config
        self.text_config = text_config
        self.word_config = word_config

    def _validate_surah(self, surah: int) -> int:
        """Validates surah number (1-114)."""
        if not (1 <= surah <= 114):
            raise ValidationError(f"Surah must be between 1 and 114, got {surah}")
        return surah

    def _validate_ayah(self, ayah: int) -> int:
        """Validates ayah number (1-286)."""
        if not (1 <= ayah <= 286):
            raise ValidationError(f"Ayah must be between 1 and 286, got {ayah}")
        return ayah

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(layout={self.layout_config}, text={self.text_config}, word={self.word_config})"
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
