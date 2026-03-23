"""Tests for the VerseWorkflow class.

This module contains tests for verifying that the VerseWorkflow correctly
renders single verses with Arabic text and translations.
"""

import os

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.workflows.verse import VerseWorkflow


def _save_result(output_dir: str, file_name: str, results: list, index: int) -> None:
    """Save a single result image to the output directory.

    Args:
        output_dir: Directory path to save the image.
        file_name: Filename for the saved image.
        results: List of result pages from the workflow.
        index: Index of the result to save.
    """
    save_path = os.path.join(output_dir, file_name)
    results[index][0].save(save_path)
    print(f"Saved {save_path}")


def test_verse() -> None:
    """Test VerseWorkflow with Surah 1, Verse 1 (Al-Fatiha)."""
    print("Starting test_verse...")
    db = DatabaseManager()

    surah = 1
    ayah = 1

    translations = [db.get_translation_from_verse(surah_number=surah, ayah_number=ayah)]

    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    print(f"Processing Surah {surah}, Ayah {ayah}...")

    workflow = VerseWorkflow(layout_config, text_config, word_config)

    # Call get_iterator
    verse_generator = workflow.get_iterator(
        surah=surah,
        ayah=ayah,
        translations=translations,
        annotate=True,
    )

    # Output directory
    output_dir = "output/test/verse"
    os.makedirs(output_dir, exist_ok=True)

    # Convert generator to list for explicit testing
    results = list(verse_generator)

    # Verify we have at least one result
    assert results, f"Expected at least 1 result, got {len(results)}"

    # Save first page to verify output
    if results:
        _save_result(output_dir, "01_page_1.png", results, 0)
        print(f"Test complete. Saved first page to {output_dir}")


def test_verse_without_annotation() -> None:
    """Test VerseWorkflow without word annotation."""
    print("Starting test_verse_without_annotation...")
    db = DatabaseManager()

    surah = 108
    ayah = 1

    translations = [db.get_translation_from_verse(surah_number=surah, ayah_number=ayah)]

    layout_config, text_config = LANDSCAPE_PRESET["default"]["1080p"][:2]
    word_config = LANDSCAPE_PRESET["arabic"]["1080p"][2]

    print(f"Processing Surah {surah}, Ayah {ayah} (without annotation)...")

    workflow = VerseWorkflow(layout_config, text_config, word_config)

    # Call get_iterator without annotation
    verse_generator = workflow.get_iterator(
        surah=surah,
        ayah=ayah,
        translations=translations,
        annotate=False,
    )

    # Output directory
    output_dir = "output/test/verse"
    os.makedirs(output_dir, exist_ok=True)

    # Convert generator to list for explicit testing
    results = list(verse_generator)

    # Verify we have at least one result
    assert results, f"Expected at least 1 result, got {len(results)}"

    # Save first page to verify output
    if results:
        _save_result(output_dir, "02_no_annotation.png", results, 0)
        print(f"Test complete. Saved first page to {output_dir}")


if __name__ == "__main__":
    test_verse()
    test_verse_without_annotation()
    print("All verse workflow tests completed.")
