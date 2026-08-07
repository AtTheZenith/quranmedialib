import logging

import pytest

from quranmedialib.modules.text_layout import (
    StyledWord,
    _text_preview,
    balance_lines_pyramid,
    wrap_rich_text_balanced,
)
from quranmedialib.types import BalancingMode


def create_mock_word(text: str, width: float, height: int = 50, ascent: int = 30) -> StyledWord:
    """Create a StyledWord with a specific width for layout testing."""
    # Use a dummy font object with a mock getlength if needed,
    # but StyledWord takes width as an argument.
    return StyledWord(
        text=text,
        font=None,  # type: ignore
        color=(255, 255, 255, 255),
        width=width,
        height=height,
        ascent=ascent,
    )


def test_balance_lines_empty():
    """Test wrapping an empty list of words."""
    assert wrap_rich_text_balanced([], 1000) == []


def test_balance_lines_single_oversized_word():
    """Test a single word that exceeds the max_width."""
    words = [create_mock_word("LongWord", 1200)]
    lines = wrap_rich_text_balanced(words, 1000)
    assert len(lines) == 1
    assert len(lines[0].words) == 1


def test_balance_lines_perfect_fit():
    """Test words that fit exactly into the max_width."""
    # 3 words of 300px = 900px
    words = [create_mock_word("W1", 300), create_mock_word("W2", 300), create_mock_word("W3", 300)]
    lines = wrap_rich_text_balanced(words, 900)
    assert len(lines) == 1
    assert len(lines[0].words) == 3


def test_balance_lines_extreme_width():
    """Test extremely large max_width."""
    words = [create_mock_word(f"W{i}", 100) for i in range(10)]
    lines = wrap_rich_text_balanced(words, 10000)
    assert len(lines) == 1
    assert len(lines[0].words) == 10


def test_balance_lines_minimum_width():
    """Test extremely small max_width."""
    words = [create_mock_word(f"W{i}", 100) for i in range(5)]
    lines = wrap_rich_text_balanced(words, 50)  # Every word is 100, max is 50
    assert len(lines) == 5
    for line in lines:
        assert len(line.words) == 1


def test_balance_lines_pyramid_shape():
    """Test the inverted pyramid balancing logic."""
    # words: [100, 100, 100, 100, 100]
    # max_width: 300
    words = [create_mock_word(f"W{i}", 100) for i in range(5)]
    lines = wrap_rich_text_balanced(words, 300)

    assert len(lines) == 2
    assert len(lines[0].words) == 3
    assert len(lines[1].words) == 2


def test_balance_lines_large_fonts():
    """Test words with extremely large widths."""
    words = [create_mock_word("Giant", 5000), create_mock_word("Tiny", 10)]
    lines = wrap_rich_text_balanced(words, 1000)
    assert len(lines) == 2
    assert lines[0].words[0].width == 5000


def _assert_feasible(lines, max_width, space_width=0.0):
    """Every produced line must fit within max_width."""
    for line in lines:
        assert line.width <= max_width


def test_balance_lines_knuth_plass_mode():
    """KNUTH_PLASS dispatch produces the same inverted pyramid as SMOOTH."""
    words = [create_mock_word(f"W{i}", 100) for i in range(5)]
    smooth_lines = wrap_rich_text_balanced(words, 300)
    kp_lines = wrap_rich_text_balanced(words, 300, mode=BalancingMode.KNUTH_PLASS)
    assert len(kp_lines) == len(smooth_lines) == 2
    assert [len(line.words) for line in kp_lines] == [3, 2]


def test_balance_lines_all_modes_feasible():
    """Every balancing mode produces width-feasible lines for the same input."""
    words = [create_mock_word(f"W{i}", 100) for i in range(10)]
    for mode in BalancingMode:
        lines = wrap_rich_text_balanced(words, 300, mode=mode)
        _assert_feasible(lines, 300)
        assert lines


def test_balance_lines_mode_string_coercion():
    """wrap_rich_text_balanced accepts lowercase string mode names."""
    words = [create_mock_word(f"W{i}", 100) for i in range(5)]
    lines = wrap_rich_text_balanced(words, 300, mode="knuth_plass")
    assert len(lines) == 2


