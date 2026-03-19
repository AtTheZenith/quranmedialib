"""Module for converting Arabic text to images using a specific font.

This module provides functionality to render Arabic words into images with
customizable font size, color, and padding. It is designed to be used
as part of a larger workflow for Quranic verse image generation.
"""

from PIL import Image, ImageDraw, ImageFont

from src.modules.database_manager import DatabaseManager
from src.modules.types import WordConfig

db = DatabaseManager()


def get_wimage(text: str, word_config: WordConfig) -> Image.Image:
    """Converts a word string into an image using the hafs font.

    Args:
        text: The Arabic text to render.
        word_config: The word configuration.

    Returns:
        A PIL Image containing the rendered text with padding.
    """
    font = ImageFont.truetype("./assets/hafs.otf", word_config.font_size)

    # Calculate text dimensions for dynamic image sizing and alignment
    ascent, descent = font.getmetrics()
    bbox = font.getbbox(text)

    # Width is based on the actual bounding box
    w = bbox[2] - bbox[0]
    # Height is based on the font's maximum possible height (ascent + descent)
    h = ascent + descent

    # Create image with padding
    # padding is (top, bottom, left, right)
    # img width: left + w + right
    # img height: top + h + bottom
    img = Image.new(
        "RGBA",
        (w + word_config.word_padding[2] + word_config.word_padding[3], h + word_config.word_padding[0] + word_config.word_padding[1]),
        color=(0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(img)

    # Draw text using the baseline
    # x: padding[2] - bbox[0] ensures the leftmost part starts at the left padding
    # y: padding[0] + ascent draws the baseline at a fixed height from the top padding
    draw.text(
        (word_config.word_padding[2] - bbox[0], word_config.word_padding[0] + ascent),
        text,
        font=font,
        fill=word_config.word_color,
        anchor="ls",  # 'l' for left, 's' for baseline
    )

    return img
