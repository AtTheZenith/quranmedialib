from __future__ import annotations

import logging
import math
import re
from functools import lru_cache
from typing import Any, Sequence

from PIL import Image, ImageDraw

from quranmedialib.modules.font_cache import _load_font_base
from quranmedialib.modules.text_layout import Line, StyledWord, wrap_rich_text_balanced, wrap_rich_text_greedy
from quranmedialib.types import MAX_CANVAS_DIMENSION, MAX_TEXT_CHARS, MAX_TEXT_WORDS, TextConfig

logger = logging.getLogger(__name__)

__all__ = [
    "get_timage",
    "format_isolation_text",
    "normalize_highlight_style",
    "prepare_translation_segments",
    "LazyTranslationImages",
]


def normalize_highlight_style(
    highlight_segments: str | list[str] | None,
) -> str:
    """Normalizes various highlight input formats into a valid rich text tag body.

    Returns a style payload of the form ``#<b|i|bi>#<hex>#`` (ready to be followed
    by text and a closing ``#``), always carrying an explicit color so downstream
    parsing never falls back to a legacy form.

    Args:
        highlight_segments: A style string, list, or None.

    Returns:
        str: A modern tag prefix such as ``#b#ffd700ff#``.
    """
    if highlight_segments is None:
        return _DEFAULT_HIGHLIGHT_PREFIX

    raw = highlight_segments if isinstance(highlight_segments, str) else str(highlight_segments)
    raw = raw.strip()

    # Accept modern full tags (with or without color) and bare style prefixes.
    m = _RE_TAG_SUFFIX.match(raw)
    if m is None:
        return _DEFAULT_HIGHLIGHT_PREFIX

    style, color = m.group(1), m.group(2)
    if not style:
        style = "b"
    if not color:
        color = _DEFAULT_HIGHLIGHT_HEX
    return f"#{style}#{color}#"


# Pattern for a tag prefix: #style# or #style#color#
_RE_TAG_SUFFIX = re.compile(r"^#([bi]*)#(?:([0-9a-fA-F]{6}|[0-9a-fA-F]{8})#)?$")

_DEFAULT_HIGHLIGHT_HEX = "ffd700ff"  # matches TextConfig.highlight_color (255, 215, 0, 255)
_DEFAULT_HIGHLIGHT_PREFIX = f"#b#{_DEFAULT_HIGHLIGHT_HEX}#"

# Stroke width (px) used when simulating bold weight on fonts without a wght
# axis. Keep draw-time stroke and measurement-time ink widest in sync so a bold
# word's advance includes its simulated overhang and never clips its right glyph.
_SIMULATE_BOLD_STROKE_WIDTH = 1


def prepare_translation_segments(text: str | list[str] | None) -> list[str]:
    """Tokenizes text into words and spaces. Handles strings and lists."""
    if text is None:
        return []
    return text if isinstance(text, list) else re.findall(r"\S+|\s+", str(text))


def format_isolation_text(
    verse_text: str | list[str] | None,
    target_word_index: int = -1,
    *args: Any,
    **kwargs: Any,
) -> str:
    """Formats verse text for word isolation using the modern rich text grammar.

    Every word is emitted as an independent tag; the target word is highlighted
    and the remaining words are made transparent so only the target renders.

    Args:
        verse_text: The verse text as a string or list of words.
        target_word_index: Index of the word to highlight.
        *args: Positional highlight_style (legacy compatibility).
        **kwargs:
            - target_index: Alias for target_word_index.
            - highlight_style: Modern tag prefix (e.g. ``#b#ffd700ff#``).

    Returns:
        str: A rich text string of the form ``<highlighted> <transparent> ...``.

    Raises:
        ValueError: If target_index is negative or out of bounds.
    """
    t_idx = kwargs.get("target_index", target_word_index)
    if t_idx == -1 and args and isinstance(args[0], int):
        t_idx = args[0]

    style = kwargs.get("highlight_style")
    if not isinstance(style, str) and args and isinstance(args[0], str):
        style = args[0]
    style = normalize_highlight_style(style)

    words = verse_text if isinstance(verse_text, list) else str(verse_text).split()
    if t_idx < 0:
        raise ValueError("target_index must be non-negative")
    if t_idx >= len(words):
        raise ValueError(f"target_index {t_idx} is out of bounds for text with {len(words)} words")

    parts = []
    for i, word in enumerate(words):
        if i == t_idx:
            parts.append(f"{style}{word}#")
        else:
            parts.append(f"#b#00000000#{word}#")
    return " ".join(parts)


