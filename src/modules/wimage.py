"""Module for converting Arabic text to images using a specific font.

This module provides functionality to render Arabic words into images with
customizable font size, color, and padding. It is designed to be used
as part of a larger workflow for Quranic verse image generation.
"""

from PIL import Image, ImageDraw, ImageFont

from src.modules.database_manager import DatabaseManager

db = DatabaseManager()


def get_wimage(text: str, font_size: int = 80, color: tuple[int, int, int, int] = (255, 255, 255, 255), padding: tuple[int, int, int, int] = (20, 20, 20, 20)) -> Image.Image:
    """Converts a word string into an image using the hafs font.

    Args:
        text: The Arabic text to render.
        font_size: The font size to use for rendering.
        color: The RGBA color of the text.
        padding: A tuple of (top, bottom, left, right) padding values.

    Returns:
        A PIL Image containing the rendered text with padding.
    """
    font = ImageFont.truetype("./assets/hafs.otf", font_size)

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
        (w + padding[2] + padding[3], h + padding[0] + padding[1]),
        color=(0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(img)

    # Draw text using the baseline
    # x: padding[2] - bbox[0] ensures the leftmost part starts at the left padding
    # y: padding[0] + ascent draws the baseline at a fixed height from the top padding
    draw.text(
        (padding[2] - bbox[0], padding[0] + ascent),
        text,
        font=font,
        fill=color,
        anchor="ls",  # 'l' for left, 's' for baseline
    )

    return img
