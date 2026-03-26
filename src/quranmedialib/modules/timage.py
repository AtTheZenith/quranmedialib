"""Module for rendering translation text into images with formatting support.

This module provides a rich-text rendering engine for translations. It supports
tag-based formatting (#b# for bold, #i# for italic, #hex# for color), balanced
inverted-pyramid wrapping, and configurable alignment.
"""

from __future__ import annotations

import logging
import re
from typing import NamedTuple

from PIL import Image, ImageDraw, ImageFont

from quranmedialib.types import (
    HorizontalAlignment,
    Line,
    StyledWord,
    TextConfig,
)

# Logger setup
logger = logging.getLogger(__name__)


class ParsedSegment(NamedTuple):
    """Represents a pre-parsed translation segment."""

    flags: str
    hex_color: str
    content: str
    original_had_tag: bool


def normalize_highlight_style(style: str) -> str:
    """Ensures highlight_style is in the correct #flags#hex# format."""
    if not style.startswith("#"):
        style = f"#{style}"
    if not style.endswith("#"):
        style = f"{style}#"
    # If highlight_style is only flags (e.g. #b#), add separator for empty hex
    if style.count("#") == 2:
        style = f"{style}#"
    return style


def prepare_translation_segments(translation: list[str]) -> list[ParsedSegment]:
    """Pre-parses translation segments to avoid redundant regex searches in loops."""
    tag_pattern = re.compile(r"#([bi]*)#([0-9a-fA-F]*|)#(.*?)(?=#|$)")
    parsed = []

    for segment in translation:
        if match := tag_pattern.search(segment):
            content = match[3].rstrip("#")
            parsed.append(ParsedSegment(match[1], match[2], content, True))
        else:
            parsed.append(ParsedSegment("", "", segment, False))
    return parsed


def format_isolation_text(
    parsed_segments: list[ParsedSegment],
    target_index: int,
    highlight_style: str,
) -> str:
    """Constructs a formatted rich text string where one segment is highlighted and others are transparent."""
    formatted = []
    for j, seg in enumerate(parsed_segments):
        if j == target_index:
            if seg.original_had_tag:
                # Keep original formatting if it already has tags
                formatted.append(f"#{seg.flags}#{seg.hex_color}#{seg.content}#")
            else:
                # Apply highlight style to plain text
                formatted.append(f"{highlight_style}{seg.content}#")
        elif seg.original_had_tag:
            # Preserve flags but force transparency
            formatted.append(f"#{seg.flags}#00000000#{seg.content}#")
        else:
            # Wrap plain text with transparent tag
            formatted.append(f"##00000000#{seg.content}#")

    return " ".join(formatted)


def _get_font(flags: str, config: TextConfig) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, bool]:
    """Selects the correct font variant based on flags. Returns (font, simulate_bold).

    For variable fonts, uses font variations (weight axis) instead of separate
    font files where possible.
    """
    wants_bold = "b" in flags
    wants_italic = "i" in flags

    # Determine base font path (italic or regular)
    base_path = config.italic_font_path if wants_italic else config.font_path
    base_path_str = str(base_path)

    # Load the font
    font = ImageFont.truetype(base_path_str, config.font_size)

    simulate_bold = False
    if wants_bold:
        try:
            # Inter variable font uses 'wght' axis (700 for bold).
            font.set_variation_by_axes([700])
        except (ValueError, OSError):
            # Fallback to stroke-based bold simulation if font is not variable.
            simulate_bold = True

    return font, simulate_bold