def _validate_input_bounds(s_text: str) -> None:
    """Reject pathological inputs before any measurement or canvas allocation.

    Args:
        s_text: The raw text to validate.

    Raises:
        ValueError: If `s_text` exceeds MAX_TEXT_CHARS or MAX_TEXT_WORDS tokens.
    """
    if len(s_text) > MAX_TEXT_CHARS:
        raise ValueError(f"text length {len(s_text)} exceeds maximum of {MAX_TEXT_CHARS} characters")
    # N whitespace-delimited words need at least 2N-1 characters, so a text this
    # short cannot reach the word limit; skip the tokenizing count in the hot path.
    if len(s_text) >= 2 * MAX_TEXT_WORDS - 1:
        word_count = len(re.findall(r"\S+", s_text))
        if word_count > MAX_TEXT_WORDS:
            raise ValueError(f"text has {word_count} words, exceeding maximum of {MAX_TEXT_WORDS}")


def _resolve_max_height(config: TextConfig, kwargs: dict[str, Any]) -> int | None:
    """Resolve and validate the `max_height` constraint from kwargs or config.

    Args:
        config: The text configuration (source of the default height).
        kwargs: Caller-supplied overrides (`max_height` alias).

    Returns:
        The effective max_height, or None if unbounded.

    Raises:
        ValueError: If max_height is negative or exceeds MAX_CANVAS_DIMENSION.
    """
    max_height = kwargs.get("max_height", config.height)
    if max_height is not None:
        if max_height < 0:
            raise ValueError("Width and height must be >= 0")
        if max_height > MAX_CANVAS_DIMENSION:
            raise ValueError(f"max_height exceeds maximum limit of {MAX_CANVAS_DIMENSION}, got {max_height}")
    return max_height


def _compute_canvas_size(
    lines: list[Line],
    l_spacing: float,
    max_height: int | None,
) -> tuple[int, int, float]:
    """Compute the pixel canvas size and the layout width for a wrapped text.

    Args:
        lines: Wrapped text lines.
        l_spacing: Vertical spacing between lines.
        max_height: Optional height constraint (from config/kwargs).

    Returns:
        tuple[int, int, float]: (canvas width, canvas height, total text width).
    """
    total_width = 0.0
    total_height = 0.0
    for line in lines:
        if line.width > total_width:
            total_width = line.width
        total_height += line.height

    total_height += (len(lines) - 1) * l_spacing

    # Apply height constraint if provided
    if max_height is not None and max_height > 0 and total_height > max_height:
        total_height = float(max_height)

    # Final sanity check to avoid SystemError on 0-dimension images.
    # Add a 1px safety margin to total_width to prevent edge glyph clipping.
    tw = math.ceil(max(total_width + 1.0, 1.0))
    th = math.ceil(max(total_height, 1.0))

    # Hard cap the canvas. A single word wider than the container is placed on
    # its own line and can exceed `max_width`, so without this cap a huge glyph
    # could force an unbounded image allocation (decompression-bomb vector).
    if tw > MAX_CANVAS_DIMENSION or th > MAX_CANVAS_DIMENSION:
        logger.warning(
            "Rendered text canvas %dx%d exceeds the %dpx cap; clamping",
            tw,
            th,
            MAX_CANVAS_DIMENSION,
        )
        tw = min(tw, MAX_CANVAS_DIMENSION)
        th = min(th, MAX_CANVAS_DIMENSION)

    return tw, th, total_width


