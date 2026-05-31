"""Tests for the verse_number module.

This module contains tests for verifying verse number rendering with the
Unicode ayah symbol and various padding configurations.
"""

import os

import pytest

from quranmedialib import LANDSCAPE_PRESET
from quranmedialib.modules.verse_number import logger, verse_number


def test_verse_number() -> None:
    print("\nRunning test_verse_number...")
    test_number = 286
    logger.info(f"Generating ayah number {test_number} using Unicode symbol...")

    # Test default padding (10, 10, 10, 10)
    img_default = verse_number(test_number, LANDSCAPE_PRESET["default"]["1080p"].word)
    logger.info(f"Default padding size: {img_default.size}")

    output_dir = "./output/test/verse_number"
    os.makedirs(output_dir, exist_ok=True)

    img_default.save(os.path.join(output_dir, f"{test_number:03d}_default.png"))

    logger.info(f"Test generation complete. Saved to {output_dir}")
    print("test_verse_number completed successfully.")


if __name__ == "__main__":
    test_verse_number()


# === Validation Tests ===


def test_verse_number_negative() -> None:
    """Test that verse_number raises ValueError for negative numbers."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"].word

    with pytest.raises(ValueError, match="Verse number must be non-negative"):
        verse_number(-1, word_config)

    with pytest.raises(ValueError, match="Verse number must be non-negative"):
        verse_number(-100, word_config)


def test_verse_number_zero() -> None:
    """Test that verse_number handles zero correctly."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"].word

    # Zero should be valid (non-negative)
    img = verse_number(0, word_config)
    assert img is not None
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_verse_number_large_value() -> None:
    """Test that verse_number handles large values correctly."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"].word

    # Large ayah number should work
    img = verse_number(9999, word_config)
    assert img is not None
    assert img.size[0] > 0


def test_verse_number_none_config() -> None:
    """Test that verse_number raises error when config is None."""
    with pytest.raises(AttributeError):
        verse_number(1, None)  # type: ignore


def test_verse_number_negative_padding_dimensions() -> None:
    """Test that verse_number with extreme negative padding produces a valid image."""
    from quranmedialib.types import Padding, WordConfig

    base_config = LANDSCAPE_PRESET["default"]["1080p"].word
    # Create config with negative padding
    neg_config = WordConfig(
        font=base_config.font,
        font_size=base_config.font_size,
        max_rows_per_page=base_config.max_rows_per_page,
        row_spacing=base_config.row_spacing,
        word_spacing=base_config.word_spacing,
        word_padding=Padding(-1000, -1000, -1000, -1000),
    )

    # Should not crash — should produce at least a minimal image
    img = verse_number(1, neg_config)
    assert img is not None
    assert img.size[0] >= 1
    assert img.size[1] >= 1


def test_verse_number_empty_text() -> None:
    """Test that verse_number with 0 produces a valid marker."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"].word
    img = verse_number(0, word_config)
    assert img is not None
    assert img.size[0] > 0
