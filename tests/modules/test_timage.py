"""
Tests for the timage module.
"""

import os

import pytest
from PIL import Image, ImageDraw, ImageOps

from quranmedialib import LANDSCAPE_PRESET
from quranmedialib.modules.text_layout import wrap_rich_text_balanced
from quranmedialib.modules.timage import (
    _parse_rich_text,
    format_isolation_text,
    get_timage,
    normalize_highlight_style,
    prepare_translation_segments,
)
from quranmedialib.types import TextConfig


def _verify_pyramid(text: str, max_width: int, filename: str | None = None):
    """Helper to verify that a given text wraps into an inverted pyramid at max_width."""
    config = TextConfig(max_width=max_width)
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    styled_words = _parse_rich_text(text, config, draw)

    lines = wrap_rich_text_balanced(styled_words, config.max_width)
    widths = [line.width for line in lines]

    assert len(lines) > 0, "Expected at least one line."
    for i in range(len(widths) - 1):
        assert widths[i] >= widths[i + 1], (
            f"Pyramid violation at line {i}: {widths[i]} is not >= {widths[i + 1]} in width sequence {widths}"
        )

    # Save image for human review if a filename is provided
    if filename:
        output_dir = "./output/test/timage/pyramid"
        os.makedirs(output_dir, exist_ok=True)
        if img := get_timage(text, config):
            # Add a border to visualize the max_width
            img_with_border = ImageOps.expand(img, border=2, fill="gray")
            img_with_border.save(f"{output_dir}/{filename}.png")

    return widths


def test_timage_rendering():
    """Verifies that various rich text formats render correctly to images."""
    output_dir = "./output/test/timage"
    os.makedirs(output_dir, exist_ok=True)

    _, text_config, _ = LANDSCAPE_PRESET["default"]["1080p"]

    test_cases = [
        ("plain", "Hello World!"),
        ("bold_red", "#b#ff0000#Bold Red Text#"),
        ("italic_green", "#i#00ff00#Italic Green Text#"),
        ("bold_italic_blue", "#bi#0000ffff#Bold Italic Blue Text#"),
        ("center_vertical", "#b#ffffff#Centered in 400px height#"),
    ]

    for filename, text in test_cases:
        max_height = 400 if filename == "center_vertical" else None
        img = get_timage(text, text_config, max_height=max_height)
        assert img is not None

        img = ImageOps.expand(img, border=2, fill="white")

        img.save(f"{output_dir}/{filename}.png")


@pytest.mark.parametrize(
    "name, text, max_width",
    [
        ("short", "This is a short text that will form a pyramid.", 400),
        (
            "lorem",
            (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut "
                "labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco "
                "laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in "
                "voluptate velit esse cillum dolore eu fugiat nulla pariatur."
            ),
            1200,
        ),
        ("single", "Short", 400),
        ("long_word", "A very very long single word that might break things", 300),
    ],
    ids=["short", "lorem", "single", "long_word"],
)
def test_timage_pyramid(name: str, text: str, max_width: int) -> None:
    """
    Tests the 'Balanced Inverted Pyramid' logic across different scales.
    """
    widths = _verify_pyramid(text, max_width, filename=name)
    if len(widths) > 1:
        print(f"Pyramid widths for '{name}' (max_width={max_width}): {widths}")


if __name__ == "__main__":
    # Allow running manually
    test_timage_rendering()
    _verify_pyramid("This is a short text that will form a pyramid.", 300, filename="manual")


# === Validation Tests ===


def test_timage_empty_text() -> None:
    """Test that get_timage returns None for empty text."""
    result = get_timage("", TextConfig())
    assert result is None


def test_timage_none_text() -> None:
    """Test that get_timage returns None for None text."""
    result = get_timage(None, TextConfig())  # type: ignore
    assert result is None


def test_timage_none_config() -> None:
    """Test that get_timage handles None config by using defaults."""
    # get_timage creates a default TextConfig when config is None
    result = get_timage("test", None)  # type: ignore
    assert result is not None
    assert result.size[0] > 0
    assert result.size[1] > 0


def test_timage_negative_max_height() -> None:
    """Test that get_timage raises error for negative max_height."""
    config = TextConfig()
    # Negative max_height causes PIL to reject the canvas dimensions
    with pytest.raises(ValueError, match="Width and height must be >= 0"):
        get_timage("test", config, max_height=-100)


def test_timage_invalid_rich_text_format() -> None:
    """Test that get_timage handles malformed rich text."""
    config = TextConfig()

    # Malformed tags (missing closing tag)
    result = get_timage("#b#unclosed bold text", config)
    assert result is not None  # Should handle gracefully

    # Invalid hex color
    result = get_timage("#invalidhex#text", config)
    assert result is not None  # Should handle gracefully