def _layout_text_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[StyledWord | Line],
    total_width: float,
    max_height: int | None,
    use_mask: bool,
    l_spacing: float,
) -> None:
    """Draw wrapped text onto the canvas, centering each line horizontally.

    Words sharing the same style are batched into a single draw call; stroke
    ink is reserved for simulated bold so glyphs never clip their right edge.

    Args:
        draw: Canvas draw handle.
        lines: Wrapped text lines to render.
        total_width: Text layout width, used for horizontal centering.
        max_height: Optional vertical cap; lines beyond it are skipped.
        use_mask: If True, draw into an 'L' mask with white ink.
        l_spacing: Vertical spacing between lines.
    """
    current_y = 0.0
    for line in lines:
        l_height = line.height
        if max_height is not None and current_y + l_height > max_height:
            break

        # Horizontal centering (using float precision)
        line_x = (total_width - line.width) / 2.0

        # 1. Find max ascent for baseline alignment
        max_ascent = 0
        for word in line.words:
            if word.ascent > max_ascent:
                max_ascent = word.ascent

        # 2. Render words in batches of same style
        curr_x = line_x
        batch_words = []
        last_style = None

        def _flush_batch() -> None:
            """Draws the accumulated batch with its style, then advances the cursor."""
            nonlocal curr_x
            if not batch_words:
                return
            txt = "".join(w.text for w in batch_words)
            sf = last_style[0]
            sa = batch_words[0].ascent
            simulate_bold = last_style[2]
            stroke_width = _SIMULATE_BOLD_STROKE_WIDTH if simulate_bold else 0
            stroke_fill = 255 if (use_mask and simulate_bold) else last_style[1]
            draw.text(
                (curr_x, current_y + (max_ascent - sa)),
                txt,
                font=sf,
                fill=255 if use_mask else last_style[1],
                stroke_width=stroke_width,
                stroke_fill=stroke_fill if simulate_bold else None,
            )
            curr_x += sf.getlength(txt)
            batch_words.clear()

        for word in line.words:
            f = word.font
            c = word.color
            simulate_bold = word.simulate_bold
            style = (f, c, simulate_bold)

            if last_style is not None and style != last_style:
                _flush_batch()

            batch_words.append(word)
            last_style = style

        if batch_words:
            _flush_batch()

        current_y += l_height + l_spacing


