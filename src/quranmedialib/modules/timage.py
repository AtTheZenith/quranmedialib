from __future__ import annotations

import logging
import math
import re
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Sequence

from PIL import Image, ImageDraw

from quranmedialib.modules.font_cache import _load_font_base, get_font
from quranmedialib.modules.text_layout import (
    Line,
    StyledWord,
    balance_lines_pyramid,
    wrap_rich_text_balanced,
    wrap_rich_text_greedy,
)
from quranmedialib.types import TextConfig

if TYPE_CHECKING:
    from quranmedialib.modules.text_layout import Line, StyledWord
    from quranmedialib.types import TextConfig

logger = logging.getLogger(__name__)

__all__ = [
    "get_timage",
    "format_isolation_text",
    "normalize_highlight_style",
    "prepare_translation_segments",
    "LazyTranslationImages",
]


def normalize_highlight_style(
    highlight_segments: Any,
) -> str:
    """Normalizes various highlight input formats into a style string.

    Legacy API expects string return (e.g. '#b#').
    """
    if highlight_segments is None:
        return "#b#"
    if isinstance(highlight_segments, str):
        return highlight_segments
    return str(highlight_segments)


def prepare_translation_segments(text: Any) -> list[str]:
    """Tokenizes text into words and spaces. Handles strings and lists."""
    if text is None:
        return []
    if isinstance(text, list):
        return text
    # re.findall is implemented in C and much faster than manual Python loops
    return re.findall(r"\S+|\s+", str(text))


def format_isolation_text(verse_text: Any, target_word_index: int = -1, *args: Any, **kwargs: Any) -> str:
    """Formats verse text for word isolation. Accepts list/str and target_index kwarg."""
    t_idx = kwargs.get("target_index", target_word_index)
    if t_idx == -1 and args:
        t_idx = args[0]

    style = kwargs.get("highlight_style", "#b#")
    if not isinstance(style, str):
        style = "#b#"

    # Handle list input
    if isinstance(verse_text, list):
        words = verse_text
    else:
        words = str(verse_text).split()

    if t_idx < 0:
        raise ValueError("target_index must be non-negative")
    if t_idx >= len(words):
        raise ValueError(f"target_index {t_idx} is out of bounds for text with {len(words)} words")

    # Apply brackets and style
    words = list(words)
    words[t_idx] = f"[{words[t_idx]}]"

    result = " ".join(words)
    if style not in result:
        return f"{style}{result}"
    return result


