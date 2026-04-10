"""Module for lazy image rendering utilities.

This module provides the `_LazyTranslationImages` class, which defers
expensive text rendering operations until images are actually accessed.
This optimization avoids rendering translation images that are never
displayed (e.g., when a verse fits on fewer pages than translations prepared).
"""

from __future__ import annotations

from typing import Sequence

from PIL import Image

from quranmedialib.modules.timage import TextConfig, get_timage

__all__ = ["LazyTranslationImages"]


class LazyTranslationImages(Sequence):
    """Lazy sequence that defers get_timage() calls until items are accessed.

    This avoids rendering translation images that are never used (e.g., when
    a verse fits on fewer pages than translations prepared).

    The class implements the `Sequence` abstract base class, making it compatible
    with any code expecting a list-like interface (iteration, indexing, len).
    """

    __slots__ = ("_texts", "_config", "_cache")

    def __init__(self, texts: list[str], config: TextConfig) -> None:
        """Initialize the lazy wrapper.

        Args:
            texts: List of translation text strings to render.
            config: Text configuration for rendering.
        """
        self._texts = texts
        self._config = config
        self._cache: list[Image.Image | None] = [None] * len(texts)

    def __len__(self) -> int:
        return len(self._texts)

    def __getitem__(self, index: int) -> Image.Image | None:
        if self._cache[index] is None and self._texts[index]:
            self._cache[index] = get_timage(self._texts[index], self._config)
        return self._cache[index]

    def render_all(self) -> list[Image.Image | None]:
        """Force rendering of all translation images.

        Useful when all translations are needed at once (e.g., for
        separate translation pages mode).

        Returns:
            List of rendered images (or None for empty translations).
        """
        return [self[i] for i in range(len(self._texts))]
