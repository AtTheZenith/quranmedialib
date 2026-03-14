import os
from src.modules.database_manager import DatabaseManager
from src.modules.framer import LayoutConfig
from src.workflows.isolate_words import isolate_words


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
    # Wait to close DB until after the workflow if we wanted to be safe,
    # but now we pass translations so we can close it here.
    db.close()

    config = LayoutConfig(
        max_width=1920,
        image_height=1080,
        padding=50,
        word_spacing=20,
        row_spacing=30,
        max_rows_per_page=5,
        bottom_offset=300,
        balanced_wrapping=True,
    )

    print(f"Processing Surah {surah}, Verse {verse} ({len(words)} words)...")

    # Call isolate_words
    isolation_table = isolate_words(verse_words=words, translation=translation_list, surah_number=surah, ayah_number=verse, config=config, annotate=True, wbw_translations=wbw_translations)

    # Save results
    output_dir = "output/test/isolate_words"
    os.makedirs(output_dir, exist_ok=True)

    total_images = 5
    isolation_table[0][0].save(os.path.join(output_dir, "item_1_page_1.png"))
    isolation_table[1][0].save(os.path.join(output_dir, "item_2_page_1.png"))
    isolation_table[2][0].save(os.path.join(output_dir, "item_3_page_1.png"))
    isolation_table[3][0].save(os.path.join(output_dir, "item_4_page_1.png"))
    isolation_table[4][0].save(os.path.join(output_dir, "item_5_page_1.png"))

    print(f"Test complete. Saved {total_images} images to {output_dir}")


if __name__ == "__main__":
    test_isolate_words()
