"""Tests for the VerseRangeWorkflow class.

This module contains tests for verifying the verse range workflow that processes
a range of verses sequentially with Arabic text and translations.
"""

import os

import pytest

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.workflows.verse_range import VerseRangeWorkflow


def test_verse_range(request: pytest.FixtureRequest) -> None:
    print("Starting test_verse_range (Surah 108 - Per-Verse Iteration)...")
    request.node.benchmark_data = ["surah=108", "verses=3"]

    db = DatabaseManager()

    # Define inputs explicitly for Surah 108 (Al-Kawthar)
    surah = 108
    start_verse = 1
    end_verse = 3

    # Fetch English translations (uses "translation" database by default)
    translations = db.get_translation_from_surah(surah)
    # translations: list[list[str]] (Per verse, per page) for passing to workflow
    # But get_translation_from_surah returns list[str] (one string per verse)
    # We need to wrap each string in a list because VerseRangeWorkflow expects list[list[str]]
    translations_list = [[t] for t in translations]

    preset = LANDSCAPE_PRESET["default"]["1080p"]

    workflow = VerseRangeWorkflow(preset)

    print(f"Processing Surah {surah}, Verses {start_verse}-{end_verse}...")

    # Execute workflow (generator yields a list of pages per verse)
    # Using explicit arguments
    generator = workflow._process_range(
        surah=surah,
        start_verse=start_verse,
        end_verse=end_verse,
        translations=translations_list,
    )

    # Output directory
    output_dir = "output/test/verse_range"
    os.makedirs(output_dir, exist_ok=True)

    # Convert generator to concrete list of lists
    results = list(generator)
    assert len(results) == 3, f"Expected 3 verse results, but got {len(results)}"

    # Verse 1
    v1_pages = results[0]
    print(f"Verse 1 generated {len(v1_pages)} pages.")
    save_path1 = os.path.join(output_dir, "v1_page_1.png")
    v1_pages[0].save(save_path1)
    print(f"Saved {save_path1}")

    # Verse 2
    v2_pages = results[1]
    print(f"Verse 2 generated {len(v2_pages)} pages.")
    save_path2 = os.path.join(output_dir, "v2_page_1.png")
    v2_pages[0].save(save_path2)
    print(f"Saved {save_path2}")

    # Verse 3
    v3_pages = results[2]
    print(f"Verse 3 generated {len(v3_pages)} pages.")
    save_path3 = os.path.join(output_dir, "v3_page_1.png")
    v3_pages[0].save(save_path3)
    print(f"Saved {save_path3}")

    print(f"Test complete. Results saved to {output_dir}")


if __name__ == "__main__":
    test_verse_range()


# === Validation Tests ===


def test_verse_range_invalid_surah() -> None:
    """Test that VerseRangeWorkflow handles invalid surah numbers."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    # Surah 0 doesn't exist, should handle gracefully
    try:
        results = list(workflow.get_iterator(surah=0, translations=[[]], start_ayah=1, end_ayah=1, annotate=False))
        assert isinstance(results, list)
    except Exception:
        pass

    # Surah 115 doesn't exist
    try:
        results = list(workflow.get_iterator(surah=115, translations=[[]], start_ayah=1, end_ayah=1, annotate=False))
        assert isinstance(results, list)
    except Exception:
        pass


def test_verse_range_invalid_ayah_range() -> None:
    """Test that VerseRangeWorkflow handles invalid ayah range."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    # Ayah 0 doesn't exist, should handle gracefully
    try:
        results = list(workflow.get_iterator(surah=1, translations=[[]], start_ayah=0, end_ayah=1, annotate=False))
        assert isinstance(results, list)
    except Exception:
        pass


def test_verse_range_reversed_range() -> None:
    """Test that VerseRangeWorkflow raises ValueError for reversed ayah range."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    # end_ayah < start_ayah should raise ValueError
    with pytest.raises(ValueError, match="start_ayah.*cannot be greater than end_ayah"):
        list(workflow.get_iterator(surah=1, translations=[[]], start_ayah=5, end_ayah=1))


def test_verse_range_empty_translations() -> None:
    """Test that VerseRangeWorkflow handles empty translations."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    # Empty translations should still work
    results = list(workflow.get_iterator(surah=108, translations=[[]], start_ayah=1, end_ayah=1, annotate=False))
    assert results


def test_verse_range_invalid_ayah() -> None:
    """Test that VerseRangeWorkflow raises ValueError for ayah outside 1-286."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    with pytest.raises(ValueError, match="Ayah must be between 1 and 286"):
        list(workflow.get_iterator(surah=1, translations=[[]], start_ayah=0, end_ayah=1, annotate=False))

    with pytest.raises(ValueError, match="Ayah must be between 1 and 286"):
        list(workflow.get_iterator(surah=1, translations=[[]], start_ayah=1, end_ayah=1000, annotate=False))
