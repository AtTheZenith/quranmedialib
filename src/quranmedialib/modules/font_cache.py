"""Centralized font caching module to avoid redundant font file loading.

This module provides an LRU-cached font loading function that eliminates
repeated file I/O and font parsing across the codebase.

To prevent state mutation bugs (e.g., set_variation_by_name affecting other
callers), this module returns a **copy** of the cached font object, ensuring
each caller gets an independent font instance that can be safely mutated.
"""

from __future__ import annotations

from functools import lru_cache

from PIL import ImageFont


@lru_cache(maxsize=128)
def _load_font_base(font_path: str, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads and caches the base font instance (internal use only)."""
    return ImageFont.truetype(font_path, font_size)


def get_font(font_path: str, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Returns a fresh copy of the font to prevent state mutation across callers.

    The base font is cached, but each call returns an independent copy that
    can be safely mutated (e.g., via set_variation_by_name) without affecting
    other callers.

    Args:
        font_path: Path to the font file as a string.
        font_size: Font size in points.

    Returns:
        A fresh PIL Font object copy.

    Raises:
        OSError: If the font file cannot be loaded.
    """
    base_font = _load_font_base(font_path, font_size)
    return base_font.font_variant()
