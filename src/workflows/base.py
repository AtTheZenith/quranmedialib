from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from PIL import Image

from src.modules.types import LayoutConfig, TextConfig, WordConfig


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
        verse_data: dict,
        translation_data: str | list[str],
        **kwargs,
    ) -> Iterator[list[tuple[Image.Image, str]]]:
        """
        Processes a single verse and yields lists of generated images (pages).
        Each page is a tuple of (Image, suffix).
        """
        pass
