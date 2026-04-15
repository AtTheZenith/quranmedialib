"""Tests for the lazy_image module.

This module contains tests for verifying lazy image rendering functionality including:
- Lazy evaluation (images rendered only when accessed)
- Caching behavior
- Sequence protocol implementation
"""

import pytest

from quranmedialib.modules.lazy_image import LazyTranslationImages
from quranmedialib.types import TextConfig


def test_lazy_image_init() -> None:
    """Test that LazyTranslationImages initializes correctly."""
    from quranmedialib.modules.lazy_image import _NOT_RENDERED

    texts = ["text1", "text2", "text3"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)

    assert len(lazy) == 3
    assert lazy._cache == [_NOT_RENDERED, _NOT_RENDERED, _NOT_RENDERED]


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
    """Test that LazyTranslationImages rejects negative indices."""
    texts = ["text1", "text2", "text3"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)

    # Negative indexing is no longer supported to prevent silent data corruption
    with pytest.raises(IndexError, match="negative index"):
        _ = lazy[-1]


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


def test_lazy_image_negative_index_minus_two() -> None:
    """Test that negative index -2 is also rejected."""
    texts = ["text1", "text2", "text3"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)
    with pytest.raises(IndexError):
        _ = lazy[-2]


def test_lazy_image_iteration() -> None:
    """Test that iterating over LazyTranslationImages yields images."""
    texts = ["text0", "text1", "text2"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)
    count = 0
    for img in lazy:
        count += 1
        assert img is not None
    assert count == 3


def test_lazy_image_slice_access() -> None:
    """Test that slice access works correctly."""
    texts = ["text0", "text1", "text2", "text3", "text4"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)
    # Slicing should return a list (Sequence.__getitem__ for slice)
    slice_result = lazy[1:3]
    assert len(slice_result) == 2
    assert all(img is not None for img in slice_result)


def test_lazy_image_len() -> None:
    """Test that len() returns the correct count."""
    texts = ["text0", "text1", "text2", "text3", "text4"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)
    assert len(lazy) == 5

    lazy_empty = LazyTranslationImages([], TextConfig())
    assert len(lazy_empty) == 0


def test_lazy_image_cache_none_for_empty_text() -> None:
    """Test that None text in list results in None cached value."""
    texts = ["valid text", None, "also valid"]
    config = TextConfig()
    lazy = LazyTranslationImages(texts, config)  # type: ignore
    result = lazy[1]
    assert result is None
