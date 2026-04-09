"""Module for converting Arabic text to images using a specific font.

This module provides functionality to render Arabic words into images with
customizable font size, color, and padding.
"""

from PIL import Image, ImageDraw

from quranmedialib.modules.font_cache import get_font
from quranmedialib.types import WordConfig


def get_wimage(text: str, word_config: WordConfig) -> Image.Image:
    """Converts an Arabic word string into an image.

    Args:
        text: The Arabic text to render.
        word_config: Configuration containing font size, colors, padding, and font.

    Returns:
        A PIL Image containing the rendered text with padding.
    """
    font = get_font(str(word_config.font.path), word_config.font_size)

    # Calculate text dimensions based on metrics and actual bounding box.
    ascent, descent = font.getmetrics()
    bbox = font.getbbox(text)

    # Width is based on the actual bounding box, height on font max (ascent + descent).
    w = bbox[2] - bbox[0]
    h = ascent + descent

    padding = word_config.word_padding

    # Create canvas with padding
    img_w = int(w + padding.horizontal)
    img_h = int(h + padding.vertical)

    img = Image.new("RGBA", (img_w, img_h), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw text using baseline alignment ('ls')
    # x: starts at left padding, adjusted for bbox offset.
    # y: draws baseline at top padding + ascent.
    draw.text(
        (padding.left - bbox[0], padding.top + ascent),
        text,
        font=font,
        fill=word_config.word_color,
        anchor="ls",
    )

    return img