def get_timage(
    text: str | None,
    config: TextConfig | None = None,
    highlight_segments: str | list[str] | None = None,
    **kwargs: Any,
) -> Image.Image | None:
    """Renders multi-line translation text. Returns None if text is empty.

    Security: text longer than MAX_TEXT_CHARS (or with more than MAX_TEXT_WORDS
    tokens) is rejected before any measurement, so untrusted strings cannot
    drive layout/rendering cost or canvas allocation unbounded.

    Raises:
        ValueError: If `text` exceeds MAX_TEXT_CHARS or MAX_TEXT_WORDS, or if
            `max_height` is negative or exceeds MAX_CANVAS_DIMENSION.
    """
    if text is None:
        return None
    s_text = str(text)
    if not s_text.strip():
        return None

    # Reject pathological inputs before any tokenization, measurement, or canvas
    # allocation so an untrusted string cannot drive memory/layout cost unbounded.
    _validate_input_bounds(s_text)

    if config is None:
        config = TextConfig()

    # Support max_height as kwarg alias for config.height
    max_height = _resolve_max_height(config, kwargs)

    # Measure and wrap
    styled_words = _parse_rich_text(s_text, config, None)

    if config.balanced_wrapping:
        lines = wrap_rich_text_balanced(styled_words, config.max_width, mode=config.balancing_mode)
    else:
        lines = wrap_rich_text_greedy(styled_words, config.max_width)

    if not lines:
        return None

    tw, th, total_width = _compute_canvas_size(lines, config.line_spacing, max_height)

    # Detect if we can use an 'L' mask (no color tags in original text)
    use_mask = "#" not in s_text
    img = Image.new("L" if use_mask else "RGBA", (tw, th), 0 if use_mask else (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _layout_text_lines(draw, lines, total_width, max_height, use_mask, config.line_spacing)

    if use_mask:
        # Convert 'L' mask to 'RGBA' using the base color to preserve performance
        # while ensuring the output image is transparent-capable.
        result = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        result.paste(config.color, (0, 0), mask=img)
        return result

    return img


# Cache for font baseline metrics (ascent + descent) and ascent
_font_metrics_cache: dict[tuple[str, int], tuple[int, int]] = {}


@lru_cache(maxsize=4096)
def _get_text_metrics(token: str, font_path: str, font_size: int) -> tuple[float, int, int]:
    """Cached wrapper for text dimension measurement.

    Uses font.getlength() for performance on word width measurements.
    """
    font = _load_font_base(font_path, font_size)

    # getlength is significantly faster than textbbox for width
    w = font.getlength(token)

    # Use cached font height/ascent if available
    key = (font_path, font_size)
    if key in _font_metrics_cache:
        h, ascent = _font_metrics_cache[key]
    else:
        ascent, descent = font.getmetrics()
        h = ascent + descent
        _font_metrics_cache[key] = (h, ascent)

    return w, h, ascent


def _hex_to_rgba(hex_str: str) -> tuple[int, int, int, int]:
    """Converts a 6- or 8-digit hex string to an RGBA tuple.

    8-digit input is interpreted as RRGGBBAA (32-bit); 6-digit input is
    interpreted as RRGGBB (24-bit) with full opacity.
    """
    if len(hex_str) == 6:
        hex_str += "ff"
    return tuple(int(hex_str[i : i + 2], 16) for i in (0, 2, 4, 6))


# Regex for structured tags: #style#color#text#
# Group 1: style (b, i, or combined bi), Group 2: color (6 or 8 hex), Group 3: text
# The closing '#' is mandatory per the modern rich text spec.
_RE_RICH_TAG = re.compile(r"#([bi]+)#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})#([^#]+)#")


def _malformed_tag_snippets(s_text: str, matches: list[re.Match[str]]) -> list[str]:
    """Return whitespace-delimited fragments that contain stray '#' characters.

    Only '#' falling outside a valid tag's span is stray. Fragments are bounded
    by whitespace or a valid tag boundary, so a correctly nested '#b#...#text#'
    never leaks into a reported malformed tag.
    """
    covered: list[tuple[int, int]] = [(m.start(), m.end()) for m in matches]
    snippets: list[str] = []

    def covered_at(pos: int) -> bool:
        return any(start <= pos < end for start, end in covered)

    for i, char in enumerate(s_text):
        if char != "#" or covered_at(i):
            continue
        left = i
        while left > 0 and s_text[left - 1] != " " and not covered_at(left - 1):
            left -= 1
        right = i + 1
        while right < len(s_text) and s_text[right] != " " and not covered_at(right):
            right += 1
        snippet = s_text[left:right]
        if snippet not in snippets:
            snippets.append(snippet)
    return snippets


def _parse_rich_text(
    text: object,
    config: TextConfig,
    draw: ImageDraw.ImageDraw,
) -> list[StyledWord]:
    """Tokenizes and measures text, parsing structured #style#color#text# tags.

    The parser identifies tags in the format #style#color#text#, where style is
    'b', 'i', or 'bi', color is a 6- or 8-digit hex string, and text is the
    content to render. The closing '#' is mandatory.
    """
    s_text = str(text)

    # 1. Plain-text Fast Path
    if "#" not in s_text:
        f = _load_font_base(str(config.font_path), config.font_size)
        color = config.color

        key = (str(config.font_path), config.font_size)
        if key in _font_metrics_cache:
            h, ascent = _font_metrics_cache[key]
        else:
            ascent, descent = f.getmetrics()
            h = ascent + descent
            _font_metrics_cache[key] = (h, ascent)

        _get_len = f.getlength
        w_cache: dict[str, float] = {}
        _StyledWord = StyledWord

        res = []
        segments = prepare_translation_segments(s_text)
        for s in segments:
            if s in w_cache:
                w = w_cache[s]
            else:
                w = _get_len(s)
                w_cache[s] = w
            res.append(_StyledWord(s, f, color, w, h, ascent))
        return res

    # 2. Rich-text path (Parsing structured tags)
    styled_words = []
    _StyledWord = StyledWord
    _metrics = _get_text_metrics

    f_norm_path = str(config.font_path)
    f_norm_size = config.font_size
    _, h_norm, a_norm = _metrics("", f_norm_path, f_norm_size)
    c_norm = config.color
    font_norm = _load_font_base(f_norm_path, f_norm_size)

    matches = list(_RE_RICH_TAG.finditer(s_text))

    # Each valid tag consumes exactly 4 '#' (opening, after style, after color,
    # closing). Any remaining '#' was not regexed into a rich tag.
    unconsumed_hashes = s_text.count("#") - 4 * len(matches)
    if unconsumed_hashes > 0 and not config.ignore_non_token_hashtags:
        malformed = _malformed_tag_snippets(s_text, matches)
        logger.warning(
            "Malformed rich text tag(s) %s (not part of a rich text tag) in: %r. "
            "Expected '#<style>#<color>#text#' syntax, e.g. '#b#ff0000ff#Bold#'. "
            "To suppress this warning, set TextConfig(ignore_non_token_hashtags=True).",
            ", ".join(f"'{s}'" for s in malformed) or f"{unconsumed_hashes} character(s)",
            s_text,
        )

    last_pos = 0
    for match in matches:
        if plain_segment := s_text[last_pos : match.start()]:
            for s in prepare_translation_segments(plain_segment):
                w, h, a = _metrics(s, f_norm_path, f_norm_size)
                styled_words.append(_StyledWord(s, font_norm, c_norm, w, h, a))

        # Parse the tag: #style#color#text#
        style_code = match.group(1)
        color_hex = match.group(2)
        tag_text = match.group(3)

        tag_color = _hex_to_rgba(color_hex)

        # Determine font based on style
        wants_bold = "b" in style_code
        wants_italic = "i" in style_code

        if wants_italic:
            # Italic (and bold-italic) use the configured italic font.
            try:
                f_tag = _load_font_base(str(config.italic_font_path), f_norm_size)
            except Exception:
                f_tag = font_norm
        else:
            f_tag = font_norm
        is_bold = wants_bold

        # Measure and create words for the tag text
        for s in prepare_translation_segments(tag_text):
            font_path = str(f_tag.path if hasattr(f_tag, "path") else f_norm_path)
            font_size = f_tag.size if hasattr(f_tag, "size") else f_norm_size
            w, h, a = _metrics(s, font_path, font_size)
            if is_bold:
                # The advance must reserve the simulated stroke ink (one width
                # per side) so bold text never clips its right-most glyph.
                w += 2 * _SIMULATE_BOLD_STROKE_WIDTH
            styled_words.append(_StyledWord(s, f_tag, tag_color, w, h, a, simulate_bold=is_bold))

        last_pos = match.end()

    if trailing_text := s_text[last_pos:]:
        for s in prepare_translation_segments(trailing_text):
            w, h, a = _metrics(s, f_norm_path, f_norm_size)
            styled_words.append(_StyledWord(s, font_norm, c_norm, w, h, a))

    return styled_words


class _NotRendered:
    """Sentinel to distinguish 'not yet rendered' from 'rendered as None'."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "_NOT_RENDERED"


_NOT_RENDERED = _NotRendered()


class LazyTranslationImages(Sequence):
    """Lazy sequence that defers get_timage() calls until items are accessed.

    This avoids rendering translation images that are never used (e.g., when
    a verse fits on fewer pages than translations prepared).

    The class implements the `Sequence` abstract base class, making it compatible
    with any code expecting a list-like interface (iteration, indexing, len).
    """

    __slots__ = ("_texts", "_config", "_cache")

    def __init__(self, texts: list[str], config: TextConfig) -> None:
        """Initialize the lazy wrapper.

        Args:
            texts: List of translation text strings to render.
            config: Text configuration for rendering.
        """
        self._texts = texts
        self._config = config
        self._cache: list[Image.Image | None | _NotRendered] = [_NOT_RENDERED] * len(texts)

    def __len__(self) -> int:
        return len(self._texts)

    def __getitem__(self, index: int) -> Image.Image | None:
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self._texts)))]
        if index < 0:
            raise IndexError("negative index not supported; use non-negative indices")
        if index >= len(self._texts):
            raise IndexError(f"index {index} out of range for {len(self._texts)} texts")
        if self._cache[index] is _NOT_RENDERED:
            self._cache[index] = get_timage(self._texts[index], self._config)

        return self._cache[index]

    def render_all(self) -> list[Image.Image | None]:
        """Force rendering of all translation images.

        Useful when all translations are needed at once (e.g., for
        separate translation pages mode).

        Returns:
            List of rendered images (or None for empty translations).
        """
        return [self[i] for i in range(len(self._texts))]
