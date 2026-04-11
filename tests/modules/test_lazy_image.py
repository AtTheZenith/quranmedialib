"""Tests for the lazy_image module.

This module contains tests for verifying lazy image rendering functionality including:
- Lazy evaluation (images rendered only when accessed)
- Caching behavior
- Sequence protocol implementation
"""

import pytest

from quranmedialib import LANDSCAPE_PRESET
from quranmedialib.modules.lazy_image import LazyTranslationImages
from quranmedialib.types import TextConfig


def test_lazy_image_init() -> None:
    """Test that LazyTranslationImages initializes correctly."""
    texts = ["text1", "text2", "text3"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)

    assert len(lazy) == 3
    assert lazy._cache == [None, None, None]


def test_lazy_image_getitem() -> None:
    """Test that LazyTranslationImages renders image on access."""
    texts = ["Hello World"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)

    # Access should render and cache the image
    img = lazy[0]
    assert img is not None
    # Second access should use cache
    img2 = lazy[0]
    assert img is img2


def test_lazy_image_empty_texts() -> None:
    """Test that LazyTranslationImages handles empty texts list."""
    lazy = LazyTranslationImages([], TextConfig())
    assert len(lazy) == 0


def test_lazy_image_none_text() -> None:
    """Test that LazyTranslationImages handles None text in list."""
    texts = ["valid text", None, "another text"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)  # type: ignore

    # Accessing None text should handle gracefully
    # Either return None or raise appropriate error
    try:
        result = lazy[1]
        assert result is None
    except (TypeError, AttributeError):
        pass  # Also acceptable


def test_lazy_image_negative_index() -> None:
    """Test that LazyTranslationImages handles negative indices."""
    texts = ["text1", "text2", "text3"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)

    # Python negative indexing should work
    img = lazy[-1]
    assert img is not None


def test_lazy_image_out_of_bounds() -> None:
    """Test that LazyTranslationImages raises IndexError for out of bounds."""
    texts = ["text1", "text2"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)

    with pytest.raises(IndexError):
        _ = lazy[10]

    with pytest.raises(IndexError):
        _ = lazy[-10]


def test_lazy_image_render_all() -> None:
    """Test that render_all renders all images."""
    texts = ["text1", "text2"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)

    results = lazy.render_all()
    assert len(results) == 2
    # All should be rendered (not None if text is non-empty)
    assert results[0] is not None
    assert results[1] is not None


def test_lazy_image_caching() -> None:
    """Test that LazyTranslationImages caches rendered images."""
    texts = ["cached text"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)

    # First access should render
    img1 = lazy[0]
    # Second access should use cache
    img2 = lazy[0]

    # Should be exact same object (cached)
    assert img1 is img2


def test_lazy_image_invalid_config() -> None:
    """Test that LazyTranslationImages stores invalid config without error."""
    texts = ["text"]

    # LazyTranslationImages doesn't validate config at init time
    lazy = LazyTranslationImages(texts, None)  # type: ignore
    assert len(lazy) == 1
    # Accessing items will fail later when get_timage is called