def test_balance_lines_tex_matches_smooth_on_small_input():
    """TEX and SMOOTH agree on a small deterministic input."""
    words = [create_mock_word(f"W{i}", 100) for i in range(5)]
    tex_lines = wrap_rich_text_balanced(words, 300, mode=BalancingMode.TEX)
    smooth_lines = wrap_rich_text_balanced(words, 300, mode=BalancingMode.SMOOTH)
    assert [len(line.words) for line in tex_lines] == [len(line.words) for line in smooth_lines] == [3, 2]


def test_balance_lines_tex_budget_abort_falls_back():
    """A large input that trips the TeX work budget falls back to a feasible layout."""
    words = [create_mock_word(f"W{i}", 100) for i in range(120)]
    lines = wrap_rich_text_balanced(words, 300, mode=BalancingMode.TEX)
    _assert_feasible(lines, 300)
    assert len(lines) > 0


def test_balance_lines_forward_mode():
    """FORWARD mode still fits within the width budget."""
    words = [create_mock_word(f"W{i}", 100) for i in range(10)]
    lines = wrap_rich_text_balanced(words, 300, mode=BalancingMode.FORWARD)
    _assert_feasible(lines, 300)
    # Single-pass fill: 3 words per line up to the 300px budget.
    assert [len(line.words) for line in lines] == [3, 3, 3, 1]


def test_greedy_single_oversized_word():
    """A single word wider than the budget stays on one line (graceful)."""
    words = [create_mock_word("HUGE", 500)]
    lines = wrap_rich_text_balanced(words, 100, mode=BalancingMode.KNUTH_PLASS)
    assert len(lines) == 1
    assert len(lines[0].words) == 1


def test_greedy_oversized_word_own_line():
    """An overlong word gets its own line, neighbors pack normally."""
    words = [
        create_mock_word("a", 50),
        create_mock_word("HUGE", 400),
        create_mock_word("b", 50),
        create_mock_word("c", 50),
    ]
    lines = wrap_rich_text_balanced(words, 100, mode=BalancingMode.FORWARD)
    assert [len(line.words) for line in lines] == [1, 1, 2]
    assert lines[1].words[0].width == 400


def test_greedy_empty_and_unbounded():
    """Empty input and a None width budget yield graceful results."""
    assert wrap_rich_text_balanced([], 300) == []
    words = [create_mock_word(f"W{i}", 100) for i in range(5)]
    lines = wrap_rich_text_balanced(words, None)
    assert len(lines) == 1
    assert len(lines[0].words) == 5


def test_greedy_fallback_signal_direct():
    """balance_lines_pyramid falls back to greedy directly for all solvers."""
    widths = [100] * 120
    for mode in (BalancingMode.SMOOTH, BalancingMode.KNUTH_PLASS, BalancingMode.TEX):
        breaks = balance_lines_pyramid(widths, 0, 40, 300, mode=mode)
        assert breaks is not None
        _assert_feasible_breaks(breaks, [100] * 120, 300)


def _assert_feasible_breaks(breaks, widths, max_width):
    """Break indices must split words into lines that each fit max_width."""
    starts = [0] + list(breaks)
    ends = list(breaks) + [len(widths)]
    for a, b in zip(starts, ends):
        assert sum(widths[a:b]) <= max_width


def test_greedy_fallback_benign_logged_at_debug(caplog):
    """A feasible primary-impossible fallback is logged (DEBUG), naming it."""
    words = [create_mock_word(f"W{i}", 100) for i in range(120)]
    with caplog.at_level(logging.DEBUG, logger="quranmedialib.modules.text_layout"):
        wrap_rich_text_balanced(words, 150, mode=BalancingMode.TEX)
    assert any(
        "impossible constraints for 'tex'" in r.message and r.levelno == logging.DEBUG
        for r in caplog.records
    )


def test_text_preview_truncation():
    """Full text up to 100 chars; longer text shows an ellipsis and a marker."""
    assert _text_preview(None) == ""
    assert _text_preview("") == ""
    short = "a" * 50
    assert _text_preview(short) == f' text="{short}"'
    assert "..." not in _text_preview(short)
    long = "a" * 150
    preview = _text_preview(long)
    assert "..." in preview
    assert preview.endswith('(truncated)"')


