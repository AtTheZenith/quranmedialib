"""Text layout and wrapping logic for QuranMediaLib.

This module provides low-level types and algorithms for arranging text,
including rich text wrapping and inverted pyramid line balancing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PIL import ImageFont

from quranmedialib.modules.knuth_plass import knuth_plass_breaks_optimized, knuth_plass_breaks_tex
from quranmedialib.types import BalancingMode

if TYPE_CHECKING:
    from PIL.ImageFont import FreeTypeFont, ImageFont

    from quranmedialib.types import Color

logger = logging.getLogger(__name__)

# Global pyramid search bounds. Realistic inputs (a single verse or a
# translation paragraph) never exceed this word count; beyond it the quadratic
# search is skipped and callers fall back to greedy wrapping.
PYRAMID_MAX_WORDS = 256
# How many line counts above the greedy minimum the global search tries before
# giving up (strict descent is infeasible for real inputs far beyond it).
PYRAMID_SEARCH_WINDOW = 16

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

    def trim_trailing_spaces(self) -> None:
        """Removes trailing space words and updates line width."""
        while self.words and self.words[-1].text.isspace():
            last_word = self.words.pop()
            self.width -= last_word.width


def _greedy_breaks_forward(
    widths: list[int],
    spacing: int,
    max_width: int,
    max_lines: int | None = None,
) -> list[int] | None:
    """Greedy max-fill wrapping: break indices for a balanced layout.

    Deterministic O(n) single-pass fill on the space-stripped input. Each line
    packs as many words as fit within `max_width`, using the minimum possible
    number of lines. A single word wider than the container is placed on its own
    (over-long) line instead of being rejected, so this solver produces a valid
    layout for any input.

    Edge cases handled explicitly:
      - No words -> [] (no lines).
      - One word  -> [] (single line), overlong or not.
      - Overlong word -> its own line; surrounding words still pack normally.
      - No width budget (None/<=0) -> [] (everything fits on one line).
      - `max_lines` cap -> at most that many lines; returns None only when even
        the minimum achievable count (every word alone) exceeds the budget.

    Returns:
        Word indices where a new line starts, [] for a single line, or None
        only when the `max_lines` budget is unsatisfiable (impossible
        constraints).
    """
    n = len(widths)

    if n == 0:
        return []
    if n == 1 or max_width is None or max_width <= 0:
        return []

    max_w = float(max_width)
    breaks: list[int] = []
    idx = 0
    lines_used = 0
    while idx < n:
        if max_lines is not None and lines_used >= max_lines:
            return None
        line_w = float(widths[idx])
        idx += 1
        while idx < n:
            next_w = line_w + spacing + widths[idx]
            if next_w > max_w:
                break
            line_w = next_w
            idx += 1
        if idx < n:
            breaks.append(idx)
        lines_used += 1

    return breaks


def _global_breaks_pyramid(
    widths: list[int],
    spacing: int,
    max_width: int,
    max_lines: int | None,
) -> list[int] | None:
    """Global search: minimum line count, then the flattest split.

    Searches line counts L upward from the greedy max-fill lower bound and
    returns the FIRST L for which a strictly-descending layout exists. Within
    that minimal L it minimizes the sum of squared adjacent width gaps, giving
    the most rectangular (least slanted) pyramid the words allow. Deterministic,
    O(L n^2) per L, with L bounded by PYRAMID_SEARCH_WINDOW. L never exceeds
    `max_lines` (a caller-supplied page/row budget); if the budget is too tight
    for a strictly-descending layout it returns None.

    Args:
        widths: Width of each word/segment (spaces excluded).
        spacing: Fixed gap between consecutive segments.
        max_width: Maximum allowed width for any line.
        max_lines: Upper bound on the number of lines. None means no bound.

    Returns:
        List of indices where line breaks should occur, or None if no
        strictly-descending layout exists within the budget.
    """
    n = len(widths)

    if n == 0:
        return []
    if n == 1 or n > PYRAMID_MAX_WORDS:
        return None

    prefix = [0.0]
    for w in widths:
        prefix.append(prefix[-1] + w)

    def segment_width(start: int, end: int) -> float:
        return prefix[end] - prefix[start] + spacing * (end - start - 1)

    # Lower bound on L: greedy max-fill without the descent constraint.
    l0 = 1
    cur = 0.0
    for w in widths:
        if cur and cur + w + spacing > max_width:
            l0 += 1
            cur = w
        else:
            cur += w + spacing if cur else w
    if l0 <= 1:
        return None

    return _global_by_line_count(widths, prefix, spacing, max_width, l0, max_lines, segment_width)


def _global_by_line_count(
    widths: list[int],
    prefix: list[float],
    spacing: int,
    max_width: int,
    l0: int,
    max_lines: int | None,
    segment_width,
) -> list[int] | None:
    """Runs the descent DP for each feasible line count within the budget.

    Tries line counts L in [l0, budget]. The budget bounds L so a caller with
    a hard page/row limit (e.g. VImage max_rows_per_page) never receives a
    pyramid that overflows it.

    Args:
        widths: Width of each word/segment (spaces excluded).
        prefix: Prefix sums of the widths (including spacing).
        spacing: Fixed gap between consecutive segments.
        max_width: Maximum allowed width for any line.
        l0: Greedy max-fill lower bound on the line count.
        max_lines: Upper bound on the number of lines (None means no bound).
        segment_width: Callable computing the width of widths[start:end].

    Returns:
        Break indices for the flattest feasible layout, or None.
    """
    n = len(widths)

    if max_lines is not None and max_lines < l0:
        return None

    upper = min(n, l0 + PYRAMID_SEARCH_WINDOW)
    if max_lines is not None:
        upper = min(upper, max_lines + 1)

    for line_count in range(l0, upper):
        # dp[j] = (cost, last_line_width) partitioning the first j words
        # (words[0..j-1]) into one line, for j in [1, n].
        dp: dict[int, tuple[float, float]] = {}
        for j in range(1, n + 1):
            first_width = segment_width(0, j)
            if first_width <= max_width:
                dp[j] = (0.0, first_width)

        # ptr[line][j] = split point k (words[0..k-1] use `line-1` lines, the
        # remainder fills line `line`) for the first j words using `line` lines.
        ptr: dict[int, dict[int, int]] = {}

        for line in range(2, line_count + 1):
            ndp: dict[int, tuple[float, float]] = {}
            nptr: dict[int, int] = {}
            for j in range(line, n + 1):
                best_cost = float("inf")
                best_k = -1
                best_width = None
                for k in range(line - 1, j):
                    state = dp.get(k)
                    if state is None:
                        continue
                    prev_cost, prev_width = state
                    new_width = segment_width(k, j)
                    if new_width <= max_width and new_width < prev_width:
                        cost = prev_cost + (prev_width - new_width) ** 2
                        if cost < best_cost:
                            best_cost = cost
                            best_k = k
                            best_width = new_width
                if best_k >= 0:
                    ndp[j] = (best_cost, best_width)
                    nptr[j] = best_k
            dp = ndp
            ptr[line] = nptr

        if dp.get(n) is None:
            continue

        breaks: list[int] = []
        j = n
        for line in range(line_count, 1, -1):
            k = ptr[line][j]
            breaks.append(k)
            j = k
        breaks.reverse()
        return breaks

    return None


def _resolve_balancing_mode(mode: BalancingMode | str) -> BalancingMode:
    """Coerce a BalancingMode or its lowercase string name to the enum."""
    if isinstance(mode, str):
        return BalancingMode(mode.lower())
    return mode


def _greedy_fallback_reason(
    mode: BalancingMode,
    widths: list[int],
    max_width: int,
) -> str:
    """Best-known reason the greedy fallback engaged (for logged wording).

    Distinguishes who could not satisfy the constraints:
      - "word too long": a single word overruns the line (impossible for every
        solver, greedy included).
      - otherwise the constraints were impossible for the primary `mode` solver
        specifically, while the greedy fallback still produced a valid layout.

    Args:
        mode: The primary balancing solver being replaced by greedy.
        widths: Width of each word/segment (spaces excluded).
        max_width: Maximum allowed width for any line.

    Returns:
        A short descriptive reason string.
    """
    if len(widths) > 1 and max(widths) > max_width:
        return "word too long"
    return f"impossible constraints for '{mode.value}' (greedy fallback still fits)"


def _balance_for_mode(
    mode: BalancingMode,
    widths: list[int],
    spacing: int,
    target_k: int | None,
    max_width: int,
) -> list[int] | None:
    """Run the requested balancing solver, returning break indices or None.

    Handles the three primary solvers (SMOOTH, KNUTH_PLASS, TEX). FORWARD is
    handled directly by balance_lines_pyramid since it is the greedy fallback
    itself. Any solver may return None, meaning it could not produce a layout;
    the caller then falls back to greedy wrapping.

    Args:
        mode: The balancing solver to run.
        widths: Width of each word/segment (spaces excluded).
        spacing: Fixed gap between consecutive segments.
        target_k: Upper bound on the number of lines (None means no bound).
        max_width: Maximum allowed width for any line.

    Returns:
        Break indices where a new line starts, [] for a single line, or None
        when this solver produced no layout.
    """
    if mode is BalancingMode.KNUTH_PLASS:
        return knuth_plass_breaks_optimized(widths, spacing, max_width, target_k)
    if mode is BalancingMode.TEX:
        return knuth_plass_breaks_tex(widths, spacing, max_width, target_k)
    return _global_breaks_pyramid(widths, spacing, max_width, target_k)


def _text_preview(text: str | None) -> str:
    """First 100 characters of the source text for logged fallback warnings.

    A longer source is truncated to its first 100 characters, with the trailing
    "..." and "(truncated)" kept inside the quoted snippet and the closing
    quote at the very end (text='...  (truncated)').

    Args:
        text: Source text of the laid-out words. None/empty yields no preview.

    Returns:
        A `text="..."` suffix (double-quoted), or an empty string when there
        is no text.
    """
    if not text:
        return ""
    head = text[:100]
    if len(text) > 100:
        head += "... (truncated)"
    # Escape a double quote/backslash so the preview stays a single token.
    escaped = head.replace("\\", "\\\\").replace('"', '\\"')
    return f' text="{escaped}"'


def balance_lines_pyramid(
    widths: list[int],
    spacing: int,
    target_k: int,
    max_width: int,
    mode: BalancingMode | str = BalancingMode.SMOOTH,
    smooth: bool | None = None,
    text: str | None = None,
) -> list[int] | None:
    """Balanced wrapping: break indices for the requested solver.

    Dispatches to the requested `mode`:
      - FORWARD: single-pass greedy max-fill (_greedy_breaks_forward).
      - SMOOTH (default): global minimal-line, flattest-split pyramid
        (_global_breaks_pyramid).
      - KNUTH_PLASS: optimized guarded quadratic-slack DP
        (knuth_plass_breaks_optimized).
      - TEX: micro-optimized faithful TeX port (knuth_plass_breaks_tex).

    Greedy wrapping (_greedy_breaks_forward) is the unconditional fallback for
    the three linear-model solvers. When SMOOTH, KNUTH_PLASS, or TEX returns
    None (infeasible under its model, a TeX work-budget abort, an oversized
    word, or an unsatisfiable budget), this function immediately runs greedy and
    logs a warning with the reason. It returns None only when greedy itself
    cannot satisfy the constraints (true impossibility).

    Args:
        widths: Width of each word/segment (spaces excluded).
        spacing: Fixed gap between consecutive segments.
        target_k: Upper bound on the number of lines (a page/row budget such as
            VImage's max_rows_per_page, or the greedy minimum for translations).
            0/None means no bound.
        max_width: Maximum allowed width for any line.
        mode: Balancing solver to use. Accepts BalancingMode or its lowercase
            string name. Defaults to SMOOTH.
        smooth: Deprecated alias. When provided, True maps to SMOOTH and False
            to FORWARD. Takes precedence over `mode`.
        text: Source text of the laid-out words, used only to report its first
            100 characters in fallback warnings (marked "(truncated)" when
            longer). Defaults to None (no preview).

    Returns:
        Word indices where a new line starts, or None when the constraints are
        impossible for greedy as well.
    """
    if smooth is not None:
        mode = BalancingMode.SMOOTH if smooth else BalancingMode.FORWARD
    resolved = _resolve_balancing_mode(mode)
    budget = target_k or None
    preview = _text_preview(text)

    if resolved is BalancingMode.FORWARD:
        return _greedy_breaks_forward(widths, spacing, max_width, budget)

    breaks = _balance_for_mode(resolved, widths, spacing, budget, max_width)
    if breaks is not None:
        return breaks

    greedy_breaks = _greedy_breaks_forward(widths, spacing, max_width, budget)
    if greedy_breaks is None:
        reason = "impossible constraints for the greedy fallback (line budget cannot be satisfied)"
        logger.warning(
            "Line balancing mode '%s' infeasible; even the greedy fallback cannot satisfy the constraints (%s)%s.",
            resolved.value,
            reason,
            preview,
        )
    elif greedy_breaks:
        reason = _greedy_fallback_reason(resolved, widths, max_width)
        if reason == "word too long":
            logger.warning(
                "Line balancing mode '%s' fell back to greedy wrapping (%s)%s.",
                resolved.value,
                reason,
                preview,
            )
        else:
            # The primary solver's own constraint (strict descent, TeX budget,
            # slack model) could not be met, but a valid greedy layout exists;
            # record the substitution without raising warning-level noise.
            logger.debug(
                "Line balancing mode '%s' fell back to greedy wrapping (%s)%s.",
                resolved.value,
                reason,
                preview,
            )
    return greedy_breaks


def wrap_rich_text_greedy(styled_words: list[StyledWord], max_width: int | None) -> list[Line]:
    """Simple greedy line wrapping. Optimized for performance.

    Packs words left-to-right into lines of at most `max_width`, never starting
    a line with a space token. Robust across edge cases: no words, a None width
    budget (one line), or single words wider than the budget (their own line).

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

    for word in styled_words:
        w_width = word.width
        if curr_line.width + w_width > max_width:
            if curr_line.words:
                curr_line.trim_trailing_spaces()
                lines.append(curr_line)

            curr_line = Line()
            w_text = word.text

            # Don't start a new line with a space
            if w_text.isspace():
                continue

        curr_line.add_word(word)

    if curr_line.words:
        curr_line.trim_trailing_spaces()
        lines.append(curr_line)

    return lines


def wrap_rich_text_balanced(
    styled_words: list[StyledWord],
    max_width: int | None,
    mode: BalancingMode | str = BalancingMode.SMOOTH,
    smooth: bool | None = None,
) -> list[Line]:
    """Descending balanced wrapping into lines.

    Dispatches to the balancing solver chosen by `mode` (see
    balance_lines_pyramid): SMOOTH by default. When that solver finds no
    multi-line layout (None), balance_lines_pyramid already falls back to greedy
    wrapping directly. This wrapper re-runs the fallback only as a final safety
    net when even greedy cannot satisfy the line budget. When `smooth` is
    provided (deprecated) it takes precedence: True maps to SMOOTH, False to
    FORWARD.

    Args:
        styled_words: List of measured StyledWord objects.
        max_width: Maximum allowed width per line.
        mode: Balancing solver to use (BalancingMode or its lowercase string).
            Defaults to SMOOTH.
        smooth: Deprecated alias for `mode` (True=SMOOTH, False=FORWARD).

    Returns:
        List of Line objects.
    """
    if not styled_words or max_width is None or max_width <= 0:
        return wrap_rich_text_greedy(styled_words, max_width)

    # Spaces are stripped from the balancing input and reconstructed per line,
    # so a space is never the first or last token (w1 <sp> w2, never <sp> w1).
    words = [w for w in styled_words if w.text and not w.text.isspace()]
    space_width = next((float(w.width) for w in styled_words if w.text and w.text.isspace()), 0.0)
    if not words:
        return []

    _widths = [w.width for w in words]

    # Get baseline line count from greedy packing (Zero-allocation pass)
    k_target = 0
    if _widths:
        k_target = 1
        curr_w = 0.0
        for w in _widths:
            if curr_w and curr_w + w + space_width > max_width:
                k_target += 1
                curr_w = w
            else:
                curr_w += w + space_width if curr_w else w

    if k_target <= 1:
        return wrap_rich_text_greedy(styled_words, max_width)

    # Pre-extract widths for performance
    best_breaks = balance_lines_pyramid(
        widths=_widths,
        spacing=space_width,  # real space advance; spaces are not tokens here
        target_k=k_target,
        max_width=max_width,
        mode=mode,
        smooth=smooth,
        text=" ".join(w.text for w in words),
    )

    if best_breaks is None:
        return wrap_rich_text_greedy(styled_words, max_width)

    # Reconstruct final Line objects only once using the optimal breaks.
    # Breaks index the space-stripped `words` list, so interleave the original
    # space tokens back into each line (matching how greedy keeps them) so the
    # renderer draws visible gaps instead of cramming words together.
    final_lines = []
    current_line = Line()
    break_set = set(best_breaks)
    word_index = 0
    for token in styled_words:
        if token.text and token.text.isspace():
            current_line.add_word(token)
            continue
        if word_index in break_set and current_line.words:
            final_lines.append(current_line)
            current_line = Line()
        current_line.add_word(token)
        word_index += 1

    if current_line.words:
        final_lines.append(current_line)

    for line in final_lines:
        line.trim_trailing_spaces()

    return final_lines
