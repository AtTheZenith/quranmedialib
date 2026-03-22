import os

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.workflows.verse_range import VerseRangeWorkflow


def test_verse_range():
    print("Starting test_verse_range (Surah 108 - Per-Verse Iteration)...")

    db = DatabaseManager()

    # Define inputs explicitly for Surah 108 (Al-Kawthar)

    surah = 108

    start_verse = 1

    end_verse = 3

    # Fetch English translations (uses "translation" database by default)
    translations = db.get_translation_from_surah(surah)

    # Argument order: (start, end, translations)

    # translations: list[list[str]] (Per verse, per page)

    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    workflow = VerseRangeWorkflow(layout_config, text_config, word_config)

    print(f"Processing Surah {surah}, Verses {start_verse}-{end_verse}...")

    # Execute workflow (generator yields a list of pages per verse)
    generator = workflow._process_range(
        surah=surah,
        start_verse=start_verse,
        end_verse=end_verse,
        translations=translations,
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
    v1_pages[0][0].save(save_path1)
    print(f"Saved {save_path1}")

    # Verse 2
    v2_pages = results[1]
    print(f"Verse 2 generated {len(v2_pages)} pages.")
    save_path2 = os.path.join(output_dir, "v2_page_1.png")
    v2_pages[0][0].save(save_path2)
    print(f"Saved {save_path2}")

    # Verse 3
    v3_pages = results[2]
    print(f"Verse 3 generated {len(v3_pages)} pages.")
    save_path3 = os.path.join(output_dir, "v3_page_1.png")
    v3_pages[0][0].save(save_path3)
    print(f"Saved {save_path3}")

    print(f"Test complete. Results saved to {output_dir}")


if __name__ == "__main__":
    test_verse_range()