@pytest.mark.benchmark
def test_timage_very_long_text() -> None:
    """Test that get_timage handles very long text without crashing."""
    config = TextConfig(max_width=1200)
    very_long_text = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore "
        "et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut "
        "aliquip ex ea commodo consequat."
    ) * 300

    result = get_timage(very_long_text, config)
    assert result is not None
    assert result.size[0] > 0
    assert result.size[1] > 0


# === Format Isolation Text Bounds Tests ===


def test_format_isolation_text_negative_target_index() -> None:
    """Test that format_isolation_text raises ValueError for negative target_index."""
    from quranmedialib.modules.timage import format_isolation_text, prepare_translation_segments

    segments = prepare_translation_segments(["text1", "text2"])

    with pytest.raises(ValueError, match="target_index must be non-negative"):
        format_isolation_text(segments, target_index=-1, highlight_style="#b#FF0000#")


def test_format_isolation_text_out_of_bounds_target_index() -> None:
    """Test that format_isolation_text raises ValueError for out-of-bounds target_index."""
    from quranmedialib.modules.timage import format_isolation_text, prepare_translation_segments

    segments = prepare_translation_segments(["text1", "text2", "text3"])

    with pytest.raises(ValueError, match="target_index.*out of bounds"):
        format_isolation_text(segments, target_index=10, highlight_style="#b#FF0000#")


def test_format_isolation_text_valid_target_index() -> None:
    """Test that format_isolation_text works correctly for valid target_index."""
    from quranmedialib.modules.timage import format_isolation_text, prepare_translation_segments

    segments = prepare_translation_segments(["text1", "text2", "text3"])

    result = format_isolation_text(segments, target_index=1, highlight_style="#b#FF0000#")
    assert result is not None
    assert isinstance(result, str)


# === timage Config Edge Cases (Round 2) ===


def test_timage_negative_line_spacing() -> None:
    """Test that get_timage handles negative line_spacing."""
    config = TextConfig(line_spacing=-10, max_width=500)
    result = get_timage("test text with negative spacing", config)
    # Should produce a valid image (negative spacing may overlap lines)
    assert result is not None
    assert result.size[0] > 0
    assert result.size[1] > 0


def test_normalize_highlight_style_none_input() -> None:
    """Test normalize_highlight_style with None input."""

    result = normalize_highlight_style(None)  # type: ignore
    # Should return a default style string
    assert isinstance(result, str)
    assert len(result) > 0


def test_prepare_translation_segments_none_input() -> None:
    """Test prepare_translation_segments with None input."""
    result = prepare_translation_segments(None)  # type: ignore
    # Should return empty list or handle gracefully
    assert isinstance(result, list)


def test_timage_empty_styled_words() -> None:
    """Test that get_timage returns None for text that produces no styled words."""
    config = TextConfig(max_width=500)
    # Text with only whitespace should produce no styled words
    result = get_timage("   \t\n   ", config)
    assert result is None


def test_timage_very_large_font_size() -> None:
    """Test that TextConfig raises ValueError for font_size exceeding MAX_FONT_SIZE."""
    from quranmedialib.types import MAX_FONT_SIZE

    # Font size exceeding MAX_FONT_SIZE should raise ValueError during config creation
    with pytest.raises(ValueError, match="font_size exceeds maximum limit"):
        TextConfig(font_size=MAX_FONT_SIZE + 1, max_width=500)


def _assert_format_isolation_text_target_index_bounds(segments, target_index):
    # Index 0
    result_0 = format_isolation_text(segments, target_index=target_index, highlight_style="#b#FF0000#")
    assert result_0 is not None
    assert "#b#" in result_0  # Should contain highlight


def test_format_isolation_text_target_index_bounds() -> None:
    """Test format_isolation_text with index exactly 0 and len-1."""
    segments = prepare_translation_segments(["first", "second", "third"])

    _assert_format_isolation_text_target_index_bounds(segments, 0)
    _assert_format_isolation_text_target_index_bounds(segments, 2)


def test_timage_single_word_no_wrapping() -> None:
    """Test that get_timage with a single word produces one line."""
    config = TextConfig(max_width=500)
    result = get_timage("singleword", config)
    assert result is not None
    assert result.size[1] > 0


def test_timage_none_max_width() -> None:
    """Test that get_timage works when config.max_width is None."""
    config = TextConfig()  # default max_width is None
    result = get_timage("test text with no max width", config)
    assert result is not None
    assert result.size[0] > 0
