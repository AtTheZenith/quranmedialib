import os
from src.modules.database_manager import DatabaseManager
from src.workflows.isolate_words import IsolateWordsWorkflow
from src.modules.presets import LANDSCAPE_PRESET


def test_isolate_words():
    print("Starting test_isolate_words...")
    db = DatabaseManager()

    surah = 1
    verse = 2
    words_str = db.get_verse(surah, verse)
    words = words_str.split()
    wbw_translations = db.get_wbw_from_verse(surah, verse)
    # Use WBW translations as the list of strings for the bottom translation area
    translation_list = list(wbw_translations)
    
    db.close()

    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    print(f"Processing Surah {surah}, Verse {verse} ({len(words)} words)...")

    workflow = IsolateWordsWorkflow(layout_config, text_config, word_config)
    
    verse_data = {
        "words": words,
        "surah": surah,
        "ayah": verse,
        "wbw_translations": wbw_translations
    }

    # Call process_verse
    isolation_generator = workflow.process_verse(
        verse_data=verse_data,
        translation_data=translation_list,
        annotate=True
    )

    # Save results
    output_dir = "output/test/isolate_words"
    os.makedirs(output_dir, exist_ok=True)

    # Convert generator to list for explicit testing without loops
    results = list(isolation_generator)
    
    # Verify we have the expected number of items (words + verse number)
    expected_count = len(words) + (1 if verse else 0)
    assert len(results) == expected_count, f"Expected {expected_count} results, got {len(results)}"

    # Explicitly save a selection of results to verify (First, Last)
    # This avoids loops and makes the test's intent clear
    
    # 1. First word ("Al-hamdu")
    save_path_first = os.path.join(output_dir, "first_word.png")
    results[0][0].save(save_path_first)
    print(f"Saved {save_path_first}")

    # 2. Last item (Verse number)
    save_path_last = os.path.join(output_dir, "last_item_verse_num.png")
    results[-1][0].save(save_path_last)
    print(f"Saved {save_path_last}")

    print(f"Test complete. Saved 2/ {len(results)} items to {output_dir}")


if __name__ == "__main__":
    test_isolate_words()
