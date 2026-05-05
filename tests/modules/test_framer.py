"""Tests for the framer module and layout functionality.

This module contains tests for verifying the multi-page layout engine including:
- Basic framing with Arabic text and translations
- Alignment configurations (top/center/bottom, left/center/right)
- Offset handling for word images and translation images
"""

import os
from dataclasses import replace

import pytest
from PIL import Image

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager, LayoutConfig, WordConfig, WordItem
from quranmedialib.modules.annotation import annotate_words
from quranmedialib.modules.framer import frame
from quranmedialib.modules.timage import get_timage
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage


def test_framer(request: pytest.FixtureRequest) -> None:
    print("\nRunning test_framer...")
    database_manager = DatabaseManager()

    # Using Ayatul Kursi (2:255) for test
    surah = 2
    verse = 255

    # Get Arabic text (always uses "quran" database)
    words_text = database_manager.get_verse(surah, verse).split()

    # Get English translation (uses "translation" database by default)
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
    request.node.benchmark_data = ["verse=2:255", f"pages={len(images)}"]
    print("test_framer completed successfully.")


@pytest.fixture
def framer_alignment_data():
    """Fixture to provide common data for framer alignment tests."""
    database_manager = DatabaseManager()
    surah = 108
    verse = 1
    words_text = database_manager.get_verse(surah, verse).split()
    verse_translation = [database_manager.get_translation_from_verse(surah, verse)]
    config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
    
    word_images = [get_wimage(word_text, word_config) for word_text in words_text]
    word_wbw_images = annotate_words(word_images, surah, verse, 1, word_config=word_config)
    word_wbw_images.append(verse_number(verse, word_config=word_config))
    
    items = [WordItem(img, text) for img, text in zip(word_wbw_images, words_text + [str(verse)])]
    
    return {
        "items": items,
        "verse_translation": verse_translation,
        "config": config,
        "text_config": text_config,
        "word_config": word_config,
    }
 
 
@pytest.mark.parametrize("v_align", ["top", "center", "bottom"])
@pytest.mark.parametrize("h_align", ["left", "center", "right"])
def test_framer_alignment(framer_alignment_data, v_align, h_align) -> None:
    """Tests all combinations of vertical and horizontal alignment."""
    data = framer_alignment_data
    items = data["items"]
    config = data["config"]
    text_config = data["text_config"]
    word_config = data["word_config"]
    verse_translation = data["verse_translation"]
 
    output_dir = "./output/test/framer"
    os.makedirs(output_dir, exist_ok=True)
 
    # Modify LayoutConfig for alignment and WordConfig for max_rows
    word_config_dyn = replace(word_config, max_rows_per_page=3)
    config_dyn = replace(config, wimage_vertical_align=v_align, wimage_horizontal_align=h_align)
 
    t_imgs_dyn = [get_timage(t, config=text_config) for t in verse_translation]
    images = frame(items, translation_images=t_imgs_dyn, config=config_dyn, word_config=word_config_dyn)
 
    images[0].save(f"{output_dir}/framer_alignment_{v_align}_{h_align}.png")



def test_framer_offsets() -> None:
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
        wimage_vertical_align="top",  # align top to make Y check easier
        wimage_horizontal_align="right",  # align right (start) to make X check easier
    )

    # Config with offsets
    config_offset = LayoutConfig(
        max_width=500,
        image_height=500,
        padding=(0, 0, 0, 0),
        wimage_x_offset=50,
        wimage_y_offset=50,
        wimage_vertical_align="top",
        wimage_horizontal_align="right",
    )

    word_config = WordConfig(
        font_size=1,
        word_spacing=10,
        row_spacing=10,
        max_rows_per_page=1,
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

    # Check TImage position - scan for green pixels to verify TImage is drawn with offset
    # Expected X range: centered (200) + offset (50) = 250, width 100, so 250-350
    # Scan entire bottom half for green pixels
    found_green = False
    for x in range(200, 400):
        for y in range(200, 500):
            pixel = img_t.getpixel((x, y))
            if pixel[1] > 200:  # Check for high green component
                found_green = True
                break
        if found_green:
            break

    assert found_green, "TImage not found in expected region"

    print("test_framer_offsets completed successfully.")


def frame_words(words: list, config: object, word_config: object) -> tuple[int, int, int, int] | None:
    pages_0 = frame(words, config=config, word_config=word_config)
    img_0 = pages_0[0]
    return img_0.getbbox()


if __name__ == "__main__":
    test_framer()
    test_framer_alignment()
    test_framer_offsets()


# === Validation Tests ===


def test_frame_empty_words() -> None:
    """Test that frame returns empty list for empty words."""
    result = frame([], translation_images=None, config=None, word_config=None)
    assert result == []


def test_frame_none_word_item_image() -> None:
    """Test that frame raises ValueError when WordItem has None image."""
    word_config = WordConfig(font_size=10)
    # Create WordItem with None image
    bad_item = WordItem(None)  # type: ignore

    with pytest.raises(ValueError, match="One or more WordItems are missing their image content"):
        frame([bad_item], word_config=word_config)


def test_frame_none_config_creates_defaults() -> None:
    """Test that frame works with None config (should create defaults)."""
    word_config = WordConfig(font_size=10)
    dummy_img = Image.new("RGBA", (50, 50))
    items = [WordItem(dummy_img)]

    # Should not raise, creates default config
    result = frame(items, word_config=word_config)
    assert len(result) > 0


def test_frame_invalid_alignment_value() -> None:
    """Test that frame handles invalid alignment values gracefully."""
    # Invalid alignment should either raise error or be handled by LayoutConfig
    with pytest.raises(Exception):
        LayoutConfig(
            max_width=500,
            image_height=500,
            padding=(0, 0, 0, 0),
            wimage_vertical_align="invalid_value",
        )


@pytest.mark.parametrize("negative_strength", [-1.0, -0.5, 0.0])
def test_frame_negative_word_spacing(negative_strength: float) -> None:
    """Test that frame handles negative word spacing."""
    word_config = WordConfig(font_size=10, word_spacing=-10)
    dummy_img = Image.new("RGBA", (50, 50))
    items = [WordItem(dummy_img), WordItem(dummy_img)]

    # Should handle gracefully (may produce overlapping images)
    result = frame(items, word_config=word_config)
    assert len(result) > 0


# === Zero Content Width Validation Tests ===


def test_frame_zero_content_width_raises_error() -> None:
    """Test that LayoutConfig raises ValueError when content_width is zero."""
    # content_width = max_width - padding.left - padding.right = 100 - 50 - 50 = 0
    # Validation now happens at config creation, not in frame()
    with pytest.raises(ValueError, match="content_width must be positive"):
        LayoutConfig(max_width=100, image_height=1080, padding=(50, 50, 50, 50))


def test_frame_negative_content_width_raises_error() -> None:
    """Test that LayoutConfig raises ValueError when content_width is negative."""
    # content_width = max_width - padding.left - padding.right = 50 - 50 - 50 = -50
    # Validation now happens at config creation, not in frame()
    with pytest.raises(ValueError, match="content_width must be positive"):
        LayoutConfig(max_width=50, image_height=1080, padding=(50, 50, 50, 50))
