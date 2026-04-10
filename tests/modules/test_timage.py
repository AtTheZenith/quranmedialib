"""
Tests for the timage module.
"""

import os

import pytest
from PIL import Image, ImageDraw, ImageOps

from quranmedialib import LANDSCAPE_PRESET
from quranmedialib.modules.timage import (
    _get_font,
    _parse_rich_text,
    _wrap_rich_text_balanced,
    get_timage,
)
from quranmedialib.types import TextConfig


def _verify_pyramid(text: str, max_width: int, filename: str | None = None):
    """Helper to verify that a given text wraps into an inverted pyramid at max_width."""
    config = TextConfig(max_width=max_width)
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    styled_words = _parse_rich_text(text, config, draw)
    default_font, _ = _get_font("", config)
    space_width = int(draw.textlength(" ", font=default_font))

    lines = _wrap_rich_text_balanced(styled_words, config.max_width)
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

        if filename == "center_vertical":
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
