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
    img = get_wimage(words[0], LANDSCAPE_PRESET["default"]["1080p"][2])
    img.save(f"{output_dir}/wimage.png")
    print("Done.")
    print("test_wimage completed successfully.")


if __name__ == "__main__":
    test_wimage()


# === Validation Tests ===


def test_wimage_empty_text() -> None:
    """Test that get_wimage handles empty text gracefully."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]
    # Empty text should return a minimal image (just padding)
    img = get_wimage("", word_config)
    assert img is not None
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_wimage_none_text() -> None:
    """Test that get_wimage handles None text gracefully."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]

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

    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]
    invalid_config = replace(word_config, font=FontResource(name="invalid", path="/nonexistent/font.otf"))

    with pytest.raises(OSError):
        get_wimage("test", invalid_config)
