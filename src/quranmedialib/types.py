"""Core types and configuration dataclasses for QuranMediaLib.

This module defines all configuration classes, database mappings, and data
structures used throughout the library. It includes:

- FontResource: Reference to a font file with metadata
- DatabaseConfig: Configuration for verse-by-verse database tables
- WbwDatabaseConfig: Extended config for word-by-word databases
- LayoutConfig, WordConfig, TextConfig: Rendering configuration
- WordItem, StyledWord, Line: Data transmission types
- Padding, Alignment: Type-safe layout primitives
"""

from __future__ import annotations

import bisect
import os
import os.path
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Annotated, NamedTuple

from PIL import Image, ImageFont

from quranmedialib.exceptions import ResourceError, ValidationError
from quranmedialib.resources import get_font_path

# === Exceptions ===


class QuranMediaLibError(Exception):
    """Base class for all QuranMediaLib exceptions."""


class LayoutError(QuranMediaLibError):
    """Raised when rendering dimensions or layouts are invalid."""


class DatabaseError(QuranMediaLibError):
    """Raised when database operations fail or schema is invalid."""


class ResourceError(QuranMediaLibError):
    """Raised when external assets (fonts, DBs) cannot be loaded."""


# Maximum font size limit to prevent decompression bomb attacks and excessive memory usage
MAX_FONT_SIZE = 2000

# Cached working directory — resolved lazily on first use to avoid stale os.getcwd()
_working_dir_cache: Path | None = None


def _get_working_dir() -> Path:
    """Return the working directory, caching on first call."""
    global _working_dir_cache
    if _working_dir_cache is None:
        _working_dir_cache = Path(os.getcwd()).resolve()
    return _working_dir_cache


def _ensure_within_working_dir(path: Path) -> None:
    """Validate that a path is within the working directory tree.

    Uses realpath to prevent prefix-matching bypasses and symlink traversal.

    Args:
        path: The path to validate.

    Raises:
        ResourceError: If the path is outside the working directory.
    """
    try:
        # resolve() is more robust on Windows/Python 3.10+
        resolved = path.resolve()
        working = _get_working_dir()

        # Check if resolved path is actually under the working directory
        if not str(resolved).startswith(str(working) + os.sep) and str(resolved) != str(working):
            raise ResourceError(f"Path {path!r} (resolved: {resolved!r}) is outside the working directory {working}.")
    except (OSError, ValueError) as e:
        raise ResourceError(f"Failed to validate path {path}: {e}")


# === Layout Primitives ===


class Padding(NamedTuple):
    """Container for 4-directional padding values (CSS/PIL order)."""

    top: int = 0
    bottom: int = 0
    left: int = 0
    right: int = 0

    @property
    def horizontal(self) -> int:
        """Total horizontal padding."""
        return self.left + self.right

    @property
    def vertical(self) -> int:
        """Total vertical padding."""
        return self.top + self.bottom


