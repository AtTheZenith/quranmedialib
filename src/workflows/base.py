from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator, TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from src.modules.database_manager import DatabaseManager
    from src.modules.framer import LayoutConfig
    from src.modules.timage import TextConfig


class VerseWorkflow(ABC):
    """
    Abstract base class for workflows that process a single verse.
    """

    def __init__(
        self,
        layout_config: LayoutConfig,
        text_config: TextConfig,
        database_manager: DatabaseManager | None = None,
    ):
        self.layout_config = layout_config
        self.text_config = text_config
        self.database_manager = database_manager

    @abstractmethod
    def process_verse(
        self,
        verse_data: dict,
        translation_data: str | list[str],
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """
        Processes a single verse and yields lists of generated images (pages).
        """
        pass


class SurahWorkflow(ABC):
    """
    Abstract base class for workflows that process an entire surah.
    """

    def __init__(
        self,
        layout_config: LayoutConfig,
        text_config: TextConfig,
        database_manager: DatabaseManager | None = None,
    ):
        self.layout_config = layout_config
        self.text_config = text_config
        self.database_manager = database_manager

    @abstractmethod
    def process_surah(
        self,
        surah_data: dict,
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """
        Processes an entire surah and yields lists of generated images.
        """
        pass
