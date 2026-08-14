"""Core types and configuration dataclasses for QuranMediaLib.

This module defines all configuration classes, database mappings, and data
structures used throughout the library. It includes:

- FontResource: Reference to a font file with metadata
- DatabaseConfig: Configuration for verse-by-verse database tables
- WbwDatabaseConfig: Extended config for word-by-word databases
- FrameConfig, WordConfig, TextConfig: Rendering configuration
- WordItem, StyledWord, Line: Data transmission types
- Padding, Alignment: Type-safe layout primitives
"""

from __future__ import annotations

import os
import os.path
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Annotated, Final, NamedTuple, Protocol, runtime_checkable

from PIL import Image

from quranmedialib.exceptions import (
    ResourceError,
    ValidationError,
)
from quranmedialib.resources import get_font_path

# === Path Security ===


# Maximum font size limit to prevent decompression bomb attacks and excessive memory usage
MAX_FONT_SIZE: Final = 2000
# Maximum allowed canvas dimension to prevent OOM via extremely large images
MAX_CANVAS_DIMENSION: Final = 5000
# Maximum glow radius for image effects to prevent excessive blurring computation
MAX_GLOW_RADIUS: Final = 200
# Maximum characters accepted for a single rendered text input. Bounds every
# downstream cost (tokenization, measurement cache, layout solvers, canvas size)
# so untrusted strings cannot trigger a DoS. Generous enough for any real
# translation paragraph or isolated-word payload.
MAX_TEXT_CHARS: Final = 10_000
# Maximum whitespace-delimited words/segments accepted for a single text input.
# Char-limit alone already bounds memory, but a pathological string of tiny
# tokens (e.g. "a a a ...") would otherwise explode the layout solver input.
# Set below the char-limit ceiling (MAX_TEXT_CHARS / 2) so the bound is actually
# reachable and independently enforced.
MAX_TEXT_WORDS: Final = 1_000

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
        raise ResourceError(f"Failed to validate path {path}: {e}") from e


# Surah and ayah range constants for runtime validation
MIN_SURAH: Final = 1
MAX_SURAH: Final = 114
MIN_AYAH: Final = 1
MAX_AYAH: Final = 286


# === Layout Primitives ===


@dataclass(frozen=True, slots=True)
class UDim2:
    """Scale+offset size/position value (inspired by Roblox).

    Resolves to absolute pixels via: parent_size * scale + offset.
    """

    x_scale: float = 0.0
    x_offset: float = 0.0
    y_scale: float = 0.0
    y_offset: float = 0.0

    def resolve(self, parent_w: float | int, parent_h: float | int) -> tuple[int, int]:
        return (
            int(parent_w * self.x_scale + self.x_offset),
            int(parent_h * self.y_scale + self.y_offset),
        )


@dataclass(frozen=True, slots=True)
class AnchorPoint:
    """Pivot point for layout elements. 0-1 range per axis.

    Examples:
        AnchorPoint(0, 0)   = top-left
        AnchorPoint(0.5, 0.5) = center
        AnchorPoint(1, 1)   = bottom-right
    """

    x: float = 0.0
    y: float = 0.0


@dataclass(frozen=True, slots=True)
class ResolvedRect:
    """Absolute pixel rectangle for content placement."""

    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0


@dataclass(frozen=True, slots=True)
class PresetLayout:
    """Resolution-independent layout element definition.

    Attributes:
        position: Where the element's anchor point is placed within parent.
        size: Width/height of the element.
        anchor: Which point of the element pivots at position.
    """

    position: UDim2 = UDim2(0, 0, 0, 0)
    size: UDim2 = UDim2(1, 0, 1, 0)
    anchor: AnchorPoint = AnchorPoint(0, 0)

    def resolve(self, frame_w: int, frame_h: int) -> ResolvedRect:
        elem_w, elem_h = self.size.resolve(frame_w, frame_h)
        pos_x, pos_y = self.position.resolve(frame_w, frame_h)
        left = int(pos_x - elem_w * self.anchor.x)
        top = int(pos_y - elem_h * self.anchor.y)
        return ResolvedRect(left=left, top=top, width=elem_w, height=elem_h)

    @classmethod
    def fill(cls) -> PresetLayout:
        return cls(UDim2(0, 0, 0, 0), UDim2(1, 0, 1, 0), AnchorPoint(0, 0))


