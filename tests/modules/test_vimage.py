import pytest
from PIL import Image

from quranmedialib.modules.vimage import QURANIC_STOP_SIGNS, VImage
from quranmedialib.types import (
    Color,
    VerseConfig,
    WordItem,
)


def create_dummy_word(text: str, width: int, height: int, color: Color | None = None) -> WordItem:
    """Helper to create a WordItem with a dummy image."""
    img = Image.new("L", (width, height), 255)
    return WordItem(image=img, text=text, color=color)


def _render_pages(
    items: list[WordItem],
    rows_per_page: int,
    word_config,
    content_width: int = 110,
) -> list[Image.Image]:
    """Render all pages for items honoring page breaks (get_page_chunk is pos-relative)."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20, balanced_wrapping=False)
    vimg = VImage(items, verse_cfg, content_width)
    pages: list[Image.Image] = []
    pos = 0
    while pos < len(items):
        rows, consumed = vimg.get_page_chunk(pos, rows_per_page)
        pages.append(vimg.render(word_config, rows_to_render=rows, mode="RGBA"))
        if consumed <= 0:
            break
        pos += consumed
    return pages


def test_vimage_greedy_pack(word_config):
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

    vimg = VImage(items, verse_cfg, 110)

    # Rows computed on-demand via get_page_chunk
    rows, consumed = vimg.get_page_chunk(0, 10)

    assert len(rows) == 2
    assert len(rows[0][0]) == 2
    assert len(rows[1][0]) == 2
    assert rows[0][1] == 110


def test_vimage_balanced_wrapping(word_config):
    """Test Descending Line Balancing (inverted pyramid shape)."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20, balanced_wrapping=True)

    # items: 5 words of 40px. Total width = 5*40 + 4*10 = 240.
    # content_width = 150.
    # Greedy: 3, 2 (140, 90)
    # Balanced: should attempt to balance.
    items = [create_dummy_word(f"W{i}", 40, 40) for i in range(5)]

    vimg = VImage(items, verse_cfg, 150)

    # Rows computed on-demand via get_page_chunk
    rows, consumed = vimg.get_page_chunk(0, 10)

    assert len(rows) >= 2
    assert sum(len(r[0]) for r in rows) == 5


def test_vimage_stop_sign_chunking(word_config):
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

    vimg = VImage(items, verse_cfg, 110)
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
    vimg_2 = VImage(items_2, verse_cfg, 110)
    # Rows: [W1, W2], [W3, W4], [W5]

    # Request 2 rows.
    # Greedy: [W1, W2], [W3, W4]. Consumed = 4.
    # W4 no stop sign. W3 has one.
    # Pull back to W3. Consumed = 3.
    chunk, consumed = vimg_2.get_page_chunk(0, 2)
    assert consumed == 3


def test_vimage_stop_sign_render_sensitive(word_config) -> None:
    """Ref-free guard: multi-page render must honor Quranic stop-sign page breaks.

    The golden scenario `vimage_stop_signs` only runs locally (refs are
    git-ignored). This assertion runs in the ref-free unit gate, so removing the
    stop-sign adjustment is caught in CI too: with the adjustment the W3 stop sign
    pulls the page break back, so page 1 holds [W1, W2, W3] and differs from the
    greedy [W1, W2, W3, W4] layout.
    """
    with_stop = [
        create_dummy_word("W1", 50, 40),
        create_dummy_word("W2", 50, 40),
        create_dummy_word(f"W3{QURANIC_STOP_SIGNS[0]}", 50, 40),
        create_dummy_word("W4", 50, 40),
        create_dummy_word("W5", 50, 40),
    ]
    no_stop = [create_dummy_word(f"W{i}", 50, 40) for i in range(1, 6)]

    pages_with_stop = _render_pages(with_stop, rows_per_page=2, word_config=word_config)
    pages_no_stop = _render_pages(no_stop, rows_per_page=2, word_config=word_config)

    assert len(pages_with_stop) == 2
    assert len(pages_no_stop) == 2
    # Page 1 = rows [W1, W2], [W3] -> 2 rows (100px); page 2 = [W4, W5] -> 1 row (40px).
    assert pages_with_stop[0].height == 100 and pages_with_stop[1].height == 40

    # Core guard: the stop-sign adjustment must change rendered page-1 pixels.
    # If removed, page 1 becomes byte-identical to the greedy no-stop layout.
    assert pages_with_stop[0].tobytes() != pages_no_stop[0].tobytes()
    # Determinism: same input yields byte-identical output (the golden premise).
    pages_with_stop_repeat = _render_pages(with_stop, rows_per_page=2, word_config=word_config)
    assert pages_with_stop[0].tobytes() == pages_with_stop_repeat[0].tobytes()


