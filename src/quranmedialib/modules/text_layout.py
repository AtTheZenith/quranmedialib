"""Text layout and wrapping logic for QuranMediaLib.

This module provides low-level types and algorithms for arranging text,
including rich text wrapping and inverted pyramid line balancing.
"""

from __future__ import annotations

import bisect
import logging
from typing import TYPE_CHECKING

from PIL import ImageFont

if TYPE_CHECKING:
    from PIL.ImageFont import FreeTypeFont, ImageFont

    from quranmedialib.types import Color

logger = logging.getLogger(__name__)

__all__ = [
    "StyledWord",
    "Line",
    "balance_lines_pyramid",
    "wrap_rich_text_greedy",
    "wrap_rich_text_balanced",
]


class StyledWord:
    """A word with specific styling applied, ready for rendering.

    Attributes:
        text: The text content of the word.
        font: The PIL font object to use for rendering.
        color: RGBA or RGB color for the text.
        width: Measured width of the word in pixels (float for sub-pixel precision).
        height: Measured height of the word in pixels (usually ascent + descent).
        ascent: Measured ascent of the font in pixels.
        simulate_bold: Whether to simulate bold weight if not supported by font.
    """

    __slots__ = ("text", "font", "color", "width", "height", "ascent", "is_transparent", "simulate_bold")

    def __init__(
        self,
        text: str,
        font: FreeTypeFont | ImageFont,
        color: Color,
        width: float,
        height: int = 0,
        ascent: int = 0,
        is_transparent: bool = False,
        simulate_bold: bool = False,
    ):
        self.text = text
        self.font = font
        self.color = color
        self.width = width
        self.height = height
        self.ascent = ascent
        self.is_transparent = is_transparent
        self.simulate_bold = simulate_bold


class Line:
    """A collection of styled words representing a single line of text."""

    __slots__ = ("words", "width", "height")

    def __init__(self):
        self.words: list[StyledWord] = []
        self.width: float = 0.0
        self.height: int = 0

    def add_word(self, word: StyledWord, space_width: float = 0.0):
        """Adds a word to the line, accounting for word spacing.

        Args:
            word: The StyledWord to add.
            space_width: Width of the space to add before the word (if not the first word).
        """
        if self.words:
            self.width += space_width
        self.words.append(word)
        self.width += word.width
        self.height = max(self.height, word.height)


