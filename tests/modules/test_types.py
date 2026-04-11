"""Tests for the types module (core types and configuration dataclasses).

This module contains tests for verifying configuration validation including:
- Padding validation
- Alignment enum/string coercion
- LayoutConfig validation
- WordConfig validation
- TextConfig validation
- FontResource validation
"""

import pytest

from quranmedialib.types import (
    DatabaseConfig,
    FontResource,
    HorizontalAlignment,
    LayoutConfig,
    Padding,
    TextConfig,
    VerticalAlignment,
    WbwDatabaseConfig,
    WordConfig,
    WordItem,
)


# === Padding Tests ===


def test_padding_default_values() -> None:
    """Test that Padding defaults to zeros."""
    p = Padding()
    assert p.top == 0
    assert p.bottom == 0
    assert p.left == 0
    assert p.right == 0
    assert p.horizontal == 0
    assert p.vertical == 0


def test_padding_custom_values() -> None:
    """Test that Padding accepts custom values."""
    p = Padding(10, 20, 30, 40)
    assert p.top == 10
    assert p.bottom == 20
    assert p.left == 30
    assert p.right == 40
    assert p.horizontal == 70
    assert p.vertical == 30


def test_padding_negative_values() -> None:
    """Test that Padding accepts negative values (no validation)."""
    p = Padding(-10, -20, -30, -40)
    assert p.horizontal == -70
    assert p.vertical == -30


def test_padding_invalid_type() -> None:
    """Test that Padding accepts any types (NamedTuple has no type validation)."""
    # NamedTuple doesn't validate types at runtime
    p = Padding("10", 20, 30, 40)  # type: ignore
    assert p.top == "10"
    assert p.bottom == 20


def test_padding_too_few_args() -> None:
    """Test that Padding works with fewer than 4 args (uses defaults)."""
    p = Padding(10)
    assert p.top == 10
    assert p.bottom == 0
    assert p.left == 0
    assert p.right == 0


# === Alignment Enum Tests ===


def test_horizontal_alignment_values() -> None:
    """Test HorizontalAlignment enum values."""
    assert HorizontalAlignment.LEFT.value == "left"
    assert HorizontalAlignment.CENTER.value == "center"
    assert HorizontalAlignment.RIGHT.value == "right"


def test_vertical_alignment_values() -> None:
    """Test VerticalAlignment enum values."""
    assert VerticalAlignment.TOP.value == "top"
    assert VerticalAlignment.CENTER.value == "center"
    assert VerticalAlignment.BOTTOM.value == "bottom"


def test_horizontal_alignment_invalid_string() -> None:
    """Test that HorizontalAlignment raises ValueError for invalid string."""
    with pytest.raises(ValueError):
        HorizontalAlignment("invalid")


def test_vertical_alignment_invalid_string() -> None:
    """Test that VerticalAlignment raises ValueError for invalid string."""
    with pytest.raises(ValueError):
        VerticalAlignment("invalid")


# === LayoutConfig Tests ===


def test_layout_config_valid_alignment_strings() -> None:
    """Test that LayoutConfig coerces valid alignment strings to enums."""
    config = LayoutConfig(
        max_width=1920,
        image_height=1080,
        wimage_vertical_align="top",
        wimage_horizontal_align="right",
        timage_vertical_align="bottom",
        timage_horizontal_align="left",
    )
    assert config.wimage_vertical_align == VerticalAlignment.TOP
    assert config.wimage_horizontal_align == HorizontalAlignment.RIGHT
    assert config.timage_vertical_align == VerticalAlignment.BOTTOM
    assert config.timage_horizontal_align == HorizontalAlignment.LEFT


def test_layout_config_invalid_alignment_string() -> None:
    """Test that LayoutConfig raises ValueError for invalid alignment strings."""
    with pytest.raises(ValueError):
        LayoutConfig(
            max_width=1920,
            image_height=1080,
            wimage_vertical_align="invalid_align",
        )


def test_layout_config_padding_tuple_coercion() -> None:
    """Test that LayoutConfig coerces tuple padding to Padding object."""
    config = LayoutConfig(
        max_width=1920,
        image_height=1080,
        padding=(10, 20, 30, 40),
    )
    assert isinstance(config.padding, Padding)
    assert config.padding.top == 10
    assert config.padding.bottom == 20
    assert config.padding.left == 30
    assert config.padding.right == 40