def test_vimage_bounding_box(word_config):
    """Verify bounding box (width, height) accuracy."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20)
    items = [
        create_dummy_word("W1", 100, 40),
        create_dummy_word("W2", 50, 60),
    ]
    # content_width 200 -> [W1, W2]. width = 100 + 10 + 50 = 160. height = 60.
    vimg = VImage(items, verse_cfg, 200)

    # Rows computed on-demand via get_page_chunk
    rows, consumed = vimg.get_page_chunk(0, 10)

    assert len(rows) == 1
    assert rows[0][1] == 160  # W1(100) + spacing(10) + W2(50)
    total_height = sum(r[2] for r in rows) + (len(rows) - 1) * verse_cfg.row_spacing
    assert total_height == 60


def test_vimage_render_modes(word_config):
    """Test render() output for both grayscale masks and RGBA."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20)
    items = [create_dummy_word("W1", 50, 40)]
    vimg = VImage(items, verse_cfg, 200)

    # Rows computed on-demand via get_page_chunk
    rows, consumed = vimg.get_page_chunk(0, 10)

    # Test RGBA
    img_rgba = vimg.render(word_config, rows_to_render=rows, mode="RGBA")
    assert img_rgba.mode == "RGBA"

    # Test L
    img_l = vimg.render(word_config, rows_to_render=rows, mode="L")
    assert img_l.mode == "L"


def test_vimage_layer_direct(word_config):
    """Test that .layer() renders correctly onto a provided canvas."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20)
    items = [create_dummy_word("W1", 50, 40)]
    vimg = VImage(items, verse_cfg, 200)

    # Rows computed on-demand via get_page_chunk
    rows, consumed = vimg.get_page_chunk(0, 10)

    # Create a blank canvas
    canvas = Image.new("RGBA", (100, 100), (0, 0, 0, 0))

    # Layer at (10, 10) with center=False to test RTL right-alignment
    vimg.layer(canvas, x=10, y=10, word_config=word_config, rows_to_render=rows, center=False)

    # Since it's RTL, W1 (width 50) will be at x = 10 + 50 = 60.
    # The pixels for W1 should be in [10, 60)
    assert canvas.getpixel((11, 11)) != (0, 0, 0, 0)
    assert canvas.getpixel((59, 11)) != (0, 0, 0, 0)
    # Outside boundaries
    assert canvas.getpixel((9, 11)) == (0, 0, 0, 0)
    assert canvas.getpixel((61, 11)) == (0, 0, 0, 0)


def test_vimage_layer_vs_render_equality(word_config):
    """Verify that .layer() produces the same pixels as .render()."""
    verse_cfg = VerseConfig(word_spacing=10, row_spacing=20)
    items = [
        create_dummy_word("W1", 50, 40),
        create_dummy_word("W2", 60, 40),
    ]
    vimg = VImage(items, verse_cfg, 200)

    # Rows computed on-demand via get_page_chunk
    rows, consumed = vimg.get_page_chunk(0, 10)

    # 1. Use the old path: render image then paste it
    img_rendered = vimg.render(word_config, rows_to_render=rows)
    canvas_old = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    canvas_old.paste(img_rendered, (0, 0))

    # 2. Use the new path: layer directly (center=False to match render)
    canvas_new = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    vimg.layer(canvas_new, x=0, y=0, word_config=word_config, rows_to_render=rows, center=False)

    # Compare pixels
    assert canvas_old.tobytes() == canvas_new.tobytes()


# === Benchmark Tests ===


@pytest.mark.benchmark
def test_vimage_benchmark_greedy_pack(word_config) -> None:
    """Benchmark VImage._greedy_pack with many items."""
    items = [create_dummy_word(f"W{i}", 40, 40) for i in range(20)]
    verse_cfg = VerseConfig(word_spacing=5, row_spacing=10, balanced_wrapping=False)
    vimg = VImage(items, verse_cfg, 120)
    rows, consumed = vimg.get_page_chunk(0, 10)
    assert consumed == 20
    assert len(rows) >= 1


@pytest.mark.benchmark
def test_vimage_benchmark_render(word_config) -> None:
    """Benchmark VImage.render with multiple rows."""
    items = [create_dummy_word(f"W{i}", 50, 40) for i in range(10)]
    verse_cfg = VerseConfig(word_spacing=5, row_spacing=10)
    vimg = VImage(items, verse_cfg, 150)
    rows, consumed = vimg.get_page_chunk(0, 10)
    img = vimg.render(word_config, rows_to_render=rows)
    assert img is not None
    assert img.size[0] > 0


@pytest.mark.benchmark
def test_vimage_benchmark_stop_sign_adjustment(word_config) -> None:
    """Benchmark stop-sign-aware page chunking with many items."""
    items = [create_dummy_word(f"W{i}{QURANIC_STOP_SIGNS[i % len(QURANIC_STOP_SIGNS)]}", 50, 40) for i in range(50)]
    verse_cfg = VerseConfig(word_spacing=5, row_spacing=10)
    vimg = VImage(items, verse_cfg, 150)
    chunk, consumed = vimg.get_page_chunk(0, 5)
    assert consumed > 0
