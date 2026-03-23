"""QuranMediaLib - Media producing library for Quranic texts.

This package provides tools for rendering Quranic Arabic text and translations
into images with customizable layouts and styling.

Package Structure:
    - quranmedialib.types: Configuration dataclasses (LayoutConfig, WordConfig, TextConfig, etc.)
    - quranmedialib.presets: Pre-configured font and layout presets
    - quranmedialib.database_manager: Stateful database connection manager
    - quranmedialib.resources: Asset path resolution via importlib.resources
    - quranmedialib.modules: Core rendering modules
        - wimage: Arabic word rendering
        - timage: Translation text rendering
        - framer: Multi-page layout engine
        - image: Image effects (glow, color, pad)
        - annotation: Word-by-word annotation
        - verse_number: Verse number rendering
    - quranmedialib.workflows: High-level workflows
        - surah: Surah-level processing
        - verse_range: Verse range processing
        - isolate_words: Word isolation workflows
        - verse: Single verse rendering with translation

Example:
    from quranmedialib import DatabaseManager
    from quranmedialib.modules.wimage import get_wimage
    from quranmedialib.modules.framer import frame
    from quranmedialib.presets import LANDSCAPE_PRESET

    db = DatabaseManager()
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    # Render a word
    word_img = get_wimage("الله", word_config)

    # Get verses from a surah
    verses = db.get_verses_from_surah(1)
"""

__version__ = "0.1.0"

# Expose types and presets at package level for convenience
from quranmedialib.database_manager import DatabaseManager
from quranmedialib.presets import (
    DATABASE_EN_SAHIH,
    DATABASE_QURAN,
    DATABASE_WBW_EN,
    FONT_HAFS,
    FONT_INTER,
    FONT_INTER_ITALIC,
    LANDSCAPE_PRESET,
    SQUARE_PRESET,
    STORY_PRESET,
)
from quranmedialib.types import (
    AyahNumber,
    Color,
    DatabaseConfig,
    FontResource,
    LayoutConfig,
    Line,
    Padding,
    StyledWord,
    SurahNumber,
    TextConfig,
    WbwDatabaseConfig,
    WordConfig,
    WordIndex,
    WordItem,
)
from quranmedialib.workflows.verse import VerseWorkflow

__all__ = [
    # Version
    "__version__",
    # Type aliases
    "Color",
    "Padding",
    "SurahNumber",
    "AyahNumber",
    "WordIndex",
    # Resource classes
    "FontResource",
    # Database classes
    "DatabaseConfig",
    "WbwDatabaseConfig",
    "DatabaseManager",
    # Config classes
    "WordItem",
    "LayoutConfig",
    "WordConfig",
    "TextConfig",
    # Text rendering types
    "StyledWord",
    "Line",
    # Presets
    "FONT_HAFS",
    "FONT_INTER",
    "FONT_INTER_ITALIC",
    "DATABASE_QURAN",
    "DATABASE_EN_SAHIH",
    "DATABASE_WBW_EN",
    "LANDSCAPE_PRESET",
    "STORY_PRESET",
    "SQUARE_PRESET",
    "VerseWorkflow",
]
