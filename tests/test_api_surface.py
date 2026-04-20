"""Verification of the public API surface and package-level exports.

This module ensures that all intended classes, constants, and types are
correctly exported via quranmedialib.__all__ and are reachable.
"""

import quranmedialib


def test_api_version_exists() -> None:
    """Verify that __version__ is present."""
    assert hasattr(quranmedialib, "__version__")
    assert isinstance(quranmedialib.__version__, str)


def test_api_exports_completeness() -> None:
    """Verify that all names in __all__ are actually exported."""
    expected_exports = [
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

    # Check that __all__ matches our expectation
    assert sorted(quranmedialib.__all__) == sorted(expected_exports)

    # Check that each name in __all__ is actually an attribute of the module
    for name in quranmedialib.__all__:
        assert hasattr(quranmedialib, name), f"Exported name '{name}' not found in quranmedialib"


def test_api_types_resolvable() -> None:
    """Verify that core types can be instantiated from the top-level package."""
    from quranmedialib import Padding

    p = Padding(1, 2, 3, 4)
    assert p.top == 1

    # Ensure constants are reachable
    from quranmedialib import MAX_FONT_SIZE

    assert MAX_FONT_SIZE > 0

    # Ensure alignment enums are reachable
    from quranmedialib import HorizontalAlignment, VerticalAlignment

    assert HorizontalAlignment.CENTER.value == "center"
    assert VerticalAlignment.CENTER.value == "center"


def test_api_workflows_resolvable() -> None:
    """Verify that workflows can be instantiated from the top-level package."""
    from quranmedialib import LANDSCAPE_PRESET, IsolateWordsWorkflow, SurahWorkflow, VerseRangeWorkflow, VerseWorkflow

    layout, text, word = LANDSCAPE_PRESET["default"]["1080p"]

    # Just check that constructors are reachable and don't fail basic init validation
    v = VerseWorkflow(layout, text, word)
    assert v is not None

    s = SurahWorkflow(layout, text, word)
    assert s is not None

    vr = VerseRangeWorkflow(layout, text, word)
    assert vr is not None

    iw = IsolateWordsWorkflow(layout, text, word)
    assert iw is not None