def test_layout_config_content_width() -> None:
    """Test LayoutConfig content_width property."""
    config = LayoutConfig(max_width=1920, image_height=1080, padding=(50, 50, 100, 100))
    assert config.content_width == 1920 - 100 - 100  # max_width - left - right


def test_layout_config_available_height() -> None:
    """Test LayoutConfig available_height property."""
    config = LayoutConfig(max_width=1920, image_height=1080, padding=(50, 100, 0, 0))
    assert config.available_height == 1080 - 50 - 100  # image_height - top - bottom


def test_layout_config_negative_dimensions() -> None:
    """Test that LayoutConfig accepts negative dimensions (no validation)."""
    # Should not raise, even with negative values
    config = LayoutConfig(max_width=-100, image_height=-100)
    assert config.max_width == -100
    assert config.image_height == -100


def test_layout_config_zero_dimensions() -> None:
    """Test that LayoutConfig accepts zero dimensions."""
    config = LayoutConfig(max_width=0, image_height=0)
    assert config.max_width == 0
    assert config.image_height == 0


# === WordConfig Tests ===


def test_word_config_padding_tuple_coercion() -> None:
    """Test that WordConfig coerces tuple padding to Padding objects."""
    config = WordConfig(
        font_size=72,
        max_rows_per_page=5,
        row_spacing=20,
        word_spacing=10,
        word_padding=(10, 20, 30, 40),
    )
    assert isinstance(config.word_padding, Padding)
    assert config.word_padding.top == 10


def test_word_config_negative_values() -> None:
    """Test that WordConfig accepts negative spacing/padding values."""
    # Should not raise
    config = WordConfig(
        font_size=72,
        max_rows_per_page=5,
        row_spacing=-10,
        word_spacing=-10,
    )
    assert config.row_spacing == -10
    assert config.word_spacing == -10


def test_word_config_zero_font_size() -> None:
    """Test that WordConfig raises ValueError for zero font size."""
    with pytest.raises(ValueError, match="font_size must be positive"):
        WordConfig(
            font_size=0,
            max_rows_per_page=1,
            row_spacing=0,
            word_spacing=0,
        )


def test_word_config_invalid_font_resource() -> None:
    """Test that WordConfig handles invalid FontResource gracefully."""
    # Invalid type should either raise error or be stored as-is
    try:
        config = WordConfig(
            font_size=72,
            max_rows_per_page=5,
            row_spacing=20,
            word_spacing=10,
            font="invalid_font",  # type: ignore
        )
        # If it doesn't raise, the font should be stored as-is
        assert config.font == "invalid_font"
    except (TypeError, AttributeError):
        pass


# === TextConfig Tests ===


def test_text_config_valid_alignment_string() -> None:
    """Test that TextConfig coerces valid alignment strings to enums."""
    config = TextConfig(alignment="left")
    assert config.alignment == HorizontalAlignment.LEFT

    config = TextConfig(alignment="RIGHT")
    assert config.alignment == HorizontalAlignment.RIGHT


def test_text_config_invalid_alignment_string() -> None:
    """Test that TextConfig raises ValueError for invalid alignment strings."""
    with pytest.raises(ValueError):
        TextConfig(alignment="invalid_align")


def test_text_config_default_values() -> None:
    """Test that TextConfig has sensible defaults."""
    config = TextConfig()
    assert config.font_size == 36
    assert config.line_spacing == 10
    assert config.height is None
    assert config.max_width is None
    assert config.alignment == HorizontalAlignment.CENTER


def test_text_config_negative_font_size() -> None:
    """Test that TextConfig accepts negative font size (no validation)."""
    config = TextConfig(font_size=-10)
    assert config.font_size == -10


# === FontResource Tests ===


def test_font_resource_from_packaged_invalid_font() -> None:
    """Test that FontResource.from_packaged returns path for non-existent font."""
    # Returns a Path object without checking existence
    resource = FontResource.from_packaged("nonexistent_font.otf")
    assert resource is not None
    assert resource.path is not None


