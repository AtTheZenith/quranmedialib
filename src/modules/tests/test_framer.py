import os
from dataclasses import replace

from src.modules.annotation import annotate_word
from src.modules.database_manager import DatabaseManager
from src.modules.framer import frame
from src.modules.verse_number import verse_number
from src.modules.timage import get_timage
from src.modules.wimage import get_wimage
from src.modules.presets import LANDSCAPE_PRESET


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

    print(f"Converting {len(words_text)} words to images...")
    word_images = [get_wimage(word_text) for word_text in words_text]

    print("Annotating words with translations...")
    word_wbw_images = []
    word_wbw_images.extend(annotate_word(word_images[index], surah, verse, index + 1) for index in range(len(word_images)))

    print("Arranging words into verses with translation...")
    config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    word_wbw_images.append(verse_number(verse, padding=word_config.verse_number_padding, font_size=word_config.verse_number_size))

    word_config = replace(word_config, max_rows_per_page=5, balanced_wrapping=False)

    # Pre-render translations
    translation_images = [get_timage(t, config.content_width, config=text_config) for t in verse_translation]

    # We pass the translation as a list of images, one for each verse segment
    images = frame(
        word_wbw_images,
        words_text,
        translation_images=translation_images,
        config=config,
        word_config=word_config,
    )

    output_dir = "./output/test/framer"
    os.makedirs(output_dir, exist_ok=True)

    images[0].save(f"{output_dir}/framer_1.png")
    images[1].save(f"{output_dir}/framer_2.png")
    images[2].save(f"{output_dir}/framer_3.png")

    print("test_framer completed successfully.")


def test_framer_balancing():
    print("\nRunning test_framer_balancing...")
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

    print(f"Converting {len(words_text)} words to images...")
    word_images = [get_wimage(word_text) for word_text in words_text]

    print("Annotating words with translations...")
    word_wbw_images = []
    word_wbw_images.extend(annotate_word(word_images[index], surah, verse, index + 1) for index in range(len(word_images)))

    print("Arranging words into verses with translation...")
    config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    word_wbw_images.append(verse_number(verse, padding=word_config.verse_number_padding, font_size=word_config.verse_number_size))

    word_config = replace(word_config, max_rows_per_page=5, balanced_wrapping=True)

    # Pre-render translations
    translation_images = [get_timage(t, config.content_width, config=text_config) for t in verse_translation]

    # We pass the translation as a list of images, one for each verse segment
    images = frame(
        word_wbw_images,
        words_text,
        translation_images=translation_images,
        config=config,
        word_config=word_config,
    )

    output_dir = "./output/test/framer"
    os.makedirs(output_dir, exist_ok=True)

    # Save balanced images with a distinct prefix
    images[0].save(f"{output_dir}/framer_balanced_1.png")
    images[1].save(f"{output_dir}/framer_balanced_2.png")
    images[2].save(f"{output_dir}/framer_balanced_3.png")

    print("test_framer_balancing completed successfully.")


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
    
    config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    word_wbw_images.append(verse_number(verse, padding=word_config.verse_number_padding, font_size=word_config.verse_number_size))

    output_dir = "./output/test/framer"
    os.makedirs(output_dir, exist_ok=True)

    # Test cases for alignment
    print("Testing top_right (Vertical: top, Horizontal: right)...")
    word_config_tr = replace(word_config, max_rows_per_page=3, verse_vertical_align="top", verse_horizontal_align="right")
    t_imgs_tr = [get_timage(t, config.content_width, config=text_config) for t in verse_translation]
    images = frame(word_wbw_images, words_text, translation_images=t_imgs_tr, config=config, word_config=word_config_tr)
    images[0].save(f"{output_dir}/framer_alignment_top_right.png")

    print("Testing center_center (Vertical: center, Horizontal: center)...")
    word_config_cc = replace(word_config, max_rows_per_page=3, verse_vertical_align="center", verse_horizontal_align="center")
    t_imgs_cc = [get_timage(t, config.content_width, config=text_config) for t in verse_translation]
    images = frame(word_wbw_images, words_text, translation_images=t_imgs_cc, config=config, word_config=word_config_cc)
    images[0].save(f"{output_dir}/framer_alignment_center_center.png")

    print("Testing top_center (Vertical: top, Horizontal: center)...")
    word_config_tc = replace(word_config, max_rows_per_page=3, verse_vertical_align="top", verse_horizontal_align="center")
    t_imgs_tc = [get_timage(t, config.content_width, config=text_config) for t in verse_translation]
    images = frame(word_wbw_images, words_text, translation_images=t_imgs_tc, config=config, word_config=word_config_tc)
    images[0].save(f"{output_dir}/framer_alignment_top_center.png")

    print("Testing center_right (Vertical: center, Horizontal: right)...")
    word_config_cr = replace(word_config, max_rows_per_page=3, verse_vertical_align="center", verse_horizontal_align="right")
    t_imgs_cr = [get_timage(t, config.content_width, config=text_config) for t in verse_translation]
    images = frame(word_wbw_images, words_text, translation_images=t_imgs_cr, config=config, word_config=word_config_cr)
    images[0].save(f"{output_dir}/framer_alignment_center_right.png")

    print("test_framer_alignment completed successfully.")


if __name__ == "__main__":
    test_framer()
    test_framer_alignment()
    test_framer_balancing()
    DatabaseManager().close()
