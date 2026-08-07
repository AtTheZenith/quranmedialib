"""Knuth-Plass paragraph line breaking for QuranMediaLib.

Implements the dynamic-programming line-breaking algorithm of D.E. Knuth and
M.F. Plass (TeX) as described in chapter 3 of _Digital Typography_. The core
state machine (Box/Glue/Penalty objects and the active-node breakpoint search)
is the original port from the Pascal reference implementation by A.M. Kuchling,
adapted to this project's style and typing.

Copyright (c) 2010, A.M. Kuchling
MIT License. Permission is hereby granted to use, copy, modify, and distribute
this software and its documentation for any purpose, provided the above
copyright notice and this permission notice appear in all copies.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = ["knuth_plass_breaks", "knuth_plass_breaks_tex", "knuth_plass_breaks_optimized"]

INFINITY = 1000


class Box:
    """A glyph of fixed width that must remain on a single line.

    Attributes:
        character: Optional payload carried along for downstream use.
        width: Fixed horizontal extent of the box.
    """

    __slots__ = ("character", "width", "stretch", "shrink", "penalty", "flagged")

    def __init__(self, width: float, character=None) -> None:
        self.character = character
        self.width = width
        self.stretch = 0.0
        self.shrink = 0.0
        self.penalty = 0
        self.flagged = 0

    def is_glue(self) -> bool:
        """Whether this item is a Glue."""
        return False

    def is_box(self) -> bool:
        """Whether this item is a Box."""
        return True

    def is_penalty(self) -> bool:
        """Whether this item is a Penalty."""
        return False

    def is_forced_break(self) -> bool:
        """Whether this item forces a line break."""
        return False


class Glue:
    """Elastic space between boxes: preferred width plus stretch/shrink.

    Line breaks may be taken at glue that immediately follows a box.

    Attributes:
        width: Preferred width.
        stretch: How much the glue may grow.
        shrink: How much the glue may contract.
    """

    __slots__ = ("width", "stretch", "shrink")

    def __init__(self, width: float, stretch: float, shrink: float) -> None:
        self.width, self.stretch, self.shrink = width, stretch, shrink

    def is_glue(self) -> bool:
        """Whether this item is a Glue."""
        return True

    def is_box(self) -> bool:
        """Whether this item is a Box."""
        return False

    def is_penalty(self) -> bool:
        """Whether this item is a Penalty."""
        return False

    def is_forced_break(self) -> bool:
        """Whether this item forces a line break."""
        return False


class Penalty:
    """Adjustment applied when a break is taken at this position.

    Positive penalties discourage breaks, negative values encourage them, and
    INFINITY forbids a break while -INFINITY forces one.

    Attributes:
        width: Width contributed to a line when a break is taken here.
        penalty: Desirability of breaking here.
        flagged: Whether this is a "flagged" penalty (breaks at two consecutive
            flagged penalties incur an extra demerit).
    """

    __slots__ = ("width", "penalty", "flagged", "stretch", "shrink")

    def __init__(self, width: float, penalty: int, flagged: int = 0) -> None:
        self.width = width
        self.penalty = penalty
        self.flagged = flagged
        self.stretch = 0.0
        self.shrink = 0.0

    def is_glue(self) -> bool:
        """Whether this item is a Glue."""
        return False

    def is_box(self) -> bool:
        """Whether this item is a Box."""
        return False

    def is_penalty(self) -> bool:
        """Whether this item is a Penalty."""
        return True

    def is_forced_break(self) -> bool:
        """Whether this item forces a line break."""
        return self.penalty == -INFINITY


class _ActiveBreak:
    """One active breakpoint in the line-breaking search.

    Attributes:
        position: Index in the ObjectList where this break occurs.
        line: Number of lines used up to and including this break.
        fitness_class: Tightness class (0=very tight .. 3=very loose).
        totalwidth: Width of all boxes before this position.
        totalstretch: Total stretch of glue before this position.
        totalshrink: Total shrink of glue before this position.
        demerits: Accumulated demerits of the layout ending at this break.
        previous: The active break this one continues from.
    """

    __slots__ = (
        "position",
        "line",
        "fitness_class",
        "totalwidth",
        "totalstretch",
        "totalshrink",
        "demerits",
        "previous",
    )

    def __init__(
        self,
        position: int,
        line: int,
        fitness_class: int,
        totalwidth: float,
        totalstretch: float,
        totalshrink: float,
        demerits: float,
        previous: _ActiveBreak | None = None,
    ) -> None:
        self.position, self.line = position, line
        self.fitness_class = fitness_class
        self.totalwidth, self.totalstretch = totalwidth, totalstretch
        self.totalshrink, self.demerits = totalshrink, demerits
        self.previous = previous


class ObjectList(list):
    """A paragraph: an ordered list of Box, Glue, and Penalty items."""

    def add_closing_penalty(self) -> None:
        """Append the standard end-of-paragraph glue and penalty."""
        self.append(Penalty(0, INFINITY, 0))
        self.append(Glue(0, INFINITY, 0))
        self.append(Penalty(0, -INFINITY, 1))

    def is_feasible_breakpoint(self, position: int) -> bool:
        """Return True if the item at `position` is a feasible breakpoint."""
        box = self[position]
        if box.is_penalty() and box.penalty < INFINITY:
            return True
        if position > 0 and box.is_glue() and self[position - 1].is_box():
            return True
        return False

    def is_forced_break(self, position: int) -> bool:
        """Return True if the item at `position` forces a break."""
        return self[position].is_penalty() and self[position].penalty == -INFINITY

    def measure_width(self, pos1: int, pos2: int) -> float:
        """Total width of boxes between positions pos1 and pos2."""
        return self.sum_width[pos2] - self.sum_width[pos1]

    def measure_stretch(self, pos1: int, pos2: int) -> float:
        """Total stretch of glue between positions pos1 and pos2."""
        return self.sum_stretch[pos2] - self.sum_stretch[pos1]

    def measure_shrink(self, pos1: int, pos2: int) -> float:
        """Total shrink of glue between positions pos1 and pos2."""
        return self.sum_shrink[pos2] - self.sum_shrink[pos1]

    def compute_adjustment_ratio(self, pos1: int, pos2: int, line: int, line_lengths: list[float]) -> float:
        """Adjustment ratio r for the line spanning pos1..pos2.

        Negative means the line must shrink to fit; positive means it stretches;
        0 means it is exactly the right width.
        """
        length = self.measure_width(pos1, pos2)
        if self[pos2].is_penalty():
            length += self[pos2].width

        if line < len(line_lengths):
            available_length = line_lengths[line]
        else:
            available_length = line_lengths[-1]

        if length < available_length:
            stretch = self.measure_stretch(pos1, pos2)
            if stretch > 0:
                return (available_length - length) / stretch
            return INFINITY
        if length > available_length:
            shrink = self.measure_shrink(pos1, pos2)
            if shrink > 0:
                return (available_length - length) / shrink
            return INFINITY
        return 0.0

    def add_active_node(self, active_nodes: list[_ActiveBreak], node: _ActiveBreak) -> None:
        """Insert `node` keeping the list sorted by line and free of duplicates."""
        index = 0
        while index < len(active_nodes) and active_nodes[index].line < node.line:
            index += 1
        insert_index = index

        while index < len(active_nodes) and active_nodes[index].line == node.line:
            if (
                active_nodes[index].fitness_class == node.fitness_class
                and active_nodes[index].position == node.position
            ):
                return
            index += 1

        active_nodes.insert(insert_index, node)

    def compute_breakpoints(
        self,
        line_lengths: list[float],
        looseness: int = 0,
        tolerance: float = 1,
        fitness_demerit: float = 100,
        flagged_demerit: float = 100,
    ) -> list[int]:
        """Compute optimal breakpoint indices for the paragraph.

        Args:
            line_lengths: Per-line available widths; the last element is reused
                for every subsequent line.
            looseness: How many lines more (positive) or fewer (negative) than
                the optimum to aim for.
            tolerance: Maximum adjustment ratio allowed for a line.
            fitness_demerit: Penalty for consecutive lines in distant fitness
                classes (tight next to loose).
            flagged_demerit: Penalty for breaking at two consecutive flagged
                penalties.

        Returns:
            List of ObjectList indices at which to break, starting with 0.
        """
        m = len(self)
        if m == 0:
            return []

        # Per-item numeric values (Knuth's w, y, z, p, f arrays).
        widths = [0] * m
        stretch = [0] * m
        shrink = [0] * m
        penalty = [0] * m
        flagged = [0] * m
        for i in range(m):
            box = self[i]
            widths[i] = box.width
            if box.is_glue():
                stretch[i] = box.stretch
                shrink[i] = box.shrink
            elif box.is_penalty():
                penalty[i] = box.penalty
                flagged[i] = box.flagged

        # Running sums (W, Y, Z in the paper); sum_*[i] excludes item i.
        self.sum_width = {}
        self.sum_stretch = {}
        self.sum_shrink = {}
        width_sum = stretch_sum = shrink_sum = 0.0
        for i in range(m):
            self.sum_width[i] = width_sum
            self.sum_stretch[i] = stretch_sum
            self.sum_shrink[i] = shrink_sum
            box = self[i]
            width_sum += box.width
            stretch_sum += box.stretch
            shrink_sum += box.shrink

        active_nodes: list[_ActiveBreak] = [
            _ActiveBreak(position=0, line=0, fitness_class=1, totalwidth=0, totalstretch=0, totalshrink=0, demerits=0)
        ]

        for i in range(m):
            if not self.is_feasible_breakpoint(i):
                continue

            feasible = []
            for node in active_nodes[:]:
                r = self.compute_adjustment_ratio(node.position, i, node.line, line_lengths)

                if r < -1 or self.is_forced_break(i):
                    if len(active_nodes) > 1:
                        active_nodes.remove(node)

                if -1 <= r <= tolerance:
                    if penalty[i] >= 0:
                        demerits = (1 + 100 * abs(r) ** 3 + penalty[i]) ** 3
                    elif self.is_forced_break(i):
                        demerits = (1 + 100 * abs(r) ** 3) ** 2 - penalty[i] ** 2
                    else:
                        demerits = (1 + 100 * abs(r) ** 3) ** 2

                    demerits += flagged_demerit * flagged[i] * flagged[node.position]

                    if r < -0.5:
                        fitness_class = 0
                    elif r <= 0.5:
                        fitness_class = 1
                    elif r <= 1:
                        fitness_class = 2
                    else:
                        fitness_class = 3

                    if abs(fitness_class - node.fitness_class) > 1:
                        demerits += fitness_demerit

                    feasible.append(
                        _ActiveBreak(
                            position=i,
                            line=node.line + 1,
                            fitness_class=fitness_class,
                            totalwidth=self.sum_width[i],
                            totalstretch=self.sum_stretch[i],
                            totalshrink=self.sum_shrink[i],
                            demerits=demerits,
                            previous=node,
                        )
                    )

            for brk in feasible:
                self.add_active_node(active_nodes, brk)

        # Optimal end node: lowest demerits, optionally adjusted for looseness.
        best_node = min(active_nodes, key=lambda node: node.demerits)

        if looseness != 0:
            # Search for a node whose line count is as close as possible to
            # (best_node.line + looseness), preferring fewer demerits on ties.
            # Matches the reference port exactly (including its original
            # bookkeeping); only reachable when a caller passes looseness != 0.
            best = 0
            best_demerits = INFINITY
            chosen = None
            for brk in active_nodes:
                delta = brk.line - best_node.line
                if (looseness <= delta < best) or (best < delta < looseness):
                    best = delta
                    best_demerits = brk.demerits
                    chosen = brk
                elif delta == best and brk.demerits < best_demerits:
                    best_demerits = brk.demerits
                    chosen = brk
            if chosen is not None:
                best_node = chosen

        breaks = []
        while best_node is not None:
            breaks.append(best_node.position)
            best_node = best_node.previous
        breaks.reverse()
        return breaks


def _paragraph_breaks(
    widths: list[float],
    spacing: float,
    max_width: int,
) -> list[int] | None:
    """Run Knuth-Plass over `widths`, returning breakpoint indices or None.

    Each word becomes a Box; fixed inter-word gaps become Glue with a small
    stretch (so underfull lines stay feasible) and no shrink (so no line ever
    exceeds max_width). The paragraph end is marked with the standard closing
    glue/penalty. Returns None when no complete layout (every word placed)
    exists within max_width.

    Args:
        widths: Width of each word/segment (spaces excluded).
        spacing: Fixed gap between consecutive segments.
        max_width: Maximum allowed width for any line.

    Returns:
        ObjectList indices at which to break, or None if the paragraph cannot
        be fully typeset (e.g. a single word wider than max_width).
    """
    paragraph = ObjectList()
    for i, width in enumerate(widths):
        paragraph.append(Box(width))
        if i < len(widths) - 1:
            # Inter-word glue with a large stretch budget so any line that fits
            # within max_width stays feasible (never collapses to None merely
            # for being short of the target). No shrink: overfull lines are
            # rejected as infeasible, enforcing max_width.
            paragraph.append(Glue(spacing, float(max_width), 0))
    paragraph.add_closing_penalty()

    raw_breaks = paragraph.compute_breakpoints([float(max_width)])
    if not raw_breaks or raw_breaks[-1] != len(paragraph) - 1:
        # The best layout never reached the forced end-of-paragraph break,
        # so some trailing words could not be placed: treat as infeasible.
        return None
    return raw_breaks


def knuth_plass_breaks(
    widths: list[int],
    spacing: int | float,
    max_width: int,
    max_lines: int | None = None,
) -> list[int] | None:
    """Knuth-Plass optimal line breaks: indices where a new line starts.

    Words are placed on the globally minimum-demerit set of lines (closest to
    the target width, penalizing widely-varying line fullness), up to `max_width`.
    Unlike the pyramid solvers, no strict width-descent is enforced.

    Args:
        widths: Width of each word/segment (spaces excluded).
        spacing: Fixed gap between consecutive segments.
        max_width: Maximum allowed width for any line.
        max_lines: Upper bound on the number of lines. None means no bound.
            If the optimal layout needs more lines than this, returns None.

    Returns:
        List of word indices where a new line starts, or None if no layout fits
        within max_width/max_lines.
    """
    n = len(widths)
    if n == 0:
        return []
    if n == 1:
        return None

    raw_breaks = _paragraph_breaks(widths, float(spacing), max_width)
    if raw_breaks is None:
        return None

    # Filter to inter-word glue breakpoints (odd indices in the Box/Glue
    # interleaving) and translate to word-start indices. Drop the leading 0
    # (start of paragraph) and the closing-penalty marker.
    word_breaks = []
    for position in raw_breaks:
        if position % 2 == 1 and position <= 2 * n - 3:
            word_start = (position + 1) // 2
            if 1 <= word_start < n:
                word_breaks.append(word_start)

    if not word_breaks:
        return []
    if max_lines is not None and len(word_breaks) + 1 > max_lines:
        return None
    return word_breaks


_R_INF = 1e9
_TOLERANCE = 1
_FLAGGED_DEMERIT = 100
_FITNESS_DEMERIT = 100
# Safety caps for the faithful TeX active-node search. The pure algorithm's
# active set/scan count grows without bound (worst case quadratic in the word
# count) on wide/long paragraphs; realistic verses stay orders of magnitude
# below these, so exceeding either marks the pathological blow-up band and the
# search aborts (None) so the caller falls back to the optimized solver.
_FAITHFUL_MAX_ACTIVE = 5000
# Total active-node work units allowed before aborting (~140 ms of Python work).
# Composed of raw scans plus each O(active) copy/remove/insert examined. Tuned
# so typical small verses/paragraphs (≤ ~50 words) complete byte-identically
# while longer, blow-up-band inputs abort quickly and fall back to the
# optimized solver.
_FAITHFUL_MAX_SCANS = 6_000_000


def _add_active_dedup(active_nodes: list[_ActiveBreak], node: _ActiveBreak) -> int:
    """Insert `node` keeping active_nodes sorted by line and duplicate-free.

    Returns the number of list elements examined (work cost, for the scan
    budget in `_fast_breakpoints`).
    """
    index = 0
    while index < len(active_nodes) and active_nodes[index].line < node.line:
        index += 1
    insert_index = index

    while index < len(active_nodes) and active_nodes[index].line == node.line:
        if (
            active_nodes[index].fitness_class == node.fitness_class
            and active_nodes[index].position == node.position
        ):
            return index + 1
        index += 1

    active_nodes.insert(insert_index, node)
    return index + 1


def _fast_breakpoints(
    widths: list[int],
    spacing: int | float,
    max_width: int,
) -> list[int] | None:
    """Knuth-Plass main loop over flat token arrays (no Box/Glue objects).

    Semantically identical to ObjectList.compute_breakpoints but represents the
    paragraph as flat lists (kind, width, stretch, shrink, penalty, flagged) and
    precomputes feasibility so the hot loop allocates only active-break nodes.
    This is the micro-optimized companion to the faithful ObjectList path.

    Args:
        widths: Width of each word/segment (spaces excluded).
        spacing: Fixed gap between consecutive segments.
        max_width: Maximum width covered by every line.

    Returns:
        List of ObjectList-style breakpoint indices, or None when no complete
        layout fits within max_width.
    """
    n = len(widths)

    kind = []
    width = []
    stretch = []
    shrink = []
    penalty = []
    flagged = []

    def push(w, y, z, p, f, k) -> None:
        width.append(float(w))
        stretch.append(float(y))
        shrink.append(float(z))
        penalty.append(p)
        flagged.append(f)
        kind.append(k)

    for i in range(n):
        push(widths[i], 0, 0, 0, 0, 0)
        if i < n - 1:
            # Match the ObjectList path: inter-word glue with the full max_width
            # stretch budget (never a short line) and no shrink (hard cap).
            push(float(spacing), float(max_width), 0, 0, 0, 1)
    push(0, 0, 0, INFINITY, 0, 2)         # closing penalty (forbid a break)
    push(0, float(INFINITY), 0, 0, 0, 1)  # final glue, stretch = INFINITY
    push(0, 0, 0, -INFINITY, 1, 2)        # forced end-of-paragraph break

    m = len(kind)

    feasible = [False] * m
    forced = [False] * m
    for i in range(m):
        k = kind[i]
        if k == 2:
            feasible[i] = penalty[i] < INFINITY
            forced[i] = penalty[i] == -INFINITY
        elif i > 0 and k == 1 and kind[i - 1] == 0:
            feasible[i] = True

    prefix_w = [0.0] * (m + 1)
    prefix_s = [0.0] * (m + 1)
    prefix_z = [0.0] * (m + 1)
    for i in range(m):
        prefix_w[i + 1] = prefix_w[i] + width[i]
        prefix_s[i + 1] = prefix_s[i] + stretch[i]
        prefix_z[i + 1] = prefix_z[i] + shrink[i]

    avail = float(max_width)
    active: list[_ActiveBreak] = [_ActiveBreak(0, 0, 1, 0.0, 0.0, 0.0, 0.0, None)]
    scans = 0

    for i in range(m):
        if not feasible[i]:
            continue

        if len(active) > _FAITHFUL_MAX_ACTIVE:
            return None

        forced_i = forced[i]
        pen_i = penalty[i]
        flag_i = flagged[i]

        feasible_breaks: list[_ActiveBreak] = []
        for node in active[:]:
            scans += len(active)
            if scans > _FAITHFUL_MAX_SCANS:
                return None
            pos1 = node.position
            length = prefix_w[i] - prefix_w[pos1]
            if kind[i] == 2:
                length += width[i]

            if length < avail:
                total_stretch = prefix_s[i] - prefix_s[pos1]
                r = (avail - length) / total_stretch if total_stretch > 0 else _R_INF
            elif length > avail:
                total_shrink = prefix_z[i] - prefix_z[pos1]
                r = (avail - length) / total_shrink if total_shrink > 0 else _R_INF
            else:
                r = 0.0

            # A line only grows as i advances, so an overfull node (r > tolerance)
            # can never become feasible again. The original keeps such dead nodes
            # alive and re-scans them every breakpoint, which blows up to O(n^2)
            # active-node accumulation on wide/long paragraphs. Deactivating them
            # never changes the result: an overfull node can never produce a child
            # and never reaches the forced end break, which always carries the
            # lowest (negative) demerits and therefore wins the final selection.
            if r < -1 or forced_i or r > _TOLERANCE:
                if len(active) > 1:
                    active.remove(node)
                    scans += len(active)
                    if scans > _FAITHFUL_MAX_SCANS:
                        return None

            if -1 <= r <= _TOLERANCE:
                if pen_i >= 0:
                    demerits = (1 + 100 * abs(r) ** 3 + pen_i) ** 3
                elif forced_i:
                    demerits = (1 + 100 * abs(r) ** 3) ** 2 - pen_i**2
                else:
                    demerits = (1 + 100 * abs(r) ** 3) ** 2

                demerits += _FLAGGED_DEMERIT * flag_i * flagged[node.position]

                if r < -0.5:
                    fitness_class = 0
                elif r <= 0.5:
                    fitness_class = 1
                elif r <= 1:
                    fitness_class = 2
                else:
                    fitness_class = 3

                if abs(fitness_class - node.fitness_class) > 1:
                    demerits += _FITNESS_DEMERIT

                feasible_breaks.append(
                    _ActiveBreak(
                        i, node.line + 1, fitness_class, prefix_w[i], prefix_s[i], prefix_z[i], demerits, node
                    )
                )

        for brk in feasible_breaks:
            scans += _add_active_dedup(active, brk)
            if scans > _FAITHFUL_MAX_SCANS:
                return None

    if not active:
        return None

    best = min(active, key=lambda nd: nd.demerits)
    breaks = []
    cur = best
    while cur is not None:
        breaks.append(cur.position)
        cur = cur.previous
    breaks.reverse()
    return breaks


def _to_word_breaks(raw_breaks: list[int], n: int) -> list[int]:
    """Translate ObjectList breakpoints to word-start indices."""
    word_breaks = []
    for position in raw_breaks:
        if position % 2 == 1 and position <= 2 * n - 3:
            word_start = (position + 1) // 2
            if 1 <= word_start < n:
                word_breaks.append(word_start)
    return word_breaks


def knuth_plass_breaks_tex(
    widths: list[int],
    spacing: int | float,
    max_width: int,
    max_lines: int | None = None,
) -> list[int] | None:
    """Micro-optimized faithful TeX line breaks: indices where a new line starts.

    Same algorithm, demerit model, and semantics as knuth_plass_breaks() but
    over flat token arrays (no Box/Glue/Penalty objects). Byte-identical to the
    faithful ObjectList port on every tested input, with a bounded active-node
    cap: the pure TeX active set grows quadratically on wide/long paragraphs,
    so when the cap is exceeded the search aborts (returns None) and the caller
    falls back to the optimized solver instead of stalling.

    Args:
        widths: Width of each word/segment (spaces excluded).
        spacing: Fixed gap between consecutive segments.
        max_width: Maximum allowed width for any line.
        max_lines: Upper bound on the number of lines. None means no bound.

    Returns:
        List of word indices where a new line starts, or None if infeasible
        (including the active-node cap being exceeded).
    """
    n = len(widths)
    if n == 0:
        return []
    if n == 1:
        return None

    raw = _fast_breakpoints(widths, float(spacing), max_width)
    if raw is None or not raw or raw[-1] != 2 * n + 1:
        return None

    word_breaks = _to_word_breaks(raw, n)
    if not word_breaks:
        return []
    if max_lines is not None and len(word_breaks) + 1 > max_lines:
        return None
    return word_breaks


def knuth_plass_breaks_optimized(
    widths: list[int],
    spacing: int | float,
    max_width: int,
    max_lines: int | None = None,
) -> list[int] | None:
    """Fastest Knuth-Plass line breaks: indices where a new line starts.

    This is the production solver for the KNUTH_PLASS balancing mode: a guarded
    quadratic-badness dynamic program (line cost = squared slack, free last
    line) that hard-exits the inner loop the moment a candidate line exceeds
    ``max_width`` and caps the search window by the most words that could ever
    fit on a line. Worst case is O(n * window) and in practice near-linear, so
    it can never blow up like the faithful active-node search. It is not
    byte-identical to TeX (the demerit model is the simplified slack² used by
    Chromium's text wrapping) but is deterministic and minimizes line-fullness
    variance, which is what the stable-fallback role requires.

    Args:
        widths: Width of each word/segment (spaces excluded).
        spacing: Fixed gap between consecutive segments.
        max_width: Maximum allowed width for any line.
        max_lines: Upper bound on the number of lines. None means no bound.

    Returns:
        List of word indices where a new line starts, or None if no layout fits
        within max_width/max_lines (e.g. a single word wider than max_width).
    """
    n = len(widths)
    if n == 0:
        return []
    if n == 1:
        return None

    # Coordinate collapse: coord[k] = sum(widths[0..k-1]) + spacing*k, so the
    # width of words[i:j] (j-i-1 inter-word gaps) is coord[j] - coord[i] - spacing
    # in O(1) per candidate without a per-pair multiply.
    coord = [0] * (n + 1)
    for k in range(n):
        coord[k + 1] = coord[k] + widths[k] + spacing

    inf = float("inf")
    cost = [inf] * (n + 1)
    parent = [-1] * (n + 1)
    cost[0] = 0.0

    # A line can never hold more than max_width // (smallest word + gap) + 2
    # words, so the j-window is bounded; the width-exit below makes the bound
    # redundant but turns the constant into a tiny guaranteed cap.
    window = int(max_width // (min(widths) + spacing)) + 2
    if window > n:
        window = n

    for i in range(n):
        ci = cost[i]
        if ci == inf:
            continue
        ci_coord = coord[i]
        limit = i + window
        if limit > n:
            limit = n
        for j in range(i + 1, limit + 1):
            line_width = coord[j] - ci_coord - spacing
            if line_width > max_width:
                break
            slack = max_width - line_width
            add = 0.0 if j == n else float(slack * slack)
            total = ci + add
            if total < cost[j]:
                cost[j] = total
                parent[j] = i

    if parent[n] == -1:
        return None

    breaks: list[int] = []
    j = n
    while j > 0:
        p = parent[j]
        if p > 0:
            breaks.append(p)
        j = p
    breaks.reverse()

    if max_lines is not None and len(breaks) + 1 > max_lines:
        return None
    return breaks
