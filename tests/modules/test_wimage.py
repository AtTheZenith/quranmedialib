"""Tests for the wimage module (Arabic word rendering).

This module contains tests for verifying Arabic word image generation
with proper font rendering and configuration.
"""

import os

import pytest

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.modules.wimage import get_wimage

db = DatabaseManager()


def _ensure_db_initialized() -> None:
    """Ensure database is initialized (handles singleton closure from other tests)."""
    global db
    if not getattr(db, "_initialized", False):
        db = DatabaseManager()


def test_wimage() -> None:
    print("\nRunning test_wimage...")
    _ensure_db_initialized()
    surah = 2
    verses = db.get_verses_from_surah(surah)
    words = [word for verse in verses for word in verse.split() if word]
    output_dir = "./output/test/wimage"
    os.makedirs(output_dir, exist_ok=True)

    print("Processing word...")
    img = get_wimage(words[0], LANDSCAPE_PRESET["default"]["1080p"].word)
    img.save(f"{output_dir}/wimage.png")
    print("Done.")
    print("test_wimage completed successfully.")


if __name__ == "__main__":
    test_wimage()


# === Validation Tests ===


def test_wimage_empty_text() -> None:
    """Test that get_wimage handles empty text gracefully."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"].word
    # Empty text should return a minimal image (just padding)
    img = get_wimage("", word_config)
    assert img is not None
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_wimage_none_text() -> None:
    """Test that get_wimage handles None text gracefully."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"].word

    with pytest.raises((TypeError, AttributeError)):
        get_wimage(None, word_config)  # type: ignore


def test_wimage_none_config() -> None:
    """Test that get_wimage raises error when config is None."""
    with pytest.raises(AttributeError):
        get_wimage("test", None)  # type: ignore


def test_wimage_invalid_font_path() -> None:
    """Test that get_wimage raises OSError for invalid font path."""
    from dataclasses import replace

    from quranmedialib.types import FontResource

    word_config = LANDSCAPE_PRESET["default"]["1080p"].word
    invalid_config = replace(word_config, font=FontResource(name="invalid", path="/nonexistent/font.otf"))

    with pytest.raises(OSError):
        get_wimage("test", invalid_config)


def test_wimage_negative_padding_dimensions() -> None:
    """Test that get_wimage with extreme negative padding produces a valid image."""
    from quranmedialib.types import Padding, WordConfig

    base_config = LANDSCAPE_PRESET["default"]["1080p"].word
    # Override padding with values that would produce negative dimensions
    neg_config = WordConfig(
        font=base_config.font,
        font_size=base_config.font_size,
        max_rows_per_page=base_config.max_rows_per_page,
        row_spacing=base_config.row_spacing,
        word_spacing=base_config.word_spacing,
        word_padding=Padding(-1000, -1000, -1000, -1000),
    )

    # Should not crash — should produce at least a minimal image
    img = get_wimage("test", neg_config)
    assert img is not None
    assert img.size[0] >= 1
    assert img.size[1] >= 1


def test_wimage_very_long_word() -> None:
    """Test that get_wimage handles very long text without crashing."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"].word
    long_text = "a" * 10000
    img = get_wimage(long_text, word_config)
    assert img is not None
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_wimage_padding_variations() -> None:
    """Test various padding combinations."""
    from quranmedialib.types import Padding, WordConfig

    word_config = LANDSCAPE_PRESET["default"]["1080p"].word
    for padding_vals in [(0, 0, 0, 0), (10, 10, 10, 10), (50, 50, 50, 50)]:
        config = WordConfig(
            font=word_config.font,
            font_size=word_config.font_size,
            max_rows_per_page=word_config.max_rows_per_page,
            row_spacing=word_config.row_spacing,
            word_spacing=word_config.word_spacing,
            word_padding=Padding(*padding_vals),
        )
        img = get_wimage("test", config)
        assert img is not None