@runtime_checkable
class Layerable(Protocol):
    """Interface for objects that can render themselves directly onto a provided canvas.

    Implemented by classes that manage their own internal coordinates (like VImage)
    to avoid intermediate canvas allocations.
    """

    def layer(self, canvas: Image.Image, x: int, y: int, **kwargs) -> None: ...


class Padding(NamedTuple):
    """Container for 4-directional padding values (top, bottom, left, right)."""

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


class BalancingMode(Enum):
    """Line-breaking solver for balanced wrapping.

    SMOOTH is the default. When a chosen solver cannot produce a layout, the
    greedy max-fill solver (FORWARD) is the unconditional direct fallback and a
    warning is logged with the reason.

    Attributes:
        FORWARD: Single-pass greedy max-fill (O(n), minimal lines). Also serves
            as the direct fallback for the other three solvers.
        SMOOTH: Global minimal-line, flattest-split pyramid (default).
        KNUTH_PLASS: Optimized guarded quadratic-slack DP.
        TEX: Micro-optimized faithful TeX port (byte-identical for small inputs).
    """

    FORWARD = "forward"
    SMOOTH = "smooth"
    KNUTH_PLASS = "knuth_plass"
    TEX = "tex"


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

    Attributes:
        image: The rendered word image.
        text: The word text (empty string for the verse number marker).
        color: Optional highlight color.
        index: 1-based position in the verse word sequence. Unset (0) for the
            verse number marker and for batched annotations until the batch
            boundary structure lands (see Gap 1 in the v5 implementation plan).
        class_type: Record discriminator — ``"word"`` or ``"verse_number"``.
            Lets sidecar consumers distinguish a real word from the phantom
            empty-text verse number marker without special-casing text.
        width: Pre-calculated image width.
        height: Pre-calculated image height.
    """

    image: Image.Image
    text: str | None = None
    color: Color | None = None
    width: int = field(init=False)
    height: int = field(init=False)
    index: int = 0
    class_type: str = "word"

    def __post_init__(self):
        """Pre-calculate image dimensions to speed up layout loops."""
        if self.image is not None:
            # Use object.__setattr__ because the dataclass is frozen
            object.__setattr__(self, "width", self.image.width)
            object.__setattr__(self, "height", self.image.height)


# === Configuration Types ===


@dataclass(frozen=True, slots=True)
class FrameConfig:
    """Simplified canvas configuration.

    In v4, layout positioning is handled by PresetLayout + LayoutEngine.
    FrameConfig carries canvas-level rendering options and the target
    canvas dimensions.

    Attributes:
        background_color: Canvas background color (RGBA).
        max_width: Canvas width in pixels.
        image_height: Canvas height in pixels.
        aspect_ratio: Aspect ratio key for layout lookup ("landscape", "story", "square").
        mode: Mode key for layout lookup ("default", "arabic", "translation").
    """

    background_color: Color = (0, 0, 0, 0)
    max_width: int = 1920
    image_height: int = 1080
    aspect_ratio: str = "landscape"
    mode: str = "default"


@dataclass(frozen=True, slots=True)
class VerseConfig:
    """Configuration for verse-level layout and wrapping.

    Attributes:
        word_spacing: Horizontal space between words.
        row_spacing: Vertical space between rows.
        max_rows_per_page: Maximum number of rows before starting a new page.
        balanced_wrapping: Whether to use balanced line wrapping.
        balancing_mode: Which balanced-wrapping solver to use (default SMOOTH).
    """

    word_spacing: int = 10
    row_spacing: int = 20
    max_rows_per_page: int = 5
    balanced_wrapping: bool = False
    balancing_mode: BalancingMode | str = BalancingMode.SMOOTH

    def __post_init__(self):
        """Validate layout parameters."""
        if isinstance(self.balancing_mode, str):
            object.__setattr__(self, "balancing_mode", BalancingMode(self.balancing_mode.lower()))
        if self.word_spacing < 0:
            raise ValidationError(f"word_spacing cannot be negative, got {self.word_spacing}")
        if self.row_spacing < 0:
            raise ValidationError(f"row_spacing cannot be negative, got {self.row_spacing}")
        if self.max_rows_per_page <= 0:
            raise ValidationError(f"max_rows_per_page must be positive, got {self.max_rows_per_page}")


@dataclass(frozen=True, slots=True)
class Preset:
    """Unified configuration preset for rendering.

    Attributes:
        frame: Canvas and framing configuration.
        word: Word-level rendering configuration.
        verse: Verse-level layout configuration.
        text: Translation text rendering configuration.
    """

    frame: FrameConfig
    word: WordConfig
    verse: VerseConfig
    text: TextConfig


@dataclass(frozen=True, slots=True)
class WordConfig:
    """Configuration for atomic word rendering behavior.

    Controls font sizes, colors, and specific verse-number styles.
    """

    font_size: FontSize
    word_padding: Padding | tuple[int, int, int, int] = field(default_factory=lambda: Padding(10, 10, 10, 10))
    word_spacing: int = 10
    row_spacing: int = 20
    max_rows_per_page: int = 5
    balanced_wrapping: bool = False
    verse_v_offset: int = 0
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
    balancing_mode: BalancingMode | str = BalancingMode.SMOOTH
    ignore_non_token_hashtags: bool = False
    highlight_font_path: Path | str | FontResource | None = None
    highlight_font_size: int | None = None
    highlight_color: Color | None = None

    def __post_init__(self):
        """Validate parameters and resolve defaults."""

        def _resolve_path(path: Path | str | FontResource | None, default_filename: str) -> Path:
            if path is None:
                return get_font_path(default_filename)
            return path.path if isinstance(path, FontResource) else Path(path)

        # Coerce alignment
        if isinstance(self.alignment, str):
            object.__setattr__(self, "alignment", HorizontalAlignment(self.alignment.lower()))

        # Coerce balancing mode
        if isinstance(self.balancing_mode, str):
            object.__setattr__(self, "balancing_mode", BalancingMode(self.balancing_mode.lower()))

        # Validate font_size
        if self.font_size <= 0:
            raise ValidationError(f"font_size must be positive, got {self.font_size}")
        if self.font_size > MAX_FONT_SIZE:
            raise ValidationError(f"font_size exceeds maximum limit of {MAX_FONT_SIZE}, got {self.font_size}")

        # Validate max_width
        if self.max_width is not None:
            if self.max_width <= 0:
                raise ValidationError(f"max_width must be positive when provided, got {self.max_width}")
            if self.max_width > MAX_CANVAS_DIMENSION:
                raise ValidationError(
                    f"max_width exceeds maximum limit of {MAX_CANVAS_DIMENSION}, got {self.max_width}"
                )

        # Validate height
        if self.height is not None:
            if self.height <= 0:
                raise ValidationError(f"height must be positive when provided, got {self.height}")
            if self.height > MAX_CANVAS_DIMENSION:
                raise ValidationError(f"height exceeds maximum limit of {MAX_CANVAS_DIMENSION}, got {self.height}")

        # Resolve paths
        object.__setattr__(self, "font_path", _resolve_path(self.font_path, "inter.ttf"))
        object.__setattr__(self, "italic_font_path", _resolve_path(self.italic_font_path, "inter_italic.ttf"))
        object.__setattr__(self, "highlight_font_path", _resolve_path(self.highlight_font_path, "inter.ttf"))

        # Resolve highlight defaults
        if self.highlight_font_size is None:
            object.__setattr__(self, "highlight_font_size", self.font_size)
        if self.highlight_color is None:
            object.__setattr__(self, "highlight_color", (255, 215, 0, 255))