def _parse_hex_color(hex_col: str, default_color: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Parses a hex color string into an RGBA tuple."""
    if not hex_col:
        return default_color

    try:
        h = hex_col
        if len(h) == 6:
            h += "ff"
        r = int(h[:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        a = int(h[6:8], 16)
        return (r, g, b, a)
    except ValueError:
        return default_color


def _parse_rich_text(text: str, config: TextConfig, draw: ImageDraw.ImageDraw) -> list[StyledWord]:
    """Parses a string with multiple tags into StyledWord objects for layout.

    Tags follow the format: #flags#hex#text#
    """
    styled_words = []
    tag_pattern = re.compile(r"#([bi]*)#([0-9a-fA-F]*|)#(.*?)#")

    matches = list(tag_pattern.finditer(text))
    last_end = 0

    def add_text_chunk(chunk: str, flags: str, color: tuple[int, int, int, int]):
        if not chunk:
            return

        font, simulate_bold = _get_font(flags, config)
        is_transparent = color[3] == 0

        words = chunk.split()
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

        # 2. Parse tag color
        color = _parse_hex_color(hex_col, config.color)
        add_text_chunk(content, flags, color)
        last_end = match.end()

    # Remaining text after the last tag
    remaining = text[last_end:].strip()
    if remaining:
        add_text_chunk(remaining, "", config.color)

    return styled_words


def _wrap_rich_text_greedy(styled_words: list[StyledWord], space_width: int, max_width: int) -> list[Line]:
    """Standard greedy wrapping logic (Lines are filled until max_width)."""
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
    """Wraps text into a balanced 'Inverted Pyramid' shape using Dynamic Programming.

    Rules:
    1. Line[i].width >= Line[i+1].width (Inverted Pyramid)
    2. Minimize the width of the longest line (Balanced)
    3. Minimize quadratic variance to avoid 'ragged' edges.
    """
    if not styled_words:
        return []

    # Estimate line count using greedy as a reference
    greedy_lines = _wrap_rich_text_greedy(styled_words, space_width, max_width)
    if len(greedy_lines) <= 1:
        return greedy_lines

    n = len(styled_words)
    # Precompute cumulative widths for O(1) row-width calculation.
    cum_widths = [0] * (n + 1)
    for i in range(n):
        cum_widths[i + 1] = cum_widths[i] + styled_words[i].width

    def get_line_width(start_idx: int, end_idx: int) -> int:
        if start_idx > end_idx:
            return 0
        w_sum = cum_widths[end_idx + 1] - cum_widths[start_idx]
        spaces = max(0, end_idx - start_idx) * space_width
        return w_sum + spaces

    # dp[i][j] = (min_cost, line_width, prev_word_index)
    max_k = min(n, len(greedy_lines) * 2)
    dp = [[(float("inf"), 0, -1) for _ in range(n)] for _ in range(max_k + 1)]

    # Base case: one line
    for j in range(n):
        w = get_line_width(0, j)
        if w <= max_width:
            cost = max_width - w  # Favor longer first lines
            dp[1][j] = (float(cost), w, -1)

    # Fill DP for 2..k lines
    for i in range(2, max_k + 1):
        found_any = False
        for j in range(n):
            for p in range(j - 1, -1, -1):
                curr_w = get_line_width(p + 1, j)
                if curr_w > max_width:
                    break

                prev_cost, prev_w, _ = dp[i - 1][p]
                if prev_cost == float("inf"):
                    continue

                # Inverted Pyramid constraint: current line must be narrower than previous
                if 0 < curr_w <= prev_w:
                    cost = prev_cost + (prev_w - curr_w) ** 2 + (max_width - curr_w)
                    if cost < dp[i][j][0]:
                        dp[i][j] = (cost, curr_w, p)
                        found_any = True
        if not found_any:
            break

    # Find the line count k that successfully reached the last word
    best_i = -1
    for i in range(1, max_k + 1):
        if dp[i][n - 1][0] != float("inf"):
            best_i = i
            break

    if best_i == -1:
        return greedy_lines

    # Backtrack to reconstruct lines
    lines = []
    curr_j = n - 1
    for i in range(best_i, 0, -1):
        prev_j = dp[i][curr_j][2]
        line = Line()
        for idx in range(prev_j + 1, curr_j + 1):
            line.add_word(styled_words[idx], space_width)
        lines.append(line)
        curr_j = prev_j

    return lines[::-1]


def _draw_styled_word(
    draw: ImageDraw.ImageDraw,
    word: StyledWord,
    pos: tuple[int, int],
    ascent: int,
):
    """Draws a single styled word, handling bold simulation and transparency."""
    if word.is_transparent:
        return

    stroke_width = 1 if word.simulate_bold else 0
    draw.text(
        (pos[0], pos[1] + ascent),
        word.text,
        font=word.font,
        fill=word.color,
        anchor="ls",
        stroke_width=stroke_width,
        stroke_fill=word.color if stroke_width > 0 else None,
    )


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
    """Draws multiple lines of text onto the canvas, respecting horizontal alignment."""
    current_y = start_y

    for line in lines:
        # Calculate start X based on alignment
        line_w = line.width
        if config.alignment == HorizontalAlignment.CENTER:
            current_x = (max_width - line_w) // 2
        elif config.alignment == HorizontalAlignment.RIGHT:
            current_x = max_width - line_w
        else:  # LEFT
            current_x = 0

        for i, word in enumerate(line.words):
            if i > 0:
                current_x += space_width
            _draw_styled_word(draw, word, (current_x, current_y), ascent)
            current_x += word.width

        current_y += line_height + config.line_spacing


def get_timage(
    text: str,
    config: TextConfig | None = None,
    max_height: int | None = None,
) -> Image.Image | None:
    """Renders translation text into an RGBA image with rich formatting.

    Args:
        text: Formatted rich text string (#b# for bold, etc.).
        config: Rendering configuration.
        max_height: Override for the canvas height.

    Returns:
        Rendered PIL Image or None if text is empty.
    """
    if not text:
        return None

    config = config or TextConfig()

    # Initial probe to measure text
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    styled_words = _parse_rich_text(text, config, draw)
    if not styled_words:
        return None

    # Determine space width from default font
    default_font, _ = _get_font("", config)
    space_width = int(draw.textlength(" ", font=default_font))

    # Apply balanced wrapping
    lines = _wrap_rich_text_balanced(styled_words, space_width, config.max_width)
    if not lines:
        return None

    ascent, descent = default_font.getmetrics()
    line_height = ascent + descent
    total_text_height = len(lines) * line_height + (len(lines) - 1) * config.line_spacing

    # Calculate final canvas dimensions
    actual_max_height = max_height if max_height is not None else config.height
    canvas_height = actual_max_height if actual_max_height is not None else total_text_height

    timage = Image.new("RGBA", (config.max_width, canvas_height), (0, 0, 0, 0))
    timage_draw = ImageDraw.Draw(timage)

    # Render lines onto the new canvas
    _draw_lines(timage_draw, lines, 0, config.max_width, space_width, ascent, line_height, config)

    return timage


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    """Measures the advance width of a given text string."""
    return int(draw.textlength(text, font=font))
