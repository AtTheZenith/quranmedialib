import os

from src.modules.annotate_word import annotate_word
from src.modules.database_manager import DatabaseManager
from src.modules.framer import frame
from src.modules.verse_number import verse_number
from src.modules.wimage import get_wimage


def test_framer():
    print("\nRunning test_framer...")
    database_manager = DatabaseManager()

    # Using Ayatul Kursi (2:255) for test
    surah = 2
    verse = 255
    words_text = database_manager.get_verse(surah, verse).split()
    verse_translation = database_manager.get_translation_from_verse(surah, verse)

    # Split up the translation
    split_index = verse_translation.find("on the earth.") + len("on the earth.") + 1
    verse_translation = [verse_translation[:split_index], verse_translation[split_index:]]
    split_index = verse_translation[1].find("after them,") + len("after them,") + 1
    verse_translation = [verse_translation[0], verse_translation[1][:split_index], verse_translation[1][split_index:]]
    split_index = verse_translation[2].find("tires Him not.") + len("tires Him not.") + 1
    verse_translation = [verse_translation[0], verse_translation[1], verse_translation[2][:split_index], verse_translation[2][split_index:]]

    print(f"Converting {len(words_text)} words to images...")
    word_images = [get_wimage(word_text) for word_text in words_text]

    print("Annotating words with translations...")
    word_wbw_images = []
    word_wbw_images.extend(annotate_word(word_images[index], surah, verse, index + 1) for index in range(len(word_images)))

    print("Arranging words into verses with translation...")
    word_wbw_images.append(verse_number(verse, padding=(1, 41, 1, 1), font_size=100))

    # We pass the translation as a list of strings, one for each verse segment
    images = frame(word_wbw_images, words_text, verse_translations=verse_translation)

    output_dir = "./output/test/"
    os.makedirs(output_dir, exist_ok=True)

    # Why is this cleaner (yes slower but whatever)
    [image.save(f"{output_dir}/framer_{i}.png") for i, image in enumerate(images)]

    print("test_framer completed successfully.")


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

    output_dir = "./output/test"
    os.makedirs(output_dir, exist_ok=True)

    # Test cases for alignment
    print("Testing top_right (Vertical: top, Horizontal: right)...")
    images = frame(
        word_wbw_images,
        words_text,
        verse_translations=verse_translation,
        verse_vertical_align="top",
        verse_horizontal_align="right",
        max_rows_per_page=3,
    )
    images[0].save(f"{output_dir}/framer_alignment_top_right.png")

    print("Testing center_center (Vertical: center, Horizontal: center)...")
    images = frame(
        word_wbw_images,
        words_text,
        verse_translations=verse_translation,
        verse_vertical_align="center",
        verse_horizontal_align="center",
        max_rows_per_page=3,
    )
    images[0].save(f"{output_dir}/framer_alignment_center_center.png")

    print("Testing top_center (Vertical: top, Horizontal: center)...")
    images = frame(
        word_wbw_images,
        words_text,
        verse_translations=verse_translation,
        verse_vertical_align="top",
        verse_horizontal_align="center",
        max_rows_per_page=3,
    )
    images[0].save(f"{output_dir}/framer_alignment_top_center.png")

    print("Testing center_right (Vertical: center, Horizontal: right)...")
    images = frame(
        word_wbw_images,
        words_text,
        verse_translations=verse_translation,
        verse_vertical_align="center",
        verse_horizontal_align="right",
        max_rows_per_page=3,
    )
    images[0].save(f"{output_dir}/framer_alignment_center_right.png")

    print("test_framer_alignment completed successfully.")


if __name__ == "__main__":
    test_framer()
    test_framer_alignment()
    DatabaseManager().close()