def test_greedy_fallback_warning_includes_text_preview(caplog):
    """Fallback warnings name the first 20 chars of the unsatisfiable text."""
    words = [create_mock_word(f"W{i}", 100) for i in range(120)]
    with caplog.at_level(logging.DEBUG, logger="quranmedialib.modules.text_layout"):
        wrap_rich_text_balanced(words, 150, mode=BalancingMode.TEX)
    assert any('text="W0 W1 W2 W3 W4 W5' in r.message for r in caplog.records)


def test_greedy_fallback_word_too_long_warns(caplog):
    """Greedy fallback due to an over-long word logs a WARNING naming it."""
    words = [create_mock_word(f"W{i}", 100) for i in range(3)] + [create_mock_word("HUGE", 900)]
    with caplog.at_level(logging.WARNING, logger="quranmedialib.modules.text_layout"):
        wrap_rich_text_balanced(words, 300, mode=BalancingMode.KNUTH_PLASS)
    assert any("word too long" in r.message and r.levelno == logging.WARNING for r in caplog.records)
    assert any("text=" in r.message for r in caplog.records)


def test_impossible_constraints_warns_greedy(caplog):
    """A budget greedy cannot meet warns it is impossible for the fallback."""
    widths = [100] * 6
    # max 100 forces one word per line; a 2-line budget is unsatisfiable by any.
    with caplog.at_level(logging.WARNING, logger="quranmedialib.modules.text_layout"):
        breaks = balance_lines_pyramid(widths, 0, 2, 100, mode=BalancingMode.TEX)
    assert breaks is None
    assert any(
        "impossible constraints for the greedy fallback" in r.message
        and r.levelno == logging.WARNING
        for r in caplog.records
    )


@pytest.mark.benchmark
def test_balance_solver_regression_benchmark(request: pytest.FixtureRequest) -> None:
    """Benchmark greedy vs SMOOTH pyramid and gate on regression-free cost.

    Greedy (FORWARD) is a single-pass O(n) max-fill; SMOOTH is a quadratic DP
    capped at PYRAMID_MAX_WORDS (256). Timings are recorded and guarded with
    generous absolute and relative-scaling bounds so an order-of-magnitude cost
    regression in either path fails loudly, while staying robust to machine speed.
    """
    import time

    def widths(n: int) -> list[int]:
        # Deterministic distinct widths so the pyramid descent never collapses
        # to a single line and the DP actually does work.
        return [(i * 37) % 90 + 10 for i in range(n)]

    def run(mode: BalancingMode, n: int) -> float:
        w = widths(n)
        start = time.perf_counter()
        for _ in range(5):
            balance_lines_pyramid(w, 8, 0, 600, mode=mode)
        return (time.perf_counter() - start) / 5

    greedy_small = run(BalancingMode.FORWARD, 2048)
    greedy_large = run(BalancingMode.FORWARD, 8192)
    smooth_128 = run(BalancingMode.SMOOTH, 128)
    smooth_256 = run(BalancingMode.SMOOTH, 256)

    # Greedy is linear: 4x the words must stay well under 8x the time.
    assert greedy_large < 8 * greedy_small + 1e-6
    # SMOOTH is ~quadratic in n: 2x the words must stay under 8x the time.
    assert smooth_256 < 8 * smooth_128 + 1e-6
    # GENEROUS absolute ceilings only trip on pathological regressions.
    assert greedy_large < 1.0
    assert smooth_256 < 5.0

    request.node.benchmark_data = [
        f"greedy_2048={greedy_small * 1000:.2f}ms",
        f"greedy_8192={greedy_large * 1000:.2f}ms",
        f"smooth_128={smooth_128 * 1000:.2f}ms",
        f"smooth_256={smooth_256 * 1000:.2f}ms",
    ]

    print("\nLayout balance solver regression benchmark:")
    print(f"  FORWARD greedy 2048w: {greedy_small * 1000:.2f}ms")
    print(f"  FORWARD greedy 8192w: {greedy_large * 1000:.2f}ms")
    print(f"  SMOOTH pyramid 128w: {smooth_128 * 1000:.2f}ms")
    print(f"  SMOOTH pyramid 256w: {smooth_256 * 1000:.2f}ms")
