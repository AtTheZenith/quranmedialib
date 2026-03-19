from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from PIL import Image, ImageFont

# === Basic Types ===
# Using the 'type' keyword for cleaner aliases
type Color = tuple[int, int, int] | tuple[int, int, int, int]
# (top, bottom, left, right)
type Padding = tuple[int, int, int, int]

type SurahNumber = Annotated[int, range(1, 115)]
type AyahNumber = Annotated[int, range(1, 287)]
type WordIndex = int


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
        # Fixed: Accessing tuple indices (left: 2, right: 3)
        return self.max_width - self.padding[2] - self.padding[3]

    @property
    def available_height(self) -> int:
        """The available height for vertical layout (height - top - bottom)."""
        # Fixed: Accessing tuple indices (top: 0, bottom: 1)
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
    annotation_font_path: str = "./assets/inter.ttf"
    background_color: Color = (0, 0, 0, 0)


@dataclass(frozen=True)
class TextConfig:
    """Configuration for text rendering."""

    font_size: int = 36
    color: Color = (255, 255, 255, 255)
    font_path: str = "./assets/inter.ttf"
    bold_font_path: str = "./assets/inter_bold.ttf"
    italic_font_path: str = "./assets/inter_italic.ttf"
    bold_italic_font_path: str = "./assets/inter_bold_italic.ttf"
    line_spacing: int = 10
    height: int | None = None
    max_width: int | None = None


# === Text Rendering Types ===
@dataclass(frozen=True)
class StyledWord:
    text: str
    font: ImageFont.ImageFont
    color: Color  # Reused your Color alias here
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