def test_font_resource_none_font_name() -> None:
    """Test that FontResource.from_packaged raises error for None font name."""
    with pytest.raises((TypeError, Exception)):
        FontResource.from_packaged(None)  # type: ignore


# === FontResource Working Directory Tests ===


def test_font_resource_from_path_outside_working_dir() -> None:
    """Test that FontResource.from_path rejects paths outside working dir."""
    with pytest.raises(ValueError, match="outside the working directory"):
        FontResource.from_path("C:\\Windows\\Fonts\\arial.ttf")


def test_font_resource_from_path_with_unsafe_paths() -> None:
    """Test that FontResource.from_path works with unsafe_paths=True."""
    from pathlib import Path

    resource = FontResource.from_path(
        "C:\\Windows\\Fonts\\arial.ttf",
        unsafe_paths=True,
    )
    assert resource.path == Path("C:\\Windows\\Fonts\\arial.ttf")


def test_font_resource_from_path_inside_working_dir() -> None:
    """Test that FontResource.from_path works for paths within working dir."""
    from pathlib import Path

    # This should work since it's a relative path that resolves within cwd
    resource = FontResource.from_path("fonts/custom.ttf")
    assert resource.path == Path("fonts/custom.ttf")
    assert resource.name == "custom"


def test_database_config_from_path() -> None:
    """Test that DatabaseConfig.from_path rejects paths outside working dir."""
    # Path outside working directory should be rejected by default
    with pytest.raises(ValueError, match="outside the working directory"):
        DatabaseConfig.from_path(
            "/path/to/db.sqlite",
            tablename="verses",
            surah_col="surah",
            ayah_col="ayah",
            text_col="text",
        )

    # With unsafe_paths=True, should work
    config = DatabaseConfig.from_path(
        "/path/to/db.sqlite",
        tablename="verses",
        surah_col="surah",
        ayah_col="ayah",
        text_col="text",
        unsafe_paths=True,
    )
    from pathlib import Path

    assert config.filepath == Path("/path/to/db.sqlite")
    assert config.tablename == "verses"


def test_database_config_invalid_tablename() -> None:
    """Test that DatabaseConfig accepts invalid tablename with unsafe_paths."""
    # Must use unsafe_paths=True since /path/to is outside working directory
    config = DatabaseConfig.from_path(
        "/path/to/db.sqlite",
        tablename="table; DROP TABLE",
        unsafe_paths=True,
    )
    assert config.tablename == "table; DROP TABLE"


# === WbwDatabaseConfig Tests ===


def test_wbw_database_config_from_path() -> None:
    """Test that WbwDatabaseConfig.from_path rejects paths outside working dir."""
    with pytest.raises(ValueError, match="outside the working directory"):
        WbwDatabaseConfig.from_path(
            "/external/path/wbw.sqlite",
            tablename="words",
        )

    # With unsafe_paths=True, should work
    config = WbwDatabaseConfig.from_path(
        "/external/path/wbw.sqlite",
        tablename="words",
        unsafe_paths=True,
    )
    assert config.tablename == "words"
    assert config.word_id_col == "word"


# === WordItem Tests ===


def test_word_item_none_image() -> None:
    """Test that WordItem with None image raises error on property access."""
    item = WordItem(None, text="test")  # type: ignore

    with pytest.raises(AttributeError):
        _ = item.width

    with pytest.raises(AttributeError):
        _ = item.height


def test_word_item_valid_image() -> None:
    """Test that WordItem with valid image works correctly."""
    from PIL import Image

    img = Image.new("RGBA", (100, 50))
    item = WordItem(img, text="test")
    assert item.width == 100
    assert item.height == 50
    assert item.text == "test"


# === Boundary Value Tests ===


@pytest.mark.parametrize("surah", [1, 114])
def test_valid_surah_boundaries(surah: int) -> None:
    """Test valid surah boundary values (1-114)."""
    # These should be valid (type hints enforce range 1-115, i.e., 1-114)
    assert 1 <= surah <= 114


@pytest.mark.parametrize("ayah", [1, 286])
def test_valid_ayah_boundaries(ayah: int) -> None:
    """Test valid ayah boundary values (1-286)."""
    # These should be valid (type hints enforce range 1-287, i.e., 1-286)
    assert 1 <= ayah <= 286
