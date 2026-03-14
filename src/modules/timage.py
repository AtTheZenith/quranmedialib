"""
Module for rendering translation text into images with formatting support.
"""

from __future__ import annotations

import contextlib
import logging
import re
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont

# Logger setup
logger = logging.getLogger(__name__)


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


@dataclass
class StyledWord:
    text: str
    font: ImageFont.ImageFont
    color: tuple[int, int, int, int]
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


def _get_font(flags: str, config: TextConfig) -> tuple[ImageFont.ImageFont, bool]:
    """Selects the correct font variant based on flags. Returns (font, simulate_bold)."""
    path = config.font_path
    wants_bold = "b" in flags
    simulate_bold = False

    if "b" in flags and "i" in flags:
        path = config.bold_italic_font_path
    elif "b" in flags:
        path = config.bold_font_path
    elif "i" in flags:
        path = config.italic_font_path

    try:
        font = ImageFont.truetype(path, config.font_size)
        return font, False
    except (OSError, IOError):
        logger.debug(f"Font variant not found: {path}. Falling back to default.")

        # Determine fallback path
        fallback_path = config.italic_font_path if "i" in flags else config.font_path

        try:
            font = ImageFont.truetype(fallback_path, config.font_size)
            if wants_bold:
                simulate_bold = True  # Bold requested but file missing, so we simulate it
            return font, simulate_bold
        except (OSError, IOError):
            return ImageFont.load_default(), False


def _parse_rich_text(text: str, config: TextConfig, draw: ImageDraw.ImageDraw) -> list[StyledWord]:
    """
    Parses a string with multiple tags into StyledWord objects.
    Format: #flags#hex#text#
    """
    styled_words = []

    # regex to find #flags#hex#content#
    # We use a lazy match for content and enforce the closing #
    tag_pattern = re.compile(r"#([bi]*)#([0-9a-fA-F]*|)#(.*?)#")

    matches = list(tag_pattern.finditer(text))
    last_end = 0

    def add_text_chunk(chunk: str, flags: str, color: tuple[int, int, int, int]):
        if not chunk:
            return

        font, simulate_bold = _get_font(flags, config)
        is_transparent = color[3] == 0

        words = chunk.split()
        if not words:
            return

        for word_text in words:
            width = int(draw.textlength(word_text, font=font))
            styled_words.append(StyledWord(word_text, font, color, width, is_transparent, simulate_bold))

    for match in matches:
        # 1. Plain text before this tag
        plain = text[last_end : match.start()].strip()
        if plain:
            add_text_chunk(plain, "", config.color)

        flags = match.group(1)
        hex_col = match.group(2)
        content = match.group(3)

        # 2. Parse color
        color = config.color
        if hex_col:
            with contextlib.suppress(ValueError):
                h = hex_col
                if len(h) == 6:
                    h += "ff"
                r = int(h[:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
                a = int(h[6:8], 16)
                color = (r, g, b, a)
        add_text_chunk(content, flags, color)
        last_end = match.end()

    # Remaining text (if there's any text after the last closed tag, or unclosed tags)
    remaining = text[last_end:].strip()
    if remaining:
        add_text_chunk(remaining, "", config.color)
    return styled_words


def _wrap_rich_text(styled_words: list[StyledWord], space_width: int, max_width: int) -> list[Line]:
    """Greedy wrapping for styled words."""
    lines = []
    current_line = Line()

    for word in styled_words:
        extra = space_width if current_line.words else 0
        if current_line.width + extra + word.width > max_width:
            if current_line.words:
                lines.append(current_line)
            current_line = Line()
        current_line.add_word(word, space_width)
    if current_line.words:
        lines.append(current_line)

    return lines


def _wrap_rich_text_balanced(styled_words: list[StyledWord], space_width: int, max_width: int) -> list[Line]:
    """Balanced wrapping for rich text."""
    if not styled_words:
        return []

    greedy_lines = _wrap_rich_text(styled_words, space_width, max_width)
    target_num_lines = len(greedy_lines)

    if target_num_lines <= 1:
        return greedy_lines

    low = max(w.width for w in styled_words)
    high = max_width
    best_lines = greedy_lines

    while low <= high:
        mid = (low + high) // 2
        lines = _wrap_rich_text(styled_words, space_width, mid)
        if len(lines) <= target_num_lines:
            best_lines = lines
            high = mid - 1
        else:
            low = mid + 1

    return best_lines


def _calculate_vertical_start(canvas_height: int, text_height: int, alignment: str) -> int:
    """Calculates the starting Y coordinate based on vertical alignment."""
    if alignment == "center":
        return (canvas_height - text_height) // 2
    return canvas_height - text_height if alignment == "bottom" else 0


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[Line],
    start_y: int,
    max_width: int,
    space_width: int,
    ascent: int,
    line_height: int,
    config: TextConfig,
) -> None:
    """Draws a list of wrapped text lines onto the canvas."""
    current_y = start_y

    for line in lines:
        if config.horizontal_align == "center":
            current_x = (max_width - line.width) // 2
        elif config.horizontal_align == "right":
            current_x = max_width - line.width
        else:  # left
            current_x = 0

        for i, word in enumerate(line.words):
            if i > 0:
                current_x += space_width

            # Skip drawing if fully transparent but width is already accounted for
            if not word.is_transparent:
                stroke_width = 1 if word.simulate_bold else 0
                draw.text(
                    (current_x, current_y + ascent),
                    word.text,
                    font=word.font,
                    fill=word.color,
                    anchor="ls",
                    stroke_width=stroke_width,
                    stroke_fill=word.color if stroke_width > 0 else None,
                )
            current_x += word.width

        current_y += line_height + config.line_spacing


def get_timage(
    text: str,
    max_width: int,
    config: TextConfig | None = None,
    max_height: int | None = None,
) -> Image.Image | None:
    """
    Renders translation text into an RGBA image with rich formatting and alignment.
    """
    if not text:
        return None

    config = config or TextConfig()

    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    styled_words = _parse_rich_text(text, config, draw)
    if not styled_words:
        return None

    default_font, _ = _get_font("", config)
    space_width = int(draw.textlength(" ", font=default_font))

    lines = _wrap_rich_text_balanced(styled_words, space_width, max_width)
    if not lines:
        return None

    ascent, descent = default_font.getmetrics()
    line_height = ascent + descent
    total_text_height = len(lines) * line_height + (len(lines) - 1) * config.line_spacing

    canvas_height = max_height if max_height is not None else total_text_height
    timage = Image.new("RGBA", (max_width, canvas_height), (0, 0, 0, 0))
    timage_draw = ImageDraw.Draw(timage)

    start_y = _calculate_vertical_start(canvas_height, total_text_height, config.vertical_align)

    _draw_lines(timage_draw, lines, start_y, max_width, space_width, ascent, line_height, config)

    return timage


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    """Measures the advance width of a given text string."""
    return int(draw.textlength(text, font=font))
