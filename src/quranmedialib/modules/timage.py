"""Module for rendering translation text into images with formatting support.

This module provides a rich-text rendering engine for translations. It supports
tag-based formatting (#b# for bold, #i# for italic, #hex# for color), balanced
inverted-pyramid wrapping, and configurable alignment.
"""

from __future__ import annotations

import contextlib
import logging
import re
import threading
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageDraw, ImageFont

from quranmedialib.modules.font_cache import get_font
from quranmedialib.types import (
    HorizontalAlignment,
    Line,
    StyledWord,
    TextConfig,
)

__all__ = [
    "get_timage",
    "ParsedSegment",
    "normalize_highlight_style",
    "prepare_translation_segments",
    "format_isolation_text",
]

# Logger setup
logger = logging.getLogger(__name__)

# Module-level regex patterns to avoid repeated compilation
_SEGMENT_TAG_PATTERN = re.compile(r"#([bi]*)#([0-9a-fA-F]*|)#(.*?)(?=#|$)")
_RICH_TEXT_TAG_PATTERN = re.compile(r"#([bi]*)#([0-9a-fA-F]*|)#(.*?)#")

# Lazy-initialized singletons for text measurement (PERF-010: avoid import-time allocation)
_measure_img: Image.Image | None = None
_measure_draw: ImageDraw.ImageDraw | None = None

# Thread-safe cache for bold variation names
# Maps font_path -> variation_name, None (needs simulation), or _AXIS_BOLD_SENTINEL (axis-based)
_BOLD_VARIATION_CACHE_LOCK = threading.Lock()
_BOLD_VARIATION_CACHE: dict[str, str | None | object] = {}
_AXIS_BOLD_SENTINEL = object()  # Sentinel to mark axis-based bold detection

# Hardcoded known bold variation names for cold-start optimization (PERF-005)
# Maps font filename -> bold variation name (None means no variations / non-variable font)
_BOLD_VARIATION_NAMES: dict[str, str | None] = {
    "Inter.ttf": "SemiBold",
    "Inter-Italic.ttf": "SemiBold Italic",
    "Inter-Regular.ttf": "SemiBold",
    "hafs.otf": None,  # Non-variable font, no variations
}


def _get_measure_draw() -> ImageDraw.ImageDraw:
    """Returns module-level ImageDraw singleton, initialized on first use (PERF-010)."""
    global _measure_img, _measure_draw
    if _measure_draw is None:
        _measure_img = Image.new("RGBA", (1, 1))
        _measure_draw = ImageDraw.Draw(_measure_img)
    return _measure_draw


class ParsedSegment(NamedTuple):
    """Represents a pre-parsed translation segment."""

    flags: str
    hex_color: str
    content: str
    original_had_tag: bool


def normalize_highlight_style(style: str) -> str:
    """Ensures highlight_style is in the correct #flags#hex# format.

    Args:
        style: The highlight style string. If None, defaults to bold.

    Returns:
        Normalized style string in #flags#hex# format.
    """
    if style is None:
        style = "#b#"
    if not style.startswith("#"):
        style = f"#{style}"
    if not style.endswith("#"):
        style = f"{style}#"
    # If highlight_style is only flags (e.g. #b#), add separator for empty hex
    if style.count("#") == 2:
        style = f"{style}#"
    return style


