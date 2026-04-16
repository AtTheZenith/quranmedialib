"""Tests for the font_cache module.

This module contains tests for verifying font caching functionality including:
- Font loading and caching
- Invalid font path handling
- Font size validation
"""

import pytest

from quranmedialib.modules.font_cache import get_font
from quranmedialib.resources import get_font_path


def test_get_font_valid() -> None:
    """Test that get_font returns font for valid path."""
    font_path = str(get_font_path("hafs.otf"))
    font = get_font(font_path, 72)
    assert font is not None


def test_get_font_invalid_path() -> None:
    """Test that get_font raises OSError for invalid font path."""
    with pytest.raises(OSError):
        get_font("/nonexistent/font.otf", 72)


def test_get_font_zero_size() -> None:
    """Test that get_font raises error for zero font size."""
    font_path = str(get_font_path("hafs.otf"))
    with pytest.raises(Exception):
        get_font(font_path, 0)


def test_get_font_negative_size() -> None:
    """Test that get_font raises error for negative font size."""
    font_path = str(get_font_path("hafs.otf"))
    with pytest.raises(Exception):
        get_font(font_path, -10)


def test_get_font_caching() -> None:
    """Test that get_font caches base font instances."""
    font_path = str(get_font_path("hafs.otf"))

    # First call should load and cache
    font1 = get_font(font_path, 72)
    # Second call should use cache
    font2 = get_font(font_path, 72)

    # Should be the same object (shared for performance)
    assert font1 is font2
    assert font1.size == font2.size


def test_get_font_none_path() -> None:
    """Test that get_font raises error for None path."""
    with pytest.raises((TypeError, OSError, AttributeError)):
        get_font(None, 72)  # type: ignore


def test_get_font_none_size() -> None:
    """Test that get_font raises error for None size."""
    font_path = str(get_font_path("hafs.otf"))
    with pytest.raises((TypeError, Exception)):
        get_font(font_path, None)  # type: ignore


def test_get_font_size_one_works() -> None:
    """Test that font_size=1 is accepted (boundary value)."""
    font_path = str(get_font_path("hafs.otf"))
    font = get_font(font_path, 1)
    assert font is not None
    assert font.size == 1


def test_get_font_exceeds_max_size() -> None:
    """Test that get_font raises error for font_size exceeding MAX_FONT_SIZE."""
    from quranmedialib.types import MAX_FONT_SIZE

    font_path = str(get_font_path("hafs.otf"))
    with pytest.raises(ValueError, match="font_size exceeds maximum limit"):
        get_font(font_path, MAX_FONT_SIZE + 1)