class HorizontalAlignment(Enum):
    """Options for horizontal content anchoring."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class VerticalAlignment(Enum):
    """Options for vertical content anchoring."""

    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


# === Type Aliases ===
# Maintained for backward compatibility and semantic clarity.
type Color = tuple[int, int, int] | tuple[int, int, int, int]
type SurahNumber = Annotated[int, range(1, 115)]
type AyahNumber = Annotated[int, range(1, 287)]
type WordIndex = int
type FontSize = Annotated[int, range(1, MAX_FONT_SIZE + 1)]


# === Font Resource ===


@dataclass(frozen=True, slots=True)
class FontResource:
    """Reference to a font file with metadata.

    Attributes:
        name: Human-readable name for the font (e.g., "Hafs", "Inter").
        path: Absolute path to the font file. Can be resolved via get_font_path()
            for packaged fonts, or a user-provided custom path.
    """

    name: str
    path: Path

    @classmethod
    def from_packaged(cls, font_name: str, display_name: str | None = None) -> FontResource:
        """Create a FontResource from a packaged font file.

        Args:
            font_name: Filename of the font in the assets directory.
            display_name: Optional display name. Defaults to font_name without extension.

        Returns:
            FontResource with resolved path.
        """
        if display_name is None:
            display_name = Path(font_name).stem
        return cls(name=display_name, path=get_font_path(font_name))

    @classmethod
    def from_path(
        cls,
        font_path: str | Path,
        display_name: str | None = None,
        unsafe_paths: bool = False,
    ) -> FontResource:
        """Create a FontResource from a custom font file path.

        Args:
            font_path: Path to the font file.
            display_name: Optional display name. Defaults to filename stem.
            unsafe_paths: If True, bypass working directory validation.
                **Warning**: Setting this to True allows access to files
                outside the working directory. Only use with trusted paths.

        Returns:
            FontResource with the specified path.

        Raises:
            ValueError: If font_path is outside the working directory and
                unsafe_paths is False.
        """
        font_path_obj = Path(font_path)
        if not unsafe_paths:
            _ensure_within_working_dir(font_path_obj)

        if display_name is None:
            display_name = font_path_obj.stem

        return cls(name=display_name, path=font_path_obj)


# === Database Configuration ===


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Configuration for a verse-by-verse database table.

    This config maps logical fields (surah, ayah, text) to actual database
    columns, allowing the DatabaseManager to work with varied schemas.

    Attributes:
        filepath: Path to the SQLite database file.
        tablename: Name of the table containing verse data.
        surah_col: Column name for surah number.
        ayah_col: Column name for ayah (verse) number.
        text_col: Column name for the text content.
    """

    filepath: Path
    tablename: str
    surah_col: str
    ayah_col: str
    text_col: str

    @classmethod
    def from_packaged(
        cls,
        db_name: str,
        tablename: str,
        surah_col: str = "sura",
        ayah_col: str = "ayah",
        text_col: str = "text",
    ) -> DatabaseConfig:
        """Create a DatabaseConfig for a packaged database file.

        Args:
            db_name: Filename of the database in the assets directory.
            tablename: Name of the table containing verse data.
            surah_col: Column name for surah. Defaults to "sura".
            ayah_col: Column name for ayah. Defaults to "ayah".
            text_col: Column name for text. Defaults to "text".

        Returns:
            Config with resolved absolute path.
        """
        from quranmedialib.resources import get_db_path

        return cls(
            filepath=get_db_path(db_name),
            tablename=tablename,
            surah_col=surah_col,
            ayah_col=ayah_col,
            text_col=text_col,
        )

    @classmethod
    def from_path(
        cls,
        db_path: str | Path,
        tablename: str,
        surah_col: str = "sura",
        ayah_col: str = "ayah",
        text_col: str = "text",
        unsafe_paths: bool = False,
        trust_config: bool = False,
    ) -> DatabaseConfig:
        """Create a DatabaseConfig from an external database file path.

        Args:
            db_path: Path to the SQLite database file.
            tablename: Name of the table.
            surah_col: Surah column name.
            ayah_col: Ayah column name.
            text_col: Text column name.
            unsafe_paths: If True, bypass working directory validation.
                **Warning**: Setting this to True allows access to files
                outside the working directory. Only use with trusted paths.
            trust_config: If True, accept custom table/column names without
                additional schema validation. When False (default), the
                DatabaseManager validates identifiers against SQL injection.

        Raises:
            ValueError: If db_path is outside the working directory and
                unsafe_paths is False.
        """
        db_path_obj = Path(db_path)
        if not unsafe_paths:
            _ensure_within_working_dir(db_path_obj)

        return cls(
            filepath=db_path_obj,
            tablename=tablename,
            surah_col=surah_col,
            ayah_col=ayah_col,
            text_col=text_col,
        )


@dataclass(frozen=True, slots=True)
class WbwDatabaseConfig(DatabaseConfig):
    """Extended configuration for word-by-word databases.

    Attributes:
        word_id_col: Column name for the word index/ID within the verse.
    """

    word_id_col: str = "word"

    @classmethod
    def from_packaged(
        cls,
        db_name: str,
        tablename: str,
        surah_col: str = "surah",
        ayah_col: str = "ayah",
        text_col: str = "translation",
        word_id_col: str = "word",
    ) -> WbwDatabaseConfig:
        """Create a WbwDatabaseConfig for a packaged word-by-word database."""
        from quranmedialib.resources import get_db_path

        return cls(
            filepath=get_db_path(db_name),
            tablename=tablename,
            surah_col=surah_col,
            ayah_col=ayah_col,
            text_col=text_col,
            word_id_col=word_id_col,
        )

    @classmethod
    def from_path(
        cls,
        db_path: str | Path,
        tablename: str,
        surah_col: str = "surah",
        ayah_col: str = "ayah",
        text_col: str = "translation",
        word_id_col: str = "word",
        unsafe_paths: bool = False,
        trust_config: bool = False,
    ) -> WbwDatabaseConfig:
        """Create a WbwDatabaseConfig from an external database file path.

        Args:
            db_path: Path to the SQLite database file.
            tablename: Name of the table.
            surah_col: Surah column name.
            ayah_col: Ayah column name.
            text_col: Text column name.
            word_id_col: Word ID column name.
            unsafe_paths: If True, bypass working directory validation.
                **Warning**: Setting this to True allows access to files
                outside the working directory. Only use with trusted paths.
            trust_config: If True, accept custom table/column names without
                additional schema validation. When False (default), the
                DatabaseManager validates identifiers against SQL injection.

        Raises:
            ValueError: If db_path is outside the working directory and
                unsafe_paths is False.
        """
        db_path_obj = Path(db_path)
        if not unsafe_paths:
            _ensure_within_working_dir(db_path_obj)

        return cls(
            filepath=db_path_obj,
            tablename=tablename,
            surah_col=surah_col,
            ayah_col=ayah_col,
            text_col=text_col,
            word_id_col=word_id_col,
        )


