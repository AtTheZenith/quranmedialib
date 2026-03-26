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

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, NamedTuple

from PIL import Image, ImageFont

from quranmedialib.resources import get_font_path

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


# === Font Resource ===


@dataclass(frozen=True)
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


# === Database Configuration ===


@dataclass(frozen=True)
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
    ) -> DatabaseConfig:
        """Create a DatabaseConfig from an external database file path.

        Args:
            db_path: Path to the SQLite database file.
            tablename: Name of the table.
            surah_col: Surah column name.
            ayah_col: Ayah column name.
            text_col: Text column name.
        """
        return cls(
            filepath=Path(db_path),
            tablename=tablename,
            surah_col=surah_col,
            ayah_col=ayah_col,
            text_col=text_col,
        )


@dataclass(frozen=True)
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
    ) -> WbwDatabaseConfig:
        """Create a WbwDatabaseConfig from an external database file path."""
        return cls(
            filepath=Path(db_path),
            tablename=tablename,
            surah_col=surah_col,
            ayah_col=ayah_col,
            text_col=text_col,
            word_id_col=word_id_col,
        )


# === Data Transmission Types ===


@dataclass(frozen=True)
class WordItem:
    """Combines a word image with its text metadata for layout processing.

    Used by the framer to calculate line breaks and alignments.
    """

    image: Image.Image
    text: str | None = None

    @property
    def width(self) -> int:
        """Width of the word image in pixels."""
        return self.image.width

    @property
    def height(self) -> int:
        """Height of the word image in pixels."""
        return self.image.height


# === Configuration Types ===


@dataclass(frozen=True)
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
    padding: Padding = Padding(0, 0, 0, 0)
    wimage_x_offset: int = 0
    wimage_y_offset: int = 0
    timage_x_offset: int = 0
    timage_y_offset: int = 0
    timage_vertical_align: VerticalAlignment | str = VerticalAlignment.CENTER
    timage_horizontal_align: HorizontalAlignment | str = HorizontalAlignment.CENTER
    wimage_vertical_align: VerticalAlignment | str = VerticalAlignment.CENTER
    wimage_horizontal_align: HorizontalAlignment | str = HorizontalAlignment.CENTER

    def __post_init__(self):
        """Ensure string literals are converted to Enums where applicable."""
        if isinstance(self.timage_vertical_align, str):
            object.__setattr__(self, "timage_vertical_align", VerticalAlignment(self.timage_vertical_align.lower()))
        if isinstance(self.timage_horizontal_align, str):
            object.__setattr__(self, "timage_horizontal_align", HorizontalAlignment(self.timage_horizontal_align.lower()))
        if isinstance(self.wimage_vertical_align, str):
            object.__setattr__(self, "wimage_vertical_align", VerticalAlignment(self.wimage_vertical_align.lower()))
        if isinstance(self.wimage_horizontal_align, str):
            object.__setattr__(self, "wimage_horizontal_align", HorizontalAlignment(self.wimage_horizontal_align.lower()))
        if not isinstance(self.padding, Padding):
            object.__setattr__(self, "padding", Padding(*self.padding))

    @property
    def content_width(self) -> int:
        """Available width for layout (max_width - left_padding - right_padding)."""
        return self.max_width - self.padding.left - self.padding.right

    @property
    def available_height(self) -> int:
        """Available height for layout (image_height - top_padding - bottom_padding)."""
        return self.image_height - self.padding.top - self.padding.bottom


