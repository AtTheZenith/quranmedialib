from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from PIL import ImageFont

# === Basic Types ===
# Using the 'type' keyword for cleaner aliases
type Color = tuple[int, int, int] | tuple[int, int, int, int]
# (top, bottom, left, right)
type Padding = tuple[int, int, int, int]

type SurahNumber = Annotated[int, range(1, 115)]
type AyahNumber = Annotated[int, range(1, 287)]
type WordIndex = int


# === Configuration Types ===
@dataclass(frozen=True)
class LayoutConfig:
    """Helper class to store canvas and top-level layout configuration."""

    max_width: int
    image_height: int
    padding: Padding = (0, 0, 0, 0)
    bottom_offset: int = 0

    @property
    def content_width(self) -> int:
        """The available width for horizontal layout (max_width - left - right)."""
        # Fixed: Accessing tuple indices (left: 2, right: 3)
        return self.max_width - self.padding[2] - self.padding[3]

    @property
    def available_height(self) -> int:
        """The available height for vertical layout (height - top - bottom - offset)."""
        # Fixed: Accessing tuple indices (top: 0, bottom: 1)
        return self.image_height - self.padding[0] - self.padding[1] - self.bottom_offset


@dataclass(frozen=True)
class WordConfig:
    """Configuration for word and verse layout behavior."""

    word_spacing: int
    row_spacing: int
    max_rows_per_page: int
    verse_vertical_align: str = "center"
    verse_horizontal_align: str = "center"
    verse_v_offset: int = 0
    balanced_wrapping: bool = False
    verse_number_size: int = 110
    verse_number_padding: Padding = (1, 71, 1, 1)


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
    horizontal_align: str = "center"  # "left", "center", "right"
    vertical_align: str = "top"  # "top", "center", "bottom"
    height: int | None = None


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