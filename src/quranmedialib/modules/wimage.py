"""Module for converting Arabic text to images using a specific font.

This module provides functionality to render Arabic words into images with
customizable font size, color, and padding.
"""

from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw

from quranmedialib.modules.font_cache import _load_font_base
from quranmedialib.types import Padding, WordConfig

__all__ = ["get_wimage"]


# Cache key: (text, font_path, font_size, padding_tuple, word_color, bg_color)
# Max 3072 entries covers all ~2,699 unique words in the Quran
@lru_cache(maxsize=3072)
def _get_wimage_cached(
    text: str,
    font_path: str,
    font_size: int,
    word_padding: tuple[int, int, int, int],
    word_color: tuple[int, ...],
    bg_color: tuple[int, ...],
) -> Image.Image:
    """Cached internal renderer. Returns new PIL Image for the given text + config."""
    font = _load_font_base(font_path, font_size)

    ascent, descent = font.getmetrics()
    bbox = font.getbbox(text)

    w = max(1, bbox[2] - bbox[0])
    h = max(1, ascent + descent)

    padding = Padding(word_padding[0], word_padding[1], word_padding[2], word_padding[3])
    img_w = max(1, int(w + padding.horizontal))
    img_h = max(1, int(h + padding.vertical))

    img = Image.new("RGBA", (img_w, img_h), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.text(
        (padding.left - bbox[0], padding.top + ascent),
        text,
        font=font,
        fill=word_color,
        anchor="ls",
    )

    return img


def get_wimage(text: str, word_config: WordConfig) -> Image.Image:
    """Converts an Arabic word string into an image.

    Results are cached (LRU, max 2048 entries) based on text + config parameters.
    Repeated words (e.g., "Allah" × 2,699) render once and reuse the cached image.

    Args:
        text: The Arabic text to render.
        word_config: Configuration containing font size, colors, padding, and font.

    Returns:
        A PIL Image containing the rendered text with padding.
    """
    return _get_wimage_cached(
        text,
        str(word_config.font.path),
        word_config.font_size,
        tuple(word_config.word_padding),
        word_config.word_color,
        word_config.background_color,
    )
