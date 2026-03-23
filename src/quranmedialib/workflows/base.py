"""Base workflow abstract class for QuranMediaLib workflows."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from PIL import Image

from quranmedialib.types import LayoutConfig, TextConfig, WordConfig


class BaseWorkflow(ABC):
    """
    Abstract base class for workflows that process a single verse.
    """

    def __init__(
        self,
        layout_config: LayoutConfig,
        text_config: TextConfig,
        word_config: WordConfig,
    ):
        self.layout_config = layout_config
        self.text_config = text_config
        self.word_config = word_config

    @abstractmethod
    def get_iterator(
        self,
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """
        Processes data and yields lists of generated images (pages).
        """
        pass
