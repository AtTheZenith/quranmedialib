from PIL import Image

from quranmedialib.modules.vimage import QURANIC_STOP_SIGNS, VImage
from quranmedialib.types import (
    Color,
    LayoutConfig,
    Padding,
    VerseConfig,
    WordItem,
)


def create_dummy_word(text: str, width: int, height: int, color: Color | None = None) -> WordItem:
    """Helper to create a WordItem with a dummy image."""
    img = Image.new("L", (width, height), 255)
    return WordItem(image=img, text=text, color=color)


def test_vimage_greedy_pack(layout_config, word_config):
    """Test RTL layout and greedy row packing."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20, balanced_wrapping=False)

    # Items: W1(50), W2(50), W3(50), W4(50)
    # Content width: 110.
    # Row 1: W1(50) + 10 + W2(50) = 110. (Fits)
    # Row 2: W3(50) + 10 + W4(50) = 110. (Fits)
    items = [
        create_dummy_word("W1", 50, 40),
        create_dummy_word("W2", 50, 40),
        create_dummy_word("W3", 50, 40),
        create_dummy_word("W4", 50, 40),
    ]

    narrow_layout = LayoutConfig(max_width=110, image_height=200, padding=Padding(0, 0, 0, 0))

    vimg = VImage(items, verse_cfg, narrow_layout)

    assert len(vimg.rows) == 2
    assert len(vimg.rows[0][0]) == 2
    assert len(vimg.rows[1][0]) == 2
    assert vimg.rows[0][1] == 110


def test_vimage_balanced_wrapping(layout_config, word_config):
    """Test Descending Line Balancing (inverted pyramid shape)."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20, balanced_wrapping=True)

    # items: 5 words of 40px. Total width = 5*40 + 4*10 = 240.
    # content_width = 150.
    # Greedy: 3, 2 (140, 90)
    # Balanced: should attempt to balance.
    items = [create_dummy_word(f"W{i}", 40, 40) for i in range(5)]

    narrow_layout = LayoutConfig(max_width=150, image_height=200, padding=Padding(0, 0, 0, 0))

    vimg = VImage(items, verse_cfg, narrow_layout)

    assert len(vimg.rows) >= 2
    assert sum(len(r[0]) for r in vimg.rows) == 5


def test_vimage_stop_sign_chunking(layout_config, word_config):
    """Test Quranic stop-sign aware page breaking using get_page_chunk."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20)

    # W1, W2(Stop), W3, W4(Stop), W5
    items = [
        create_dummy_word("W1", 50, 40),
        create_dummy_word(f"W2{QURANIC_STOP_SIGNS[0]}", 50, 40),
        create_dummy_word("W3", 50, 40),
        create_dummy_word(f"W4{QURANIC_STOP_SIGNS[1]}", 50, 40),
        create_dummy_word("W5", 50, 40),
    ]

    narrow_layout = LayoutConfig(max_width=110, image_height=200, padding=Padding(0, 0, 0, 0))

    vimg = VImage(items, verse_cfg, narrow_layout)
    # Rows: [W1, W2], [W3, W4], [W5]

    # Request 2 rows.
    # Without stop sign: Row1, Row2. items_consumed = 4.
    # Last word W4 has a stop sign, so keep 4.
    chunk, consumed = vimg.get_page_chunk(0, 2)
    assert consumed == 4

    # Request 3 rows.
    chunk, consumed = vimg.get_page_chunk(0, 3)
    assert consumed == 5

    # Test adjustment by making it so the break is NOT on a stop sign.
    # Items: W1, W2, W3(Stop), W4, W5
    items_2 = [
        create_dummy_word("W1", 50, 40),
        create_dummy_word("W2", 50, 40),
        create_dummy_word(f"W3{QURANIC_STOP_SIGNS[0]}", 50, 40),
        create_dummy_word("W4", 50, 40),
        create_dummy_word("W5", 50, 40),
    ]
    vimg_2 = VImage(items_2, verse_cfg, narrow_layout)
    # Rows: [W1, W2], [W3, W4], [W5]

    # Request 2 rows.
    # Greedy: [W1, W2], [W3, W4]. Consumed = 4.
    # W4 no stop sign. W3 has one.
    # Pull back to W3. Consumed = 3.
    chunk, consumed = vimg_2.get_page_chunk(0, 2)
    assert consumed == 3


def test_vimage_bounding_box(layout_config, word_config):
    """Verify bounding box (width, height) accuracy."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20)
    items = [
        create_dummy_word("W1", 100, 40),
        create_dummy_word("W2", 50, 60),
    ]
    # content_width 200 -> [W1, W2]. width = 100 + 10 + 50 = 160. height = 60.
    narrow_layout = LayoutConfig(max_width=200, image_height=200, padding=Padding(0, 0, 0, 0))
    vimg = VImage(items, verse_cfg, narrow_layout)

    assert vimg.width == 160
    assert vimg.height == 60


def test_vimage_render_modes(layout_config, word_config):
    """Test render() output for both grayscale masks and RGBA."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20)
    items = [create_dummy_word("W1", 50, 40)]
    narrow_layout = LayoutConfig(max_width=200, image_height=200, padding=Padding())
    vimg = VImage(items, verse_cfg, narrow_layout)

    # Test RGBA
    img_rgba = vimg.render(word_config, mode="RGBA")
    assert img_rgba.mode == "RGBA"

    # Test L
    img_l = vimg.render(word_config, mode="L")
    assert img_l.mode == "L"
