"""Centralized font caching module to avoid redundant font file loading.

This module provides an LRU-cached font loading function that eliminates
repeated file I/O and font parsing across the codebase.
"""

from __future__ import annotations

from functools import lru_cache

from PIL import ImageFont


@lru_cache(maxsize=128)
def get_font(font_path: str, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads and caches a font file to avoid repeated file I/O.

    Args:
        font_path: Path to the font file as a string.
        font_size: Font size in points.

    Returns:
        A loaded PIL Font object.

    Raises:
        OSError: If the font file cannot be loaded.
    """
    return ImageFont.truetype(font_path, font_size)
