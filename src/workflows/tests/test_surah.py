import os
import time

from src.modules.database_manager import DatabaseManager
from src.modules.presets import LANDSCAPE_PRESET
from src.workflows.surah import SurahWorkflow


def run_test_scenario(surah_num: int, separate_translations: bool, folder_name: str):
    print(f"\n--- Running Scenario: {folder_name} (Separate: {separate_translations}) ---")
    start_time = time.perf_counter()
    db = DatabaseManager()

    # Verify Surah exists
    arabic_verses = db.get_verses_from_surah(surah_num)

    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    print(f"Processing Surah {surah_num} ({len(arabic_verses)} verses)...")
    workflow = SurahWorkflow(layout_config, text_config, word_config)

    surah_data = {"surah": surah_num}
    # Call get_iterator with the requested flag
    surah_generator = workflow.get_iterator(surah_data=surah_data, annotate=True, separate_translations=separate_translations)

    # Save results
    output_dir = os.path.join("output/test/surah", folder_name)
    os.makedirs(output_dir, exist_ok=True)
    verse_count = 0

    # Process and save each verse as it is yielded
    for i, page_tuples in enumerate(surah_generator):
        # page_tuples is a list[tuple[Image.Image, str]]
        verse_num = i + 1

        # Track page numbers per suffix to handle multi-page Arabic or multi-page translation
        # (Though usually it's page 1a, page 2a... or page 1t, page 2t...)
        suffix_counts = {}

        for img, suffix in page_tuples:
            suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
            page_num = suffix_counts[suffix]

            # Naming Logic:
            # Surah and Verse: 3-digit zero-padded
            # Combined mode: surah_002_verse_001_page_1.png
            # Separate mode: surah_002_verse_001_page_1a.png / 1t.png
            s_str = f"{surah_num:03d}"
            v_str = f"{verse_num:03d}"

            if separate_translations and suffix == "a" or not separate_translations:
                filename = f"surah_{s_str}_verse_{v_str}_page_{page_num}.png"
            else:
                filename = f"surah_{s_str}_verse_{v_str}_page_{suffix}.png"
            save_path = os.path.join(output_dir, filename)
            img.save(save_path)
            # print(f"Saved {save_path}") # Optional: can be noisy for 286 verses

        verse_count += 1
        if verse_count % 50 == 0:
            print(f"  Processed {verse_count} verses...")

    # Verify we have the expected number of verses
    assert verse_count == len(arabic_verses), f"Expected {len(arabic_verses)} results, got {verse_count}"

    elapsed_time = time.perf_counter() - start_time
    print(f"Scenario '{folder_name}' complete. Saved images for {verse_count} verses. Elapsed: {elapsed_time:.2f}s")


def test_surah_stress():
    print("Starting Stress Test for Surah Workflow...")
    surah_num = 2  # Al-Baqarah

    # 1. Combined translations
    run_test_scenario(surah_num, separate_translations=False, folder_name="combined")

    # 2. Separate translations
    run_test_scenario(surah_num, separate_translations=True, folder_name="separate")


if __name__ == "__main__":
    test_surah_stress()