@dataclass(frozen=True, init=False)
class WordConfig:
    """Configuration for word and verse rendering behavior.

    Controls font sizes, spacing, colors, and specific verse-number styles.
    """

    font_size: int
    max_rows_per_page: int
    row_spacing: int
    word_spacing: int
    word_padding: Padding
    verse_v_offset: int
    balanced_wrapping: bool
    verse_number_size: int
    verse_number_padding: Padding
    verse_number_color: Color
    annotation_font_size: int
    word_color: Color
    annotation_color: Color
    annotation_font_path: Path
    background_color: Color

    def __init__(
        self,
        font_size: int,
        max_rows_per_page: int,
        row_spacing: int,
        word_spacing: int,
        word_padding: Padding | tuple[int, int, int, int] = (10, 10, 10, 10),
        verse_v_offset: int = 0,
        balanced_wrapping: bool = False,
        verse_number_size: int = 110,
        verse_number_padding: Padding | tuple[int, int, int, int] = (1, 41, 1, 1),
        verse_number_color: Color = (255, 255, 255, 255),
        annotation_font_size: int = 28,
        word_color: Color = (255, 255, 255, 255),
        annotation_color: Color = (255, 255, 255, 255),
        annotation_font_path: Path | str | FontResource | None = None,
        background_color: Color = (0, 0, 0, 0),
    ):
        """Initialize WordConfig with resolved paths and type-safe layout primitives."""
        # Resolve annotation_font_path
        if annotation_font_path is None:
            resolved_font_path = get_font_path("inter.ttf")
        elif isinstance(annotation_font_path, FontResource):
            resolved_font_path = annotation_font_path.path
        elif isinstance(annotation_font_path, str):
            resolved_font_path = Path(annotation_font_path)
        else:
            resolved_font_path = annotation_font_path

        # Resolve paddings
        word_padding = word_padding if isinstance(word_padding, Padding) else Padding(*word_padding)
        verse_number_padding = verse_number_padding if isinstance(verse_number_padding, Padding) else Padding(*verse_number_padding)

        object.__setattr__(self, "font_size", font_size)
        object.__setattr__(self, "max_rows_per_page", max_rows_per_page)
        object.__setattr__(self, "row_spacing", row_spacing)
        object.__setattr__(self, "word_spacing", word_spacing)
        object.__setattr__(self, "word_padding", word_padding)
        object.__setattr__(self, "verse_v_offset", verse_v_offset)
        object.__setattr__(self, "balanced_wrapping", balanced_wrapping)
        object.__setattr__(self, "verse_number_size", verse_number_size)
        object.__setattr__(self, "verse_number_padding", verse_number_padding)
        object.__setattr__(self, "verse_number_color", verse_number_color)
        object.__setattr__(self, "annotation_font_size", annotation_font_size)
        object.__setattr__(self, "word_color", word_color)
        object.__setattr__(self, "annotation_color", annotation_color)
        object.__setattr__(self, "annotation_font_path", resolved_font_path)
        object.__setattr__(self, "background_color", background_color)


@dataclass(frozen=True, init=False)
class TextConfig:
    """Configuration for translation/rich text rendering.

    Bold weight is applied via font variations (wght axis) during rendering.
    """

    font_size: int
    color: Color
    font_path: Path
    italic_font_path: Path
    line_spacing: int
    height: int | None
    max_width: int | None
    alignment: HorizontalAlignment

    def __init__(
        self,
        font_size: int = 36,
        color: Color = (255, 255, 255, 255),
        font_path: Path | str | FontResource | None = None,
        italic_font_path: Path | str | FontResource | None = None,
        line_spacing: int = 10,
        height: int | None = None,
        max_width: int | None = None,
        alignment: HorizontalAlignment | str = HorizontalAlignment.CENTER,
    ):
        """Initialize TextConfig with resolved font paths."""

        def _resolve_path(path: Path | str | FontResource | None, default_filename: str) -> Path:
            if path is None:
                return get_font_path(default_filename)
            return path.path if isinstance(path, FontResource) else Path(path)

        # Resolve alignment
        if isinstance(alignment, str):
            alignment = HorizontalAlignment(alignment.lower())

        object.__setattr__(self, "font_size", font_size)
        object.__setattr__(self, "color", color)
        object.__setattr__(self, "font_path", _resolve_path(font_path, "inter.ttf"))
        object.__setattr__(self, "italic_font_path", _resolve_path(italic_font_path, "inter_italic.ttf"))
        object.__setattr__(self, "line_spacing", line_spacing)
        object.__setattr__(self, "height", height)
        object.__setattr__(self, "max_width", max_width)
        object.__setattr__(self, "alignment", alignment)


# === Text Rendering Types ===


@dataclass(frozen=True)
class StyledWord:
    """A word with specific styling applied, ready for rendering."""

    text: str
    font: ImageFont.ImageFont
    color: Color
    width: int
    is_transparent: bool = False
    simulate_bold: bool = False


class Line:
    """A collection of styled words representing a single line of text."""

    def __init__(self):
        self.words: list[StyledWord] = []
        self.width: int = 0

    def add_word(self, word: StyledWord, space_width: int):
        """Adds a word to the line, accounting for word spacing."""
        if self.words:
            self.width += space_width
        self.words.append(word)
        self.width += word.width
