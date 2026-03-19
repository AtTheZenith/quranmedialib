import os
from dataclasses import replace

from PIL import Image

from src.modules.annotation import annotate_words
from src.modules.database_manager import DatabaseManager
from src.modules.framer import frame
from src.modules.presets import LANDSCAPE_PRESET
from src.modules.timage import get_timage
from src.modules.types import LayoutConfig, WordConfig, WordItem
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

    config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    print(f"Converting {len(words_text)} words to images...")
    word_images = [get_wimage(word_text, word_config) for word_text in words_text]

    print("Annotating words with translations...")
    word_wbw_images = annotate_words(word_images, surah, verse, 1, word_config=word_config)
    word_wbw_images.append(verse_number(verse, word_config=word_config))

    # Pre-render translations
    translation_images = [get_timage(t, config=text_config) for t in verse_translation]

    # Bundle into WordItems
    items = [WordItem(img, text) for img, text in zip(word_wbw_images[:-1], words_text)]
    items.append(WordItem(word_wbw_images[-1], str(verse)))  # Verse number

    # We pass the translation as a list of images, one for each verse segment
    images = frame(
        items,
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


def test_framer_alignment():
    print("\nRunning test_framer_alignment...")
    database_manager = DatabaseManager()

    # Using a short verse for clear centering visibility (e.g., 108:1)
    surah = 108
    verse = 1
    words_text = database_manager.get_verse(surah, verse).split()
    verse_translation = [database_manager.get_translation_from_verse(surah, verse)]
    config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    print(f"Converting {len(words_text)} words to images...")
    word_images = [get_wimage(word_text, word_config) for word_text in words_text]

    print("Annotating words...")
    word_wbw_images = annotate_words(word_images, surah, verse, 1, word_config=word_config)
    word_wbw_images.append(verse_number(verse, word_config=word_config))

    output_dir = "./output/test/framer"
    os.makedirs(output_dir, exist_ok=True)

    # Bundle into WordItems
    items = [WordItem(img, text) for img, text in zip(word_wbw_images, words_text + [str(verse)])]

    # Test cases for alignment
    print("Testing top_right (Vertical: top, Horizontal: right)...")
    word_config_tr = replace(word_config, max_rows_per_page=3, verse_vertical_align="top", verse_horizontal_align="right")
    t_imgs_tr = [get_timage(t, config=text_config) for t in verse_translation]
    images = frame(items, translation_images=t_imgs_tr, config=config, word_config=word_config_tr)
    images[0].save(f"{output_dir}/framer_alignment_top_right.png")

    print("Testing center_center (Vertical: center, Horizontal: center)...")
    word_config_cc = replace(word_config, max_rows_per_page=3, verse_vertical_align="center", verse_horizontal_align="center")
    t_imgs_cc = [get_timage(t, config=text_config) for t in verse_translation]
    images = frame(items, translation_images=t_imgs_cc, config=config, word_config=word_config_cc)
    images[0].save(f"{output_dir}/framer_alignment_center_center.png")

    print("Testing top_center (Vertical: top, Horizontal: center)...")
    word_config_tc = replace(word_config, max_rows_per_page=3, verse_vertical_align="top", verse_horizontal_align="center")
    t_imgs_tc = [get_timage(t, config=text_config) for t in verse_translation]
    images = frame(items, translation_images=t_imgs_tc, config=config, word_config=word_config_tc)
    images[0].save(f"{output_dir}/framer_alignment_top_center.png")

    print("Testing center_right (Vertical: center, Horizontal: right)...")
    word_config_cr = replace(word_config, max_rows_per_page=3, verse_vertical_align="center", verse_horizontal_align="right")
    t_imgs_cr = [get_timage(t, config=text_config) for t in verse_translation]
    images = frame(items, translation_images=t_imgs_cr, config=config, word_config=word_config_cr)
    images[0].save(f"{output_dir}/framer_alignment_center_right.png")

    print("test_framer_alignment completed successfully.")


def test_framer_offsets():
    print("\nRunning test_framer_offsets...")
    # Create dummy words
    words = [Image.new("RGBA", (50, 50), (255, 0, 0, 255)) for _ in range(3)]

    # Config without offsets
    config_0 = LayoutConfig(
        max_width=500,
        image_height=500,
        padding=(0, 0, 0, 0),
        wimage_x_offset=0,
        wimage_y_offset=0,
    )

    # Config with offsets
    config_offset = LayoutConfig(
        max_width=500,
        image_height=500,
        padding=(0, 0, 0, 0),
        wimage_x_offset=50,
        wimage_y_offset=50,
    )

    word_config = WordConfig(
        font_size=1,
        word_spacing=10,
        row_spacing=10,
        max_rows_per_page=1,
        verse_vertical_align="top",  # align top to make Y check easier
        verse_horizontal_align="right",  # align right (start) to make X check easier
    )

    word_items = [WordItem(w) for w in words]
    bbox_0 = frame_words(word_items, config_0, word_config)
    bbox_offset = frame_words(word_items, config_offset, word_config)
    print(f"BBox 0: {bbox_0}")
    print(f"BBox Offset: {bbox_offset}")

    # Check X/Y offsets
    assert bbox_offset[0] == bbox_0[0] + 50, f"X offset failed: {bbox_offset[0]} != {bbox_0[0] + 50}"
    assert bbox_offset[1] == bbox_0[1] + 50, f"Y offset failed: {bbox_offset[1]} != {bbox_0[1] + 50}"

    # Test TImage Offset
    t_img = Image.new("RGBA", (100, 50), (0, 255, 0, 255))

    # Config with T offset
    config_t = LayoutConfig(
        max_width=500,
        image_height=500,
        padding=(0, 0, 0, 0),
        timage_x_offset=50,
        timage_y_offset=0,
    )

    pages_t = frame(word_items, translation_images=[t_img], config=config_t, word_config=word_config)
    img_t = pages_t[0]

    # Check TImage position
    # Centered X: (500 - 100) // 2 = 200. Offset X: 200 + 50 = 250.
    # Center Y fallback with padding 0: 500 - 0 - 25 = 475.
    pixel = img_t.getpixel((260, 480))  # Should be green (within 250-350 range)
    assert pixel == (0, 255, 0, 255), f"TImage X offset failed: {pixel}"

    print("test_framer_offsets completed successfully.")


def frame_words(words, config, word_config):
    pages_0 = frame(words, config=config, word_config=word_config)
    img_0 = pages_0[0]
    return img_0.getbbox()


if __name__ == "__main__":
    test_framer()
    test_framer_alignment()
    test_framer_offsets()
    DatabaseManager().close()
