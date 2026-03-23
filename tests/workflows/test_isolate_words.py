import os

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.workflows.isolate_words import IsolateWordsWorkflow


def save_result(output_dir, file_name, results, index):
    # Explicitly save a selection of results to verify
    # This avoids loops and makes the test's intent clear

    save_path = os.path.join(output_dir, file_name)
    results[index][0].save(save_path)
    print(f"Saved {save_path}")


def test_isolate_words():
    print("Starting test_isolate_words...")
    db = DatabaseManager()

    surah = 1
    verse = 2

    # Get Arabic verse text (always uses "quran" database)
    words_str = db.get_verse(surah, verse)
    words = words_str.split()

    # WBW is automatically fetched from the WBW database
    wbw_translations = db.get_wbw_from_verse(surah, verse)
    # Use WBW translations as the list of strings for the bottom translation area
    translation_list = list(wbw_translations)

    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    print(f"Processing Surah {surah}, Verse {verse} ({len(words)} words)...")

    workflow = IsolateWordsWorkflow(layout_config, text_config, word_config)

    # Call get_iterator with explicit arguments
    isolation_generator = workflow.get_iterator(
        surah=surah,
        verse_words=words,
        translations=translation_list,
        ayah=verse,
        wbw_translations=wbw_translations,
        annotate=True,
    )

    # Save results
    output_dir = "output/test/isolate_words"
    os.makedirs(output_dir, exist_ok=True)

    # Convert generator to list for explicit testing without loops
    results = list(isolation_generator)

    # Verify we have the expected number of items (words + verse number)
    expected_count = len(words) + (1 if verse else 0)
    assert len(results) == expected_count, f"Expected {expected_count} results, got {len(results)}"

    # Save results  (5 items, basically all of them)
    save_result(output_dir, "01.png", results, 0)
    save_result(output_dir, "02.png", results, 1)
    save_result(output_dir, "03.png", results, 2)
    save_result(output_dir, "04.png", results, 3)
    save_result(output_dir, "05.png", results, 4)
    print(f"Test complete. Saved 5/5 items to {output_dir}")


if __name__ == "__main__":
    test_isolate_words()
