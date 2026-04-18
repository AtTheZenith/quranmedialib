"""Performance benchmarks for QuranMediaLib rendering workflows.

These tests establish a 'Contractual Benchmark' for core rendering tasks.
They are marked with @pytest.mark.benchmark and skipped by default
unless specifically requested via --run-benchmarks.
"""

import time

import pytest

from quranmedialib import LANDSCAPE_PRESET, SurahWorkflow


@pytest.mark.benchmark
def test_full_surah_fatiha_benchmark() -> None:
    """Contractual Benchmark: Render Surah Al-Fatiha (1:1-7).

    Target: Should be extremely fast on any modern system.
    Note: We set a generous 10s limit to avoid false positives on very weak systems,
    but real-world expectation is < 1s.
    """
    layout, text, word = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = SurahWorkflow(layout, text, word)

    start_time = time.perf_counter()
    # Execute full surah processing
    results = list(workflow.get_iterator(surah=1))
    elapsed = time.perf_counter() - start_time

    assert len(results) == 7
    print(f"\nSurah Al-Fatiha benchmark: {elapsed:.4f}s")

    # Contractual limit
    assert elapsed < 10.0


@pytest.mark.benchmark
def test_high_res_render_performance_ratio(request: pytest.FixtureRequest) -> None:
    """Verify that 2160p (4K) rendering doesn't cause exponential slowdown.

    This monitors the performance scaling between 1080p and 2160p.
    """

    def run_benchmark(res):
        layout, text, word = LANDSCAPE_PRESET["default"][res]
        workflow = SurahWorkflow(layout, text, word)
        start = time.perf_counter()
        list(workflow.get_iterator(surah=108))  # Al-Kawthar (3 verses)
        return time.perf_counter() - start

    t_1080 = run_benchmark("1080p")
    t_2160 = run_benchmark("2160p")

    ratio = t_2160 / t_1080 if t_1080 > 0 else 1
    # Attach data to the test node for auto-formatting in conftest.py
    request.node.benchmark_data = [f"{ratio:.2f}x"]
    print(f"\nScaling Ratio (2160p/1080p): {ratio:.2f}x")

    # We expect some slowdown but it should be linear relative to pixel count
    # 4K has 4x more pixels, so a 5-6x time multiplier is a safe contract limit.
    assert ratio < 8.0
