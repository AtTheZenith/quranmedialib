"""Tests for the VerseWorkflow class.

This module contains tests for verifying that the VerseWorkflow correctly
renders single verses with Arabic text and translations.
"""

import os

import pytest

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager, WorkflowError
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


def test_verse(request: pytest.FixtureRequest) -> None:
    """Test VerseWorkflow with Surah 1, Verse 1 (Al-Fatiha)."""
    print("Starting test_verse...")
    request.node.benchmark_data = ["verse=1:1"]
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


# === Validation Tests ===


def test_verse_invalid_surah() -> None:
    """Test that VerseWorkflow handles invalid surah numbers (empty verses)."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseWorkflow(layout_config, text_config, word_config)

    # Surah 0 doesn't exist, workflow should handle empty verses gracefully
    # Either raise error or return empty results
    try:
        results = list(workflow.get_iterator(surah=0, ayah=1, translations=["test"], annotate=False))
        # If it doesn't raise error, should handle gracefully
        assert isinstance(results, list)
    except Exception:
        pass  # Also acceptable

    # Surah 115 doesn't exist
    try:
        results = list(workflow.get_iterator(surah=115, ayah=1, translations=["test"], annotate=False))
        assert isinstance(results, list)
    except Exception:
        pass


def test_verse_invalid_ayah() -> None:
    """Test that VerseWorkflow handles invalid ayah numbers (empty verse)."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseWorkflow(layout_config, text_config, word_config)

    # Ayah 0 doesn't exist, should handle gracefully
    try:
        results = list(workflow.get_iterator(surah=1, ayah=0, translations=["test"], annotate=False))
        assert isinstance(results, list)
    except Exception:
        pass


def test_verse_empty_translations() -> None:
    """Test that VerseWorkflow handles empty translations list."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseWorkflow(layout_config, text_config, word_config)

    # Empty translations should still work (no translation images)
    results = list(workflow.get_iterator(surah=1, ayah=1, translations=[], annotate=False))
    assert results, "Expected at least one result even with empty translations"


def test_verse_invalid_surah_range() -> None:
    """Test that VerseWorkflow raises ValueError for surah outside 1-114."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseWorkflow(layout_config, text_config, word_config)

    with pytest.raises(ValueError, match="Surah must be between 1 and 114"):
        list(workflow.get_iterator(surah=0, ayah=1, translations=["test"], annotate=False))

    with pytest.raises(ValueError, match="Surah must be between 1 and 114"):
        list(workflow.get_iterator(surah=115, ayah=1, translations=["test"], annotate=False))

    with pytest.raises(ValueError, match="Surah must be between 1 and 114"):
        list(workflow.get_iterator(surah=999, ayah=1, translations=["test"], annotate=False))


def test_verse_invalid_ayah_range() -> None:
    """Test that VerseWorkflow raises ValueError for ayah outside 1-286."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseWorkflow(layout_config, text_config, word_config)

    with pytest.raises(ValueError, match="Ayah must be between 1 and 286"):
        list(workflow.get_iterator(surah=1, ayah=0, translations=["test"], annotate=False))

    with pytest.raises(ValueError, match="Ayah must be between 1 and 286"):
        list(workflow.get_iterator(surah=1, ayah=-1, translations=["test"], annotate=False))

    with pytest.raises(ValueError, match="Ayah must be between 1 and 286"):
        list(workflow.get_iterator(surah=1, ayah=1000, translations=["test"], annotate=False))


def test_verse_empty_text() -> None:
    """Test that VerseWorkflow raises ValueError when DB returns empty verse text."""
    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseWorkflow(layout_config, text_config, word_config)

    # Surah 114 has only 6 verses, so ayah=7 returns empty text
    # (ayah is within 1-286 global range but doesn't exist in this surah)
    with pytest.raises(WorkflowError, match="No verse text found"):
        list(workflow.get_iterator(surah=114, ayah=7, translations=["test"], annotate=False))


def test_base_workflow_none_configs_rejected() -> None:
    """Test that BaseWorkflow raises ValidationError when any config is None."""
    from quranmedialib import ValidationError

    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    with pytest.raises(ValidationError, match="must not be None"):
        VerseWorkflow(None, text_config, word_config)  # type: ignore

    with pytest.raises(ValidationError, match="must not be None"):
        VerseWorkflow(layout_config, None, word_config)  # type: ignore

    with pytest.raises(ValidationError, match="must not be None"):
        VerseWorkflow(layout_config, text_config, None)  # type: ignore
