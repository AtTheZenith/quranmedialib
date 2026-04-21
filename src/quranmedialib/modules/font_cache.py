"""Centralized font caching module to avoid redundant font file loading.

This module provides an LRU-cached font loading function that eliminates
repeated file I/O and font parsing across the codebase.

To prevent state mutation bugs (e.g., set_variation_by_name affecting other
callers), this module returns a **copy** of the cached font object, ensuring
each caller gets an independent font instance that can be safely mutated.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from quranmedialib.types import MAX_FONT_SIZE

# Supported font file extensions
_SUPPORTED_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc", ".pfb", ".pcf", ".bdf", ".pfa", ".pfm"}

# Maximum font file size (50MB) to prevent decompression bomb attacks
_MAX_FONT_FILE_SIZE = 50 * 1024 * 1024


@lru_cache(maxsize=512)
def _load_font_base(font_path: str, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads and caches the base font instance (internal use only)."""
    # Validate file extension
    ext = Path(font_path).suffix.lower()
    if ext not in _SUPPORTED_FONT_EXTENSIONS:
        supported = ", ".join(sorted(_SUPPORTED_FONT_EXTENSIONS))
        raise ValueError(f"Unsupported font file extension: {ext}. Supported: {supported}")

    # Validate file size
    file_size = Path(font_path).stat().st_size
    if file_size > _MAX_FONT_FILE_SIZE:
        raise ValueError(f"Font file too large: {file_size} bytes (limit: {_MAX_FONT_FILE_SIZE})")

    return ImageFont.truetype(font_path, font_size)


def get_font(font_path: str, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Returns a cached font instance.

    Args:
        font_path: Path to the font file as a string.
        font_size: Font size in points (must be in range 1 to MAX_FONT_SIZE).

    Returns:
        A PIL Font object.

    Raises:
        ValueError: If font_size is not in range (1, MAX_FONT_SIZE).
        OSError: If the font file cannot be loaded.
    """
    if font_size <= 0:
        raise ValueError(f"font_size must be positive, got {font_size}")
    if font_size > MAX_FONT_SIZE:
        raise ValueError(f"font_size exceeds maximum limit of {MAX_FONT_SIZE}, got {font_size}")
    return _load_font_base(font_path, font_size)
