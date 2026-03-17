from dataclasses import dataclass


@dataclass
class LayoutConfig:
    """Helper class to store canvas and top-level layout configuration."""

    max_width: int
    image_height: int
    padding: int
    bottom_offset: int = 0

    @property
    def content_width(self) -> int:
        """The available width for horizontal layout."""
        return self.max_width - 2 * self.padding

    @property
    def available_height(self) -> int:
        """The available height for vertical layout, excluding bottom reserved area."""
        return self.image_height - 2 * self.padding - self.bottom_offset


@dataclass
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
    verse_number_padding: tuple[int, int, int, int] = (1, 71, 1, 1)


@dataclass
class TextConfig:
    """Configuration for text rendering."""

    font_size: int = 36
    color: tuple[int, int, int, int] = (255, 255, 255, 255)
    font_path: str = "./assets/inter.ttf"
    bold_font_path: str = "./assets/inter_bold.ttf"
    italic_font_path: str = "./assets/inter_italic.ttf"
    bold_italic_font_path: str = "./assets/inter_bold_italic.ttf"
    line_spacing: int = 10
    horizontal_align: str = "center"  # "left", "center", "right"
    vertical_align: str = "top"  # "top", "center", "bottom"
    height: int | None = None