def get_timage(
    text: str | None,
    config: TextConfig | None = None,
    highlight_segments: Any = None,
    **kwargs: Any,
) -> Image.Image | None:
    """Renders multi-line translation text. Returns None if text is empty."""
    if text is None:
        return None
    s_text = str(text)
    if not s_text.strip():
        return None

    if config is None:
        config = TextConfig()

    # Support max_height as kwarg alias for config.height
    max_height = kwargs.get("max_height", config.height)
    if max_height is not None and max_height < 0:
        raise ValueError("Width and height must be >= 0")

    # Measure and wrap
    styled_words = _parse_rich_text(s_text, config, None)

    if config.balanced_wrapping:
        lines = wrap_rich_text_balanced(styled_words, config.max_width)
    else:
        lines = wrap_rich_text_greedy(styled_words, config.max_width)

    if not lines:
        return None

    total_width = 0.0
    total_height = 0.0
    for line in lines:
        if line.width > total_width:
            total_width = line.width
        total_height += line.height

    l_spacing = config.line_spacing
    total_height += (len(lines) - 1) * l_spacing

    # Apply height constraint if provided
    if max_height is not None and max_height > 0 and total_height > max_height:
        total_height = float(max_height)

    # Final sanity check to avoid SystemError on 0-dimension images.
    # Add a 1px safety margin to total_width to prevent edge glyph clipping.
    tw = math.ceil(max(total_width + 1.0, 1.0))
    th = math.ceil(max(total_height, 1.0))

    # Detect if we can use an 'L' mask (no color tags in original text)
    use_mask = "#" not in s_text
    img = Image.new("L" if use_mask else "RGBA", (tw, th), 0 if use_mask else (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _draw_text = draw.text

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
            wa = word.ascent
            if wa > max_ascent:
                max_ascent = wa

        # 2. Render words in batches of same style
        curr_x = line_x
        batch_words = []
        last_style = None

        for word in line.words:
            f = word.font
            c = word.color
            style = (f, c)

            if last_style is not None and style != last_style:
                # Flush batch
                txt = "".join(w.text for w in batch_words)
                sf = last_style[0]
                sa = batch_words[0].ascent
                _draw_text(
                    (curr_x, current_y + (max_ascent - sa)),
                    txt,
                    font=sf,
                    fill=255 if use_mask else last_style[1],
                )
                # Use font.getlength for accurate batch advance
                curr_x += sf.getlength(txt)
                batch_words = []

            batch_words.append(word)
            last_style = style

        if batch_words and last_style:
            txt = "".join(w.text for w in batch_words)
            sf = last_style[0]
            sa = batch_words[0].ascent
            _draw_text(
                (curr_x, current_y + (max_ascent - sa)),
                txt,
                font=sf,
                fill=255 if use_mask else last_style[1],
            )

        current_y += l_height + l_spacing
 
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


# Pre-compiled regex for tag stripping to avoid repeated compilation in hot path
_RE_STRIP_TAGS = re.compile(r"#[^#]+#")


def _parse_rich_text(
    text: Any,
    config: TextConfig,
    draw: ImageDraw.ImageDraw,
) -> list[StyledWord]:
    """Tokenizes and measures text. Detects plain-text fast-path to skip style checks."""
    clean_text = _RE_STRIP_TAGS.sub("", str(text))
    segments = prepare_translation_segments(clean_text)

    # 1. Plain-text Fast Path
    if "[" not in clean_text:
        f = _load_font_base(str(config.font_path), config.font_size)
        color = config.color

        # Get metrics once (baseline)
        key = (str(config.font_path), config.font_size)
        if key in _font_metrics_cache:
            h, ascent = _font_metrics_cache[key]
        else:
            ascent, descent = f.getmetrics()
            h = ascent + descent
            _font_metrics_cache[key] = (h, ascent)

        # Local cache for word widths in this call
        _get_len = f.getlength
        w_cache: dict[str, float] = {}
        _StyledWord = StyledWord

        res = []
        for s in segments:
            if s in w_cache:
                w = w_cache[s]
            else:
                w = _get_len(s)
                w_cache[s] = w
            res.append(_StyledWord(s, f, color, w, h, ascent))
        return res

    # 2. Rich-text path (Style switching)
    styled_words = []
    _StyledWord = StyledWord
    _load_font = _load_font_base
    _metrics = _get_text_metrics

    f_norm_path = str(config.font_path)
    f_high_path = str(config.highlight_font_path)
    f_norm_size = config.font_size
    f_high_size = config.highlight_font_size

    _, h_norm, a_norm = _metrics("", f_norm_path, f_norm_size)
    _, h_high, a_high = _metrics("", f_high_path, f_high_size)

    c_norm = config.color
    c_high = config.highlight_color

    # Pre-resolve font objects outside hot loop
    font_norm = _load_font(f_norm_path, f_norm_size)
    font_high = _load_font(f_high_path, f_high_size)

    # Local caches for style widths
    w_cache_norm: dict[str, int] = {}
    w_cache_high: dict[str, int] = {}

    for segment in segments:
        is_highlight = segment.startswith("[") and segment.endswith("]")
        token = segment[1:-1] if is_highlight else segment

        if is_highlight:
            if token in w_cache_high:
                w = w_cache_high[token]
            else:
                w, _, _ = _metrics(token, f_high_path, f_high_size)
                w_cache_high[token] = w
            styled_words.append(_StyledWord(token, font_high, c_high, w, h_high, a_high))
        else:
            if token in w_cache_norm:
                w = w_cache_norm[token]
            else:
                w, _, _ = _metrics(token, f_norm_path, f_norm_size)
                w_cache_norm[token] = w
            styled_words.append(_StyledWord(token, font_norm, c_norm, w, h_norm, a_norm))

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

        result = self._cache[index]
        return None if isinstance(result, _NotRendered) else result

    def render_all(self) -> list[Image.Image | None]:
        """Force rendering of all translation images.

        Useful when all translations are needed at once (e.g., for
        separate translation pages mode).

        Returns:
            List of rendered images (or None for empty translations).
        """
        return [self[i] for i in range(len(self._texts))]