# === Data Transmission Types ===


@dataclass(frozen=True, slots=True)
class WordItem:
    """Combines a word image with its text metadata for layout processing.

    Used by the framer to calculate line breaks and alignments.
    """

    image: Image.Image
    text: str | None = None
    color: Color | None = None
    width: int = field(init=False)
    height: int = field(init=False)

    def __post_init__(self):
        """Pre-calculate image dimensions to speed up layout loops."""
        if self.image is not None:
            # Use object.__setattr__ because the dataclass is frozen
            object.__setattr__(self, "width", self.image.width)
            object.__setattr__(self, "height", self.image.height)


# === Configuration Types ===


@dataclass(frozen=True, slots=True)
class LayoutConfig:
    """Stores canvas sizing and top-level layout offsets.

    Attributes:
        max_width: Total canvas width in pixels.
        image_height: Total canvas height in pixels.
        padding: Internal canvas margins (top, bottom, left, right).
        wimage_x_offset: Additional X offset for word images.
        wimage_y_offset: Additional Y offset for word images.
        timage_x_offset: Additional X offset for translation images.
        timage_y_offset: Additional Y offset for translation images.
        timage_vertical_align: Vertical alignment for translation text.
        timage_horizontal_align: Horizontal alignment for translation text.
        wimage_vertical_align: Vertical alignment for Arabic word block.
        wimage_horizontal_align: Horizontal alignment for Arabic word block.
    """

    max_width: int
    image_height: int
    padding: Padding = field(default_factory=Padding)
    wimage_x_offset: int = 0
    wimage_y_offset: int = 0
    timage_x_offset: int = 0
    timage_y_offset: int = 0
    timage_vertical_align: VerticalAlignment | str = VerticalAlignment.CENTER
    timage_horizontal_align: HorizontalAlignment | str = HorizontalAlignment.CENTER
    wimage_vertical_align: VerticalAlignment | str = VerticalAlignment.CENTER
    wimage_horizontal_align: HorizontalAlignment | str = HorizontalAlignment.CENTER

    def __post_init__(self):
        """Ensure string literals are converted to Enums, validate dimensions."""
        if isinstance(self.timage_vertical_align, str):
            object.__setattr__(self, "timage_vertical_align", VerticalAlignment(self.timage_vertical_align.lower()))
        if isinstance(self.timage_horizontal_align, str):
            object.__setattr__(
                self, "timage_horizontal_align", HorizontalAlignment(self.timage_horizontal_align.lower())
            )
        if isinstance(self.wimage_vertical_align, str):
            object.__setattr__(self, "wimage_vertical_align", VerticalAlignment(self.wimage_vertical_align.lower()))
        if isinstance(self.wimage_horizontal_align, str):
            object.__setattr__(
                self, "wimage_horizontal_align", HorizontalAlignment(self.wimage_horizontal_align.lower())
            )
        if not isinstance(self.padding, Padding):
            try:
                object.__setattr__(self, "padding", Padding(*self.padding))
            except (TypeError, ValueError):
                object.__setattr__(self, "padding", Padding())

        # Validate dimensions
        if self.max_width <= 0:
            raise ValidationError(f"max_width must be positive, got {self.max_width}")
        if self.image_height <= 0:
            raise ValidationError(f"image_height must be positive, got {self.image_height}")

        if self.content_width <= 0:
            raise ValidationError(
                f"LayoutConfig content_width must be positive, got {self.content_width}. "
                f"(max_width={self.max_width}, padding.left={self.padding.left}, padding.right={self.padding.right})"
            )

    @property
    def content_width(self) -> int:
        """Available width for layout (max_width - left_padding - right_padding)."""
        return self.max_width - self.padding.left - self.padding.right

    @property
    def available_height(self) -> int:
        """Available height for layout (image_height - top_padding - bottom_padding)."""
        return self.image_height - self.padding.top - self.padding.bottom


