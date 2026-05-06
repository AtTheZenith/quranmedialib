"""QuranMediaLib - Generate beautiful Quranic verse images with ease.

QuranMediaLib is a media generation library for rendering Quranic Arabic text
and translations into customizable, high-quality images with professional layouts.

Quick Start:
    >>> from quranmedialib import DatabaseManager, VerseWorkflow, LANDSCAPE_PRESET
    >>> db = DatabaseManager()
    >>> layout, text_cfg, word_cfg = LANDSCAPE_PRESET["default"]["1080p"]
    >>> workflow = VerseWorkflow(layout, text_cfg, word_cfg)
    >>> pages = list(workflow.get_iterator(surah=1, ayah=1, translations=["In the name of Allah"]))
    >>> pages[0][0].save("output.png")  # Save first page
    >>> db.close()

Key Features:
    - Render Arabic Quranic text with customizable fonts and colors
    - Add word-by-word translations and annotations
    - Multi-page layout engine with right-to-left text support
    - Rich text formatting for translations (bold, italic, colors)
    - Image effects: glow, colorization, padding
    - Pre-configured presets for common formats (landscape, story, square)

Package Structure:
    types:         Configuration dataclasses (LayoutConfig, WordConfig, etc.)
    presets:       Pre-configured layouts (LANDSCAPE_PRESET, STORY_PRESET, etc.)
    database_manager:  Stateful SQLite connection manager for Quran databases
    resources:     Asset path resolution (fonts, databases) via importlib.resources
    modules:       Core rendering modules
        wimage:        Arabic word rendering
        timage:        Translation text rendering with rich formatting
        framer:        Multi-page layout engine (RTL support)
        image:         Image effects (glow, color, padding)
        annotation:    Word-by-word annotation with translations
        verse_number:  Verse number badge rendering
    workflows:     High-level workflow classes
        verse:         Single verse rendering with translation
        surah:         Process entire surahs
        verse_range:   Process verse ranges
        isolate_words: Isolate individual words in context

For more examples, see the demo.py file and README.md.
"""

from importlib.metadata import version

__version__ = version("quranmedialib")

# Expose types and presets at package level for convenience
from quranmedialib.database_manager import DatabaseManager
from quranmedialib.exceptions import (
    DatabaseError,
    LayoutError,
    QuranMediaLibError,
    ResourceError,
    ValidationError,
    WorkflowError,
)
from quranmedialib.modules.text_layout import Line, StyledWord
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
    MAX_AYAH,
    MAX_FONT_SIZE,
    MAX_SURAH,
    MIN_AYAH,
    MIN_SURAH,
    AyahNumber,
    Color,
    DatabaseConfig,
    FontResource,
    HorizontalAlignment,
    LayoutConfig,
    Padding,
    SurahNumber,
    TextConfig,
    VerticalAlignment,
    WbwDatabaseConfig,
    WordConfig,
    WordIndex,
    WordItem,
)
from quranmedialib.workflows.isolate_words import IsolateWordsWorkflow
from quranmedialib.workflows.surah import SurahWorkflow
from quranmedialib.workflows.verse import VerseWorkflow
from quranmedialib.workflows.verse_range import VerseRangeWorkflow

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
    "HorizontalAlignment",
    "VerticalAlignment",
    "MAX_FONT_SIZE",
    "MIN_SURAH",
    "MAX_SURAH",
    "MIN_AYAH",
    "MAX_AYAH",
    # Text rendering types
    "StyledWord",
    "Line",
    # Exceptions
    "QuranMediaLibError",
    "ResourceError",
    "DatabaseError",
    "WorkflowError",
    "ValidationError",
    "LayoutError",
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
    # Workflows
    "VerseWorkflow",
    "VerseRangeWorkflow",
    "SurahWorkflow",
    "IsolateWordsWorkflow",
]
