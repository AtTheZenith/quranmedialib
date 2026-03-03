import os
from src.modules.database_manager import DatabaseManager
from src.modules.wimage import get_wimage
from src.modules.annotate_word import annotate_word
from src.modules.verse_number import verse_number
from src.modules.framer import frame


def test_framer_alignment():
    print("\nRunning test_framer_alignment...")
    database_manager = DatabaseManager()

    # Using a short verse for clear centering visibility (e.g., 108:1)
    surah = 108
    verse = 1
    words_text = database_manager.get_verse(surah, verse).split()
    verse_translation = [database_manager.get_translation_from_verse(surah, verse)]

    print(f"Converting {len(words_text)} words to images...")
    word_images = [get_wimage(word_text) for word_text in words_text]

    print("Annotating words...")
    word_wbw_images = []
    word_wbw_images.extend(annotate_word(word_images[index], surah, verse, index + 1) for index in range(len(word_images)))
    word_wbw_images.append(verse_number(verse, padding=(1, 41, 1, 1), font_size=100))

    output_dir = "./output/test/alignment/"
    os.makedirs(output_dir, exist_ok=True)

    # Test cases for alignment
    alignments = [
        ("default_align", {}, {}),  # Should be center/center
        ("top_right", {"verse_vertical_align": "top", "verse_horizontal_align": "right"}, {}),
        ("center_center_offset", {"verse_v_offset": 50}, {}),
        ("top_center_negative_offset", {"verse_vertical_align": "top", "verse_v_offset": -30}, {}),
    ]

    for name, params, _ in alignments:
        print(f"Testing {name} with params {params}...")
        images = frame(word_wbw_images, words_text, verse_translations=verse_translation, max_rows_per_page=3, **params)
        for i, image in enumerate(images):
            image.save(f"{output_dir}/{name}_{i}.png")

    print("test_framer_alignment completed successfully.")


if __name__ == "__main__":
    try:
        test_framer_alignment()
    finally:
        DatabaseManager().close()