def prepare_translation_segments(translation: list[str]) -> list[ParsedSegment]:
    """Pre-parses translation segments to avoid redundant regex searches in loops.

    Args:
        translation: List of translation segment strings. If None, returns empty list.

    Returns:
        List of ParsedSegment objects.
    """
    if translation is None:
        return []
    parsed = []

    for segment in translation:
        if match := _SEGMENT_TAG_PATTERN.search(segment):
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
    """Constructs a formatted rich text string where one segment is highlighted and others are transparent.

    Args:
        parsed_segments: List of pre-parsed translation segments.
        target_index: Index of the segment to highlight (0-based).
        highlight_style: Rich text formatting string for the highlighted segment.

    Returns:
        Formatted rich text string with one highlighted segment.

    Raises:
        ValueError: If target_index is out of bounds (negative or >= len(parsed_segments)).
    """
    if target_index < 0:
        raise ValueError(f"target_index must be non-negative, got {target_index}")
    if target_index >= len(parsed_segments):
        raise ValueError(f"target_index {target_index} out of bounds for {len(parsed_segments)} segments")

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

    Args:
        flags: String containing style flags (e.g., "b", "i", "bi").
        config: Text configuration containing font paths and size.

    Returns:
        tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, bool]: A tuple containing
        the selected font object and a boolean indicating whether bold simulation
        is required.
    """
    wants_bold = "b" in flags
    wants_italic = "i" in flags

    # Determine base font path (italic or regular)
    base_path = config.italic_font_path if wants_italic else config.font_path
    base_path_str = str(base_path)

    # Load the font using centralized cache
    font = get_font(base_path_str, config.font_size)

    simulate_bold = False
    if wants_bold:
        # Check cache for bold variation name
        with _BOLD_VARIATION_CACHE_LOCK:
            if base_path_str in _BOLD_VARIATION_CACHE:
                cached_variation = _BOLD_VARIATION_CACHE[base_path_str]
                if cached_variation is _AXIS_BOLD_SENTINEL:
                    # Axis-based bold was detected, need to re-apply axes
                    # Fall through to re-detect since we don't store the axes values
                    pass
                elif cached_variation is not None:
                    try:
                        font.set_variation_by_name(cached_variation)
                        return font, False
                    except (AttributeError, OSError):
                        # Cache might be stale or font state changed, fall through to re-detect
                        pass
                else:
                    # cached_variation is None, meaning this font needs bold simulation
                    simulate_bold = True
                    return font, True

        # Try hardcoded bold variation names first (PERF-005: cold-start optimization)
        font_filename = Path(base_path_str).name
        hardcoded_bold = _BOLD_VARIATION_NAMES.get(font_filename)
        if hardcoded_bold is not None:
            try:
                font.set_variation_by_name(hardcoded_bold)
                with _BOLD_VARIATION_CACHE_LOCK:
                    _BOLD_VARIATION_CACHE[base_path_str] = hardcoded_bold
                return font, False
            except (AttributeError, OSError):
                pass  # Fall through to dynamic detection

        try:
            # First attempt: Try setting bold via named instance (most reliable for complex fonts)
            # Inter uses "Bold" or "Bold Italic" etc.
            target_name = "Bold Italic" if wants_italic else "Bold"
            found = False
            with contextlib.suppress(AttributeError, OSError):
                # Iterate through available instances to find a matching one (case-insensitive)
                for variation_name in font.get_variation_names():
                    # Names can be bytes or str depending on PIL/FreeType version
                    name_str = (
                        variation_name.decode("utf-8") if isinstance(variation_name, bytes) else str(variation_name)
                    )
                    if target_name.lower() in name_str.lower():
                        font.set_variation_by_name(variation_name)
                        found = True
                        # Cache the successful variation name
                        with _BOLD_VARIATION_CACHE_LOCK:
                            _BOLD_VARIATION_CACHE[base_path_str] = (
                                variation_name if isinstance(variation_name, str) else variation_name.decode("utf-8")
                            )
                        break
            if not found:
                # Second attempt: Search for Weight/wght axis and set it manually
                with contextlib.suppress(AttributeError, KeyError, OSError):
                    axes = font.get_variation_axes()
                    for i, axis in enumerate(axes):
                        name_val = axis.get("name", b"")
                        if isinstance(name_val, bytes):
                            name_val = name_val.decode("utf-8")
                        tag_val = axis.get("tag", "")

                        if "weight" in name_val.lower() or tag_val == "wght":
                            # PIL's set_variation_by_axes typically requires all axis values
                            vals = [a["default"] for a in axes]
                            vals[i] = 700  # Set Weight to 700 (Bold)
                            font.set_variation_by_axes(vals)
                            found = True
                            # Cache that we used axis-based approach (mark as special value)
                            with _BOLD_VARIATION_CACHE_LOCK:
                                _BOLD_VARIATION_CACHE[base_path_str] = _AXIS_BOLD_SENTINEL
                            break
            if not found:
                # Final fallback: Use stroke-based bold simulation
                logger.warning(
                    f"Could not find native Bold variation for font '{base_path_str}'. "
                    "Falling back to stroke-based bold simulation."
                )
                simulate_bold = True
                # Cache that this font needs simulation
                with _BOLD_VARIATION_CACHE_LOCK:
                    _BOLD_VARIATION_CACHE[base_path_str] = None

        except (OSError, ValueError, AttributeError, KeyError) as e:
            logger.warning(f"Failed to apply bold style to font '{base_path_str}': {e}. Falling back to simulation.")
            simulate_bold = True
            with _BOLD_VARIATION_CACHE_LOCK:
                _BOLD_VARIATION_CACHE[base_path_str] = None

    return font, simulate_bold


def _parse_hex_color(hex_col: str, default_color: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Parses a hex color string into an RGBA tuple.

    Args:
        hex_col: Hex color string (6 or 8 characters, with or without alpha).
        default_color: Fallback RGBA color tuple if parsing fails.

    Returns:
        tuple[int, int, int, int]: RGBA color values (0-255 for each channel).
    """
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

    Tags follow the format: #flags#hex#content#
    Whitespaces are preserved as explicit StyledWord tokens.

    Args:
        text: Rich text string with formatting tags.
        config: Text configuration containing font paths and colors.
        draw: ImageDraw instance for measuring text widths.

    Returns:
        list[StyledWord]: List of styled word objects ready for rendering.
    """
    styled_words = []

    matches = list(_RICH_TEXT_TAG_PATTERN.finditer(text))
    last_end = 0

    def add_text_chunk(chunk: str, flags: str, color: tuple[int, int, int, int]):
        if not chunk:
            return

        font, simulate_bold = _get_font(flags, config)
        is_transparent = color[3] == 0

        # Tokenize by non-whitespace and whitespace to preserve all original spacing
        tokens = re.findall(r"\S+|\s+", chunk)
        for word_text in tokens:
            # PIL.textlength fails on multiline text. We treat all whitespaces (including \n)
            # as horizontal space for measurement and wrapping purposes.
            measure_text = word_text.replace("\n", " ")
            width = int(draw.textlength(measure_text, font=font))
            styled_words.append(StyledWord(word_text, font, color, width, is_transparent, simulate_bold))

    for match in matches:
        # 1. Plain text before this tag (preserving all characters including leading/trailing spaces)
        plain = text[last_end : match.start()]
        if plain:
            add_text_chunk(plain, "", config.color)

        flags = match.group(1)
        hex_col = match.group(2)
        content = match.group(3)

        # 2. Parse tag color and add content
        color = _parse_hex_color(hex_col, config.color)
        add_text_chunk(content, flags, color)
        last_end = match.end()

    # Remaining text after the last tag
    remaining = text[last_end:]
    if remaining:
        add_text_chunk(remaining, "", config.color)

    return styled_words


def _wrap_rich_text_greedy(styled_words: list[StyledWord], max_width: int | None) -> list[Line]:
    """Standard greedy wrapping logic (Lines are filled until max_width).

    Since whitespaces are explicit tokens, we:
    1. Skip leading whitespaces at the start of each line.
    2. Trim trailing whitespaces at the end of each line for visual consistency.

    Args:
        styled_words: List of styled word objects with explicit whitespace tokens.
        max_width: Maximum line width in pixels. If None, no wrapping is applied (single line).

    Returns:
        list[Line]: List of line objects containing wrapped words.
    """
    # If max_width is None, treat as unlimited width (single line)
    if max_width is None:
        line = Line()
        for word in styled_words:
            if not line.words and word.text.isspace():
                continue
            line.add_word(word, 0)
        if line.words:
            if line.words[-1].text.isspace():
                line.words.pop()
        return [line] if line.words else []

    lines = []
    current_line = Line()

    for word in styled_words:
        is_space = word.text.isspace()

        # Rule 1: Never start a line with a whitespace token
        if not current_line.words and is_space:
            continue

        if current_line.width + word.width > max_width:
            if current_line.words:
                # Rule 2: Trim trailing whitespaces from finished lines
                if current_line.words[-1].text.isspace():
                    last_space = current_line.words.pop()
                    current_line.width -= last_space.width
                lines.append(current_line)

            # Start a new line
            current_line = Line()
            # If the word caused a wrap and it's a whitespace, skip it for the new line
            if is_space:
                continue

        # Add the word (space_width set to 0 as tokens contain their own spaces)
        current_line.add_word(word, 0)

    # Clean up the last line
    if current_line.words:
        if current_line.words[-1].text.isspace():
            current_line.words.pop()
        lines.append(current_line)
    return lines


def _wrap_rich_text_balanced(styled_words: list[StyledWord], max_width: int | None) -> list[Line]:
    """Wraps text into a balanced 'Inverted Pyramid' shape using Dynamic Programming.

    This version handles explicit whitespace tokens by trimming them from line width
    calculations to ensure a cleanly centered visual distribution.

    For very large word counts (> MAX_DP_WORDS), falls back to greedy wrapping to avoid
    excessive computation time (DP is O(k × n²)).

    Args:
        styled_words: List of styled word objects with explicit whitespace tokens.
        max_width: Maximum line width in pixels. If None, no wrapping is applied.

    Returns:
        list[Line]: List of line objects forming an inverted pyramid shape.
    """
    if not styled_words:
        return []

    # If max_width is None, fall back to greedy (which handles None)
    if max_width is None:
        return _wrap_rich_text_greedy(styled_words, None)

    # Estimate line count using greedy as a reference
    greedy_lines = _wrap_rich_text_greedy(styled_words, max_width)
    if len(greedy_lines) <= 1:
        return greedy_lines

    # Performance guard: DP is O(k × n²), fallback to greedy for large inputs
    from quranmedialib.database_manager import MAX_DP_WORDS

    if len(styled_words) > MAX_DP_WORDS:
        logger.debug(
            "Falling back to greedy wrapping for %d words (DP would be too slow)",
            len(styled_words),
        )
        return greedy_lines

    n = len(styled_words)
    cum_widths = [0] * (n + 1)
    for i in range(n):
        cum_widths[i + 1] = cum_widths[i] + styled_words[i].width

    def get_line_width_normalized(start_idx: int, end_idx: int) -> int:
        """Calculates line width while trimming leading/trailing whitespaces."""
        if start_idx > end_idx:
            return 0

        # Adjust start/end to skip whitespace tokens for accurate line width
        actual_start = start_idx
        while actual_start <= end_idx and styled_words[actual_start].text.isspace():
            actual_start += 1

        actual_end = end_idx
        while actual_end >= actual_start and styled_words[actual_end].text.isspace():
            actual_end -= 1

        if actual_start > actual_end:
            return 0

        return cum_widths[actual_end + 1] - cum_widths[actual_start]

    # dp[i][j] = (min_cost, line_width_normalized, prev_word_index)
    max_k = min(n, len(greedy_lines) * 2)
    dp = [[(float("inf"), 0, -1) for _ in range(n)] for _ in range(max_k + 1)]

    # Base case: one line
    for j in range(n):
        w = get_line_width_normalized(0, j)
        if w <= max_width:
            cost = max_width - w  # Favor longer first lines
            dp[1][j] = (float(cost), w, -1)

    # Fill DP for 2..k lines
    for i in range(2, max_k + 1):
        found_any = False
        for j in range(n):
            for p in range(j - 1, -1, -1):
                curr_w = get_line_width_normalized(p + 1, j)
                if curr_w > max_width:
                    break

                prev_cost, prev_w, _ = dp[i - 1][p]
                if prev_cost == float("inf"):
                    continue

                if 0 < curr_w <= prev_w:
                    cost = prev_cost + (prev_w - curr_w) ** 2 + (max_width - curr_w)
                    if cost < dp[i][j][0]:
                        dp[i][j] = (cost, curr_w, p)
                        found_any = True
        if not found_any:
            break

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

        # Assemble line while trimming leading/trailing whitespace tokens
        line_start = prev_j + 1
        while line_start <= curr_j and styled_words[line_start].text.isspace():
            line_start += 1

        line_end = curr_j
        while line_end >= line_start and styled_words[line_end].text.isspace():
            line_end -= 1

        for idx in range(line_start, line_end + 1):
            line.add_word(styled_words[idx], 0)

        lines.append(line)
        curr_j = prev_j

    return lines[::-1]


def _draw_styled_word(
    draw: ImageDraw.ImageDraw,
    word: StyledWord,
    pos: tuple[int, int],
    ascent: int,
) -> None:
    """Draws a single styled word, handling bold simulation and transparency.

    Args:
        draw: ImageDraw instance for rendering text.
        word: StyledWord object containing text, font, color, and styling.
        pos: (x, y) position for the bottom-left anchor of the text.
        ascent: Font ascent value for baseline alignment.
    """
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
    ascent: int,
    line_height: int,
    config: TextConfig,
) -> None:
    """Draws multiple lines of text onto the canvas, respecting horizontal alignment.

    Args:
        draw: ImageDraw instance for rendering text.
        lines: List of Line objects containing styled words.
        start_y: Starting Y coordinate for the first line.
        max_width: Canvas width for alignment calculations.
        ascent: Font ascent value for baseline alignment.
        line_height: Height of each line (ascent + descent).
        config: Text configuration containing alignment settings.
    """
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

        for word in line.words:
            # We no longer re-insert space_width; tokens contain their own whitespaces.
            _draw_styled_word(draw, word, (current_x, current_y), ascent)
            current_x += word.width

        current_y += line_height + config.line_spacing


def get_timage(
    text: str,
    config: TextConfig | None = None,
    max_height: int | None = None,
) -> Image.Image | None:
    """Renders translation text into an RGBA image with rich formatting.

    Results are cached (LRU, max 1024 entries) based on text + config parameters.

    Args:
        text: Formatted rich text string (#b# for bold, etc.).
        config: Rendering configuration.
        max_height: Override for the canvas height.

    Returns:
        Rendered PIL Image or None if text is empty.
    """
    return _get_timage_cached(text, config, max_height)


# Cache for timage (PERF-007)
# Key: (text, font_path, italic_path, font_size, max_width, max_height, color, line_spacing, alignment_value)
_timage_cache: dict[tuple, Image.Image | None] = {}
_TIMAGE_CACHE_MAX = 1024
_timage_cache_order: list[tuple] = []  # LRU order (oldest first)


def _get_timage_cached(
    text: str,
    config: TextConfig | None,
    max_height: int | None,
) -> Image.Image | None:
    """Cached wrapper for get_timage. Uses LRU eviction."""
    if not text:
        return None

    resolved_config = config or TextConfig()
    cache_key: tuple = (
        text,
        str(resolved_config.font_path),
        str(resolved_config.italic_font_path),
        resolved_config.font_size,
        resolved_config.max_width,
        max_height,
        resolved_config.color,
        resolved_config.line_spacing,
        resolved_config.alignment.value,
    )

    if cache_key in _timage_cache:
        return _timage_cache[cache_key]

    result = _render_timage(text, resolved_config, max_height)

    # LRU eviction
    if len(_timage_cache) >= _TIMAGE_CACHE_MAX:
        oldest = _timage_cache_order.pop(0)
        _timage_cache.pop(oldest, None)
    _timage_cache[cache_key] = result
    _timage_cache_order.append(cache_key)

    return result


def _render_timage(
    text: str,
    config: TextConfig,
    max_height: int | None,
) -> Image.Image | None:
    """Internal renderer — the original get_timage logic, now cache-backed."""
    # Use lazy-initialized module-level singleton for text measurement (PERF-010)
    draw = _get_measure_draw()

    styled_words = _parse_rich_text(text, config, draw)
    if not styled_words:
        return None

    # Determine space width only for estimating line count if needed,
    # but tokens now contain their own whitespace characters.
    default_font, _ = _get_font("", config)
    # Note: space_width is no longer used for layout as tokens now contain their own whitespace characters.

    # Apply balanced wrapping (now operates on explicit whitespace tokens)
    lines = _wrap_rich_text_balanced(styled_words, config.max_width)
    if not lines:
        return None

    ascent, descent = default_font.getmetrics()
    line_height = ascent + descent
    total_text_height = len(lines) * line_height + (max(0, len(lines) - 1)) * config.line_spacing

    # Calculate final canvas dimensions
    actual_max_height = max_height if max_height is not None else config.height
    canvas_height = actual_max_height if actual_max_height is not None else total_text_height

    # When max_width is None, compute actual width from widest line
    effective_max_width = config.max_width if config.max_width is not None else max(line.width for line in lines)

    timage = Image.new("RGBA", (effective_max_width, canvas_height), (0, 0, 0, 0))
    timage_draw = ImageDraw.Draw(timage)

    # Render lines onto the new canvas
    _draw_lines(timage_draw, lines, 0, effective_max_width, ascent, line_height, config)

    return timage


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    """Measures the advance width of a given text string.

    Args:
        draw: ImageDraw instance for measuring text.
        text: Text string to measure.
        font: Font object for rendering.

    Returns:
        int: Text width in pixels.
    """
    return int(draw.textlength(text, font=font))
