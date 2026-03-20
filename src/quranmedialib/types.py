"""Core types and configuration dataclasses for QuranMediaLib.

This module defines all configuration classes, database mappings, and data
structures used throughout the library. It includes:

- FontResource: Reference to a font file with metadata
- DatabaseConfig: Configuration for verse-by-verse database tables
- WbwDatabaseConfig: Extended config for word-by-word databases
- LayoutConfig, WordConfig, TextConfig: Rendering configuration
- WordItem, StyledWord, Line: Data transmission types
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

from PIL import Image, ImageFont

from quranmedialib.resources import get_font_path

# === Basic Type Aliases ===
type Color = tuple[int, int, int] | tuple[int, int, int, int]
type Padding = tuple[int, int, int, int]

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

    This config maps the logical fields (surah, ayah, text) to actual
    database table and column names, allowing the DatabaseManager to
    work with any compatible SQLite database.

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
        cls, db_name: str, tablename: str, surah_col: str = "sura", ayah_col: str = "ayah", text_col: str = "text"
    ) -> DatabaseConfig:
        """Create a DatabaseConfig for a packaged database file.

        Args:
            db_name: Filename of the database in the assets directory.
            tablename: Name of the table containing verse data.
            surah_col: Column name for surah number. Defaults to "sura".
            ayah_col: Column name for ayah number. Defaults to "ayah".
            text_col: Column name for text content. Defaults to "text".

        Returns:
            DatabaseConfig with resolved path.
        """
        from quranmedialib.resources import get_db_path

        return cls(
            filepath=get_db_path(db_name),
            tablename=tablename,
            surah_col=surah_col,
            ayah_col=ayah_col,
            text_col=text_col,
        )


@dataclass(frozen=True)
class WbwDatabaseConfig(DatabaseConfig):
    """Extended configuration for word-by-word databases.

    Inherits all fields from DatabaseConfig and adds word-level column mapping.

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
        """Create a WbwDatabaseConfig for a packaged word-by-word database.

        Args:
            db_name: Filename of the database in the assets directory.
            tablename: Name of the table containing word-by-word data.
            surah_col: Column name for surah number. Defaults to "surah".
            ayah_col: Column name for ayah number. Defaults to "ayah".
            text_col: Column name for translation text. Defaults to "translation".
            word_id_col: Column name for word index. Defaults to "word".

        Returns:
            WbwDatabaseConfig with resolved path.
        """
        from quranmedialib.resources import get_db_path

        return cls(
            filepath=get_db_path(db_name),
            tablename=tablename,
            surah_col=surah_col,
            ayah_col=ayah_col,
            text_col=text_col,
            word_id_col=word_id_col,
        )


# === Data Transmission Types ===
@dataclass(frozen=True)
class WordItem:
    """Combines a word image with its text metadata for layout processing."""

    image: Image.Image
    text: str | None = None

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height


# === Configuration Types ===
@dataclass(frozen=True)
class LayoutConfig:
    """Helper class to store canvas and top-level layout configuration."""

    max_width: int
    image_height: int
    padding: Padding = (0, 0, 0, 0)
    wimage_x_offset: int = 0
    wimage_y_offset: int = 0
    timage_x_offset: int = 0
    timage_y_offset: int = 0
    timage_vertical_align: str = "center"
    timage_horizontal_align: str = "center"
    wimage_vertical_align: str = "center"
    wimage_horizontal_align: str = "center"

    @property
    def content_width(self) -> int:
        """The available width for horizontal layout (max_width - left - right)."""
        return self.max_width - self.padding[2] - self.padding[3]

    @property
    def available_height(self) -> int:
        """The available height for vertical layout (height - top - bottom)."""
        return self.image_height - self.padding[0] - self.padding[1]