@dataclass(frozen=True, slots=True)
class WordConfig:
    """Configuration for word and verse rendering behavior.

    Controls font sizes, spacing, colors, and specific verse-number styles.
    """

    font_size: FontSize
    max_rows_per_page: int = 5
    row_spacing: int = 20
    word_spacing: int = 10
    word_padding: Padding | tuple[int, int, int, int] = field(default_factory=lambda: Padding(10, 10, 10, 10))
    verse_v_offset: int = 0
    balanced_wrapping: bool = False
    verse_number_size: int = 110
    verse_number_padding: Padding | tuple[int, int, int, int] = field(default_factory=lambda: Padding(1, 41, 1, 1))
    verse_number_color: Color = (255, 255, 255, 255)
    annotation_font_size: int = 28
    word_color: Color = (255, 255, 255, 255)
    annotation_color: Color = (255, 255, 255, 255)
    annotation_font_path: Path | str | FontResource | None = None
    background_color: Color = (0, 0, 0, 0)
    font: FontResource | None = None

    def __post_init__(self):
        """Validate parameters and resolve defaults."""
        from quranmedialib.presets import FONT_HAFS

        # Validate font sizes
        for name, size in [
            ("font_size", self.font_size),
            ("annotation_font_size", self.annotation_font_size),
            ("verse_number_size", self.verse_number_size),
        ]:
            if size <= 0:
                raise ValidationError(f"{name} must be positive, got {size}")
            if size > MAX_FONT_SIZE:
                raise ValidationError(f"{name} exceeds maximum limit of {MAX_FONT_SIZE}, got {size}")

        if self.max_rows_per_page <= 0:
            raise ValidationError(f"max_rows_per_page must be positive, got {self.max_rows_per_page}")

        # Resolve defaults
        if self.font is None:
            object.__setattr__(self, "font", FONT_HAFS)

        # Resolve annotation font path
        if self.annotation_font_path is None:
            object.__setattr__(self, "annotation_font_path", get_font_path("inter.ttf"))
        elif isinstance(self.annotation_font_path, FontResource):
            object.__setattr__(self, "annotation_font_path", self.annotation_font_path.path)
        elif isinstance(self.annotation_font_path, str):
            object.__setattr__(self, "annotation_font_path", Path(self.annotation_font_path))

        # Coerce paddings
        if not isinstance(self.word_padding, Padding):
            object.__setattr__(self, "word_padding", Padding(*self.word_padding))
        if not isinstance(self.verse_number_padding, Padding):
            object.__setattr__(self, "verse_number_padding", Padding(*self.verse_number_padding))


@dataclass(frozen=True, slots=True)
class TextConfig:
    """Configuration for translation/rich text rendering.

    Bold weight is applied via font variations (wght axis) during rendering.
    """

    font_size: FontSize = 36
    color: Color = (255, 255, 255, 255)
    font_path: Path | str | FontResource | None = None
    italic_font_path: Path | str | FontResource | None = None
    line_spacing: int = 10
    height: int | None = None
    max_width: int | None = None
    alignment: HorizontalAlignment | str = HorizontalAlignment.CENTER
    balanced_wrapping: bool = True
    highlight_font_path: Path | str | FontResource | None = None
    highlight_font_size: int | None = None
    highlight_color: Color | None = None

    def __post_init__(self):
        """Validate parameters and resolve defaults."""

        def _resolve_path(path: Path | str | FontResource | None, default_filename: str) -> Path:
            if path is None:
                return get_font_path(default_filename)
            if isinstance(path, FontResource):
                return path.path
            return Path(path)

        # Coerce alignment
        if isinstance(self.alignment, str):
            object.__setattr__(self, "alignment", HorizontalAlignment(self.alignment.lower()))

        # Validate font_size
        if self.font_size <= 0:
            raise ValidationError(f"font_size must be positive, got {self.font_size}")
        if self.font_size > MAX_FONT_SIZE:
            raise ValidationError(f"font_size exceeds maximum limit of {MAX_FONT_SIZE}, got {self.font_size}")

        # Validate max_width
        if self.max_width is not None and self.max_width <= 0:
            raise ValidationError(f"max_width must be positive when provided, got {self.max_width}")

        # Resolve paths
        object.__setattr__(self, "font_path", _resolve_path(self.font_path, "inter.ttf"))
        object.__setattr__(self, "italic_font_path", _resolve_path(self.italic_font_path, "inter_italic.ttf"))
        object.__setattr__(self, "highlight_font_path", _resolve_path(self.highlight_font_path, "inter.ttf"))

        # Resolve highlight defaults
        if self.highlight_font_size is None:
            object.__setattr__(self, "highlight_font_size", self.font_size)
        if self.highlight_color is None:
            object.__setattr__(self, "highlight_color", (255, 215, 0, 255))
