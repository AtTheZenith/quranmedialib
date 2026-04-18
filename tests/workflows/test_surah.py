"""Tests for the SurahWorkflow class.

This module contains tests for verifying the surah-level workflow that processes
entire surahs with Arabic text and translations, including benchmarking with
large surahs (e.g., Al-Baqarah with 286 verses).
"""

import os
import time
import warnings

import pytest

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.utils.memory import MemoryMonitor
from quranmedialib.workflows.surah import SurahWorkflow


def run_test_scenario(surah_num: int, separate_translations: bool, folder_name: str) -> None:
    print(f"\n--- Running Scenario: {folder_name} (Separate: {separate_translations}) ---")
    start_time = time.perf_counter()
    db = DatabaseManager()

    # Verify Surah exists
    arabic_verses = db.get_verses_from_surah(surah_num)

    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    print(f"Processing Surah {surah_num} ({len(arabic_verses)} verses)...")
    workflow = SurahWorkflow(layout_config, text_config, word_config)

    # Save results
    output_dir = os.path.join("output/test/surah", folder_name)
    os.makedirs(output_dir, exist_ok=True)

    # Genius: Pass output_dir to get_iterator to enable parallel I/O (bypass serial overhead)
    surah_generator = workflow.get_iterator(
        surah=surah_num,
        annotate=True,
        separate_translations=separate_translations,
        output_dir=output_dir,
        filename_prefix=f"surah_{surah_num:03d}",
    )

    # Process results (which are now paths)
    verse_count = 0
    for i, paths in enumerate(surah_generator):
        verse_count += 1
        if verse_count % 50 == 0:
            print(f"  Processed {verse_count} verses...")

    # Verify we have the expected number of verses
    assert verse_count == len(arabic_verses), f"Expected {len(arabic_verses)} results, got {verse_count}"

    elapsed_time = time.perf_counter() - start_time
    print(f"Scenario '{folder_name}' complete. Saved images for {verse_count} verses. Elapsed: {elapsed_time:.2f}s")


def test_surah_standard(request: pytest.FixtureRequest) -> None:
    """Lightweight surah rendering check (Surah 100 - Al-Adiyat, 11 verses)."""
    print("Starting Standard Test for Surah Workflow (Surah 100)...")
    surah_num = 100  # Al-Adiyat
    run_test_scenario(surah_num, separate_translations=False, folder_name="standard")
    request.node.benchmark_data = ["verse_count=11"]


@pytest.mark.benchmark
def test_surah_al_baqarah_benchmark(request: pytest.FixtureRequest) -> None:
    """Heavy benchmark for the entire Surah Al-Baqarah (286 verses) - Worst Case Scenario."""

    print("Starting Al-Baqarah Worst-Case Benchmark (Surah 2)...")
    surah_num = 2  # Al-Baqarah

    # Use MemoryMonitor to capture the true aggregate peak of all hardware-parallel workers
    with MemoryMonitor(limit_mb=2048.0) as monitor:
        run_test_scenario(surah_num, separate_translations=False, folder_name="bulk_al_baqarah")
        peak_mb = monitor.peak_rss

    request.node.benchmark_data = [f"Peak Aggregate RAM: {peak_mb:.2f}MB"]
    print(f"Memory Footprint (Al-Baqarah): Peak Aggregate RAM={peak_mb:.2f}MB")

    # Contract: Aggregate RAM (Main + N Workers) should stay within 1.6GB for this 1080p workload.
    # Note: 8 workers * ~180MB each = ~1.4GB + Main Process (~50MB) = ~1.5GB.
    assert peak_mb < 1600.0


if __name__ == "__main__":
    test_surah_al_baqarah_benchmark()


def test_surah_invalid_surah_number() -> None:
    """Test that SurahWorkflow raises error for invalid surah numbers (0 and 115)."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = SurahWorkflow(layout_config, text_config, word_config)

    for invalid_surah in [0, 115]:
        with pytest.raises(ValueError, match=f"Surah must be between 1 and 114, got {invalid_surah}"):
            list(workflow.get_iterator(surah=invalid_surah))


def test_surah_no_verses_found() -> None:
    """Test that SurahWorkflow raises ValueError for surah outside valid range."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = SurahWorkflow(layout_config, text_config, word_config)

    # Surah 0 is out of valid range — caught by surah validation before DB lookup
    with pytest.raises(ValueError, match="Surah must be between 1 and 114"):
        list(workflow.get_iterator(surah=0))


def test_surah_empty_translations() -> None:
    """Test that SurahWorkflow works with empty translations for a short surah (surah 108)."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = SurahWorkflow(layout_config, text_config, word_config)

    # Surah 108 (Al-Kawthar) has 3 verses
    db = DatabaseManager()
    arabic_verses = db.get_verses_from_surah(108)
    assert len(arabic_verses) == 3, f"Expected 3 verses for Surah 108, got {len(arabic_verses)}"

    results = list(workflow.get_iterator(surah=108))
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"

    # Verify each result is a non-empty list of images
    for i, pages in enumerate(results):
        assert isinstance(pages, list), f"Verse {i + 1}: Expected list, got {type(pages)}"
        assert len(pages) > 0, f"Verse {i + 1}: Expected at least one page"


def test_surah_invalid_surah_range() -> None:
    """Test that SurahWorkflow raises ValueError for surah outside 1-114."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = SurahWorkflow(layout_config, text_config, word_config)

    with pytest.raises(ValueError, match="Surah must be between 1 and 114"):
        list(workflow.get_iterator(surah=0))

    with pytest.raises(ValueError, match="Surah must be between 1 and 114"):
        list(workflow.get_iterator(surah=115))


def test_surah_unrecognized_kwargs_warns() -> None:
    """Test that SurahWorkflow warns on unrecognized kwargs."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = SurahWorkflow(layout_config, text_config, word_config)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # Pass an unrecognized kwarg (typo)
        results = list(workflow.get_iterator(surah=108, annota=True))  # type: ignore — intentional typo

        # Should have warned about unrecognized kwarg
        assert any("Unknown kwargs" in str(warning.message) for warning in w)
        assert len(results) == 3  # Surah 108 has 3 verses