@dataclass(frozen=True)
class WordConfig:
    """Configuration for word and verse layout behavior."""

    font_size: int
    max_rows_per_page: int
    row_spacing: int
    word_spacing: int
    word_padding: Padding = (10, 10, 10, 10)
    verse_v_offset: int = 0
    balanced_wrapping: bool = False
    verse_number_size: int = 110
    verse_number_padding: Padding = (1, 41, 1, 1)
    verse_number_color: Color = (255, 255, 255, 255)
    annotation_font_size: int = 28
    word_color: Color = (255, 255, 255, 255)
    annotation_color: Color = (255, 255, 255, 255)
    annotation_font_path: Path | None = field(default=None, init=False)
    background_color: Color = (0, 0, 0, 0)

    def __init__(
        self,
        font_size: int,
        max_rows_per_page: int,
        row_spacing: int,
        word_spacing: int,
        word_padding: Padding = (10, 10, 10, 10),
        verse_v_offset: int = 0,
        balanced_wrapping: bool = False,
        verse_number_size: int = 110,
        verse_number_padding: Padding = (1, 41, 1, 1),
        verse_number_color: Color = (255, 255, 255, 255),
        annotation_font_size: int = 28,
        word_color: Color = (255, 255, 255, 255),
        annotation_color: Color = (255, 255, 255, 255),
        annotation_font_path: Path | str | FontResource | None = None,
        background_color: Color = (0, 0, 0, 0),
    ):
        """Initialize WordConfig with resolved annotation_font_path."""
        # Resolve annotation_font_path before freezing
        resolved_path: Path | None = None
        if annotation_font_path is None:
            resolved_path = get_font_path("inter.ttf")
        elif isinstance(annotation_font_path, FontResource):
            resolved_path = annotation_font_path.path
        elif isinstance(annotation_font_path, str):
            resolved_path = Path(annotation_font_path)
        else:
            resolved_path = annotation_font_path

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
        object.__setattr__(self, "annotation_font_path", resolved_path)
        object.__setattr__(self, "background_color", background_color)


@dataclass(frozen=True)
class TextConfig:
    """Configuration for text rendering."""

    font_size: int = 36
    color: Color = (255, 255, 255, 255)
    font_path: Path | None = field(default=None, init=False)
    bold_font_path: Path | None = field(default=None, init=False)
    italic_font_path: Path | None = field(default=None, init=False)
    bold_italic_font_path: Path | None = field(default=None, init=False)
    line_spacing: int = 10
    height: int | None = None
    max_width: int | None = None

    def __init__(
        self,
        font_size: int = 36,
        color: Color = (255, 255, 255, 255),
        font_path: Path | str | FontResource | None = None,
        bold_font_path: Path | str | FontResource | None = None,
        italic_font_path: Path | str | FontResource | None = None,
        bold_italic_font_path: Path | str | FontResource | None = None,
        line_spacing: int = 10,
        height: int | None = None,
        max_width: int | None = None,
    ):
        """Initialize TextConfig with resolved font paths."""
        from quranmedialib.resources import get_font_path

        def _resolve_path(path: Path | str | FontResource | None, default: str) -> Path:
            """Resolve a font path to a Path object."""
            if path is None:
                return get_font_path(default)
            elif isinstance(path, FontResource):
                return path.path
            elif isinstance(path, str):
                return Path(path)
            return path

        object.__setattr__(self, "font_size", font_size)
        object.__setattr__(self, "color", color)
        object.__setattr__(self, "font_path", _resolve_path(font_path, "inter.ttf"))
        object.__setattr__(self, "bold_font_path", _resolve_path(bold_font_path, "inter_bold.ttf"))
        object.__setattr__(self, "italic_font_path", _resolve_path(italic_font_path, "inter_italic.ttf"))
        object.__setattr__(self, "bold_italic_font_path", _resolve_path(bold_italic_font_path, "inter_bold_italic.ttf"))
        object.__setattr__(self, "line_spacing", line_spacing)
        object.__setattr__(self, "height", height)
        object.__setattr__(self, "max_width", max_width)


# === Text Rendering Types ===
@dataclass(frozen=True)
class StyledWord:
    text: str
    font: ImageFont.ImageFont
    color: Color
    width: int
    is_transparent: bool = False
    simulate_bold: bool = False


class Line:
    def __init__(self):
        self.words: list[StyledWord] = []
        self.width: int = 0

    def add_word(self, word: StyledWord, space_width: int):
        if self.words:
            self.width += space_width
        self.words.append(word)
        self.width += word.width