def balance_lines_pyramid(
    widths: list[int],
    spacing: int,
    target_k: int,
    max_width: int,
) -> list[int] | None:
    """Core IPL-B algorithm: finds line break indices for a top-heavy layout.

    Uses Prefix Sums + Bisection (O(K log N log W)) for high-performance partitioning.
    Attempts to create an inverted pyramid shape (W_i >= W_{i+1}).

    Args:
        widths: List of widths for each word/segment.
        spacing: Fixed spacing between segments.
        target_k: Desired number of lines.
        max_width: Maximum allowed width for any line.

    Returns:
        List of indices where line breaks should occur, or None if no valid layout exists.
    """
    if not widths:
        return []

    # Pre-calculate prefix sums for O(log N) line break lookups
    n = len(widths)
    # sums[i] = width of first i items + (i-1) spacings
    sums = [0] * (n + 1)
    for i, w in enumerate(widths):
        sums[i + 1] = sums[i] + w + spacing

    _spacing = spacing
    _target_k = target_k
    _n = n

    def check_feasibility(w1_limit: int) -> int:
        """Finds k using bisection over prefix sums. Zero allocations, O(K log N)."""
        curr_idx = 0
        prev_limit = w1_limit
        count = 0

        while curr_idx < _n:
            count += 1
            if count > _target_k:
                return 9999

            # Find max j such that (sums[j] - sums[curr_idx]) - spacing <= prev_limit
            # Target = prev_limit + spacing + sums[curr_idx]
            target = prev_limit + _spacing + sums[curr_idx]
            next_idx = bisect.bisect_right(sums, target) - 1

            if next_idx <= curr_idx:
                return 9999

            # Update limit for next line (Inverted Pyramid constraint)
            prev_limit = (sums[next_idx] - sums[curr_idx]) - _spacing
            curr_idx = next_idx

        return count

    # Bounds
    max_w = max(widths)
    total_w = sums[n] - spacing

    low = max(max_w, total_w // target_k)
    high = max_width
    best_w1 = -1

    while low <= high:
        mid = (low + high) // 2
        if check_feasibility(mid) <= target_k:
            best_w1 = mid
            high = mid - 1
        else:
            low = mid + 1

    if best_w1 == -1:
        return None

    # Final pass: Reconstruct breaks
    breaks = []
    curr_idx = 0
    prev_limit = best_w1
    while curr_idx < n:
        target = prev_limit + spacing + sums[curr_idx]
        next_idx = bisect.bisect_right(sums, target) - 1
        if next_idx < n:
            breaks.append(next_idx)
            prev_limit = (sums[next_idx] - sums[curr_idx]) - spacing
            curr_idx = next_idx
        else:
            break

    return breaks


def wrap_rich_text_greedy(styled_words: list[StyledWord], max_width: int | None) -> list[Line]:
    """Simple greedy line wrapping. Optimized for performance.

    Args:
        styled_words: List of measured StyledWord objects.
        max_width: Maximum allowed width per line. If None, all words placed on one line.

    Returns:
        List of Line objects.
    """
    if not styled_words:
        return []

    if max_width is None:
        line = Line()
        for w in styled_words:
            line.add_word(w)
        return [line]

    lines = []
    curr_line = Line()
    curr_words = curr_line.words
    curr_w = 0
    curr_h = 0

    for word in styled_words:
        w_width = word.width
        w_height = word.height
        if curr_w + w_width > max_width:
            if curr_words:
                # Strip trailing space from previous line
                if curr_words[-1].text.isspace():
                    last_space = curr_words.pop()
                    curr_w -= last_space.width

                curr_line.width = curr_w
                curr_line.height = curr_h
                lines.append(curr_line)

            curr_line = Line()
            curr_words = curr_line.words
            curr_w = 0
            curr_h = 0

            w_text = word.text

            # Don't start a new line with a space
            if w_text.isspace():
                continue

        curr_words.append(word)
        curr_w += w_width
        if w_height > curr_h:
            curr_h = w_height

    if curr_words:
        # Strip trailing space from last line
        if curr_words[-1].text.isspace():
            last_space = curr_words.pop()
            curr_w -= last_space.width
        curr_line.width = curr_w
        curr_line.height = curr_h
        lines.append(curr_line)

    return lines


def wrap_rich_text_balanced(styled_words: list[StyledWord], max_width: int | None) -> list[Line]:
    """Inverted pyramid line balancing (IPL-B).

    Strictly enforces W_i >= W_{i+1} to create an inverted pyramid shape.
    Delegates to balance_lines_pyramid for the optimal break search.

    Args:
        styled_words: List of measured StyledWord objects.
        max_width: Maximum allowed width per line.

    Returns:
        List of Line objects.
    """
    if not styled_words or max_width is None:
        return wrap_rich_text_greedy(styled_words, max_width)

    # Use space-stripped content as base for balancing (spaces are handled by widths)
    content = [w for w in styled_words if w.text.strip() or w.text == " "]
    if not content:
        return []

    _widths = [w.width for w in content]

    # Get baseline line count from greedy packing (Zero-allocation pass)
    k_target = 0
    if _widths:
        k_target = 1
        curr_w = 0
        for w in _widths:
            if curr_w + w > max_width:
                k_target += 1
                curr_w = w
            else:
                curr_w += w

    if k_target <= 1:
        return wrap_rich_text_greedy(content, max_width)

    # Pre-extract widths for performance
    best_breaks = balance_lines_pyramid(
        widths=_widths,
        spacing=0,  # spacing already baked into StyledWord widths
        target_k=k_target,
        max_width=max_width,
    )

    # Reconstruct final Line objects only once using the optimal breaks
    if best_breaks is None:
        return wrap_rich_text_greedy(content, max_width)

    final_lines = []
    current_line = Line()
    break_set = set(best_breaks)
    for i, word in enumerate(content):
        if i in break_set:
            final_lines.append(current_line)
            current_line = Line()

        current_line.words.append(word)
        current_line.width += word.width
        if word.height > current_line.height:
            current_line.height = word.height

    if current_line.words:
        final_lines.append(current_line)

    # Post-process: Strip trailing spaces from each line
    for line in final_lines:
        words = line.words
        while words and words[-1].text.isspace():
            last_word = words.pop()
            line.width -= last_word.width

    return final_lines
