import pytest
from PIL import Image

from quranmedialib.modules.frame import Frame
from quranmedialib.types import (
    FrameConfig,
    HorizontalAlignment,
    Padding,
    VerticalAlignment,
)


def test_frame_initialization():
    """Test canvas initialization (size, transparency)."""
    config = FrameConfig(max_width=1000, image_height=500, padding=Padding(10, 10, 10, 10))
    frame = Frame(config)

    assert frame.image.size == (1000, 500)
    assert frame.image.mode == "RGBA"
    # Check center pixel is transparent
    assert frame.image.getpixel((500, 250)) == (0, 0, 0, 0)


@pytest.mark.parametrize(
    "h_align, v_align",
    [
        (HorizontalAlignment.LEFT, VerticalAlignment.TOP),
        (HorizontalAlignment.LEFT, VerticalAlignment.CENTER),
        (HorizontalAlignment.LEFT, VerticalAlignment.BOTTOM),
        (HorizontalAlignment.CENTER, VerticalAlignment.TOP),
        (HorizontalAlignment.CENTER, VerticalAlignment.CENTER),
        (HorizontalAlignment.CENTER, VerticalAlignment.BOTTOM),
        (HorizontalAlignment.RIGHT, VerticalAlignment.TOP),
        (HorizontalAlignment.RIGHT, VerticalAlignment.CENTER),
        (HorizontalAlignment.RIGHT, VerticalAlignment.BOTTOM),
    ],
)
def test_frame_alignments(h_align, v_align, dummy_rgba_image):
    """Exhaustively test HorizontalAlignment and VerticalAlignment combinations."""
    # No padding, no offset for pure alignment test
    config = FrameConfig(
        max_width=1000, image_height=1000, padding=Padding(0, 0, 0, 0), wimage_x_offset=0, wimage_y_offset=0
    )
    frame = Frame(config)

    # Use a smaller image to make calculations easy
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))

    frame.layer(img, alignment=(h_align, v_align))

    # Expected X
    if h_align == HorizontalAlignment.LEFT:
        expected_x = 0
    elif h_align == HorizontalAlignment.RIGHT:
        expected_x = 1000 - 100
    else:
        expected_x = (1000 - 100) // 2

    # Expected Y
    if v_align == VerticalAlignment.TOP:
        expected_y = 0
    elif v_align == VerticalAlignment.BOTTOM:
        expected_y = 1000 - 100
    else:
        expected_y = (1000 - 100) // 2

    # Check a pixel that should be colored
    assert frame.image.getpixel((expected_x, expected_y)) == (255, 0, 0, 255)


def test_frame_offset(dummy_rgba_image):
    """Verify offset application."""
    config = FrameConfig(
        max_width=1000,
        image_height=1000,
        padding=Padding(0, 0, 0, 0),
        wimage_horizontal_align=HorizontalAlignment.LEFT,
        wimage_vertical_align=VerticalAlignment.TOP,
        wimage_x_offset=10,
        wimage_y_offset=20,
    )
    frame = Frame(config)
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))

    frame.layer(img)  # Uses config offsets
    assert frame.image.getpixel((10, 20)) == (255, 0, 0, 255)

    # Test override offset
    frame2 = Frame(config)
    frame2.layer(img, offset=(50, 60))
    assert frame2.image.getpixel((50, 60)) == (255, 0, 0, 255)


def test_frame_layering_modes():
    """Test layering modes: 'L' masks with text_color, 'RGBA', and standard paste."""
    config = FrameConfig(max_width=100, image_height=100)
    frame = Frame(config)

    # 1. 'L' mask
    mask = Image.new("L", (20, 20), 0)
    mask.putpixel((5, 5), 255)
    text_color = (123, 234, 56, 255)

    # Align to top-left, no offset
    frame.layer(mask, alignment=(HorizontalAlignment.LEFT, VerticalAlignment.TOP), offset=(0, 0), text_color=text_color)
    # Center of canvas is (50, 50). Alignment center is (40, 40).
    # Left/Top is (0,0).
    # - Wait, alignment=LEFT/TOP with offset=(0,0) and padding=0 should be at (0,0).
    # Check pixel (5, 5) - relative to top-left
    assert frame.image.getpixel((5, 5)) == text_color

    # 2. 'RGBA'
    rgba_img = Image.new("RGBA", (20, 20), (255, 0, 0, 128))  # Semi-transparent red
    frame.layer(rgba_img, alignment=(HorizontalAlignment.LEFT, VerticalAlignment.TOP), offset=(20, 0))
    # (25, 5) should be semi-transparent red
    assert frame.image.getpixel((25, 5)) == (255, 0, 0, 128)

    # 3. standard paste (RGB)
    rgb_img = Image.new("RGB", (20, 20), (0, 255, 0))  # Opaque green
    frame.layer(rgb_img, alignment=(HorizontalAlignment.LEFT, VerticalAlignment.TOP), offset=(40, 0))
    assert frame.image.getpixel((45, 5)) == (0, 255, 0, 255)


def test_frame_stacking_order():
    """Verify stacking order (last layer on top)."""
    config = FrameConfig(max_width=100, image_height=100)
    frame = Frame(config)

    img1 = Image.new("RGBA", (50, 50), (255, 0, 0, 255))  # Red
    img2 = Image.new("RGBA", (50, 50), (0, 255, 0, 255))  # Green

    # Both at the same position
    frame.layer(img1, alignment=(HorizontalAlignment.LEFT, VerticalAlignment.TOP), offset=(0, 0))
    frame.layer(img2, alignment=(HorizontalAlignment.LEFT, VerticalAlignment.TOP), offset=(0, 0))

    # Green should be on top
    assert frame.image.getpixel((10, 10)) == (0, 255, 0, 255)


def test_frame_layerable_integration(dummy_rgba_image, layout_config, word_config):
    """Verify that Frame correctly handles Layerable objects (like VImage)."""
    from quranmedialib.modules.vimage import VImage
    from quranmedialib.types import VerseConfig

    # Create a simple VImage
    verse_cfg = VerseConfig(word_spacing=0, row_spacing=0)
    items = [
        # 100x40 word
        # create_dummy_word helper from test_vimage.py isn't here, let's make one
        # we can't import it because it's not exported.
        # so we'll just use a WordItem with a manual image.
        # Using a white 'L' mask to be consistent with vimage rendering
        # the logic in vimage.layer expects either 'L' or 'RGBA'
    ]
    # To avoid importing helpers from other tests, we just define the WordItem manually
    from PIL import Image

    from quranmedialib.types import WordItem

    word_img = Image.new("L", (100, 40), 255)
    items = [WordItem(image=word_img, text="Test")]

    # Setup layout
    layout_cfg = layout_config  # from fixture
    vimg = VImage(items, verse_cfg, layout_cfg)

    # Rows computed on-demand via get_page_chunk
    rows, consumed = vimg.get_page_chunk(0, 10)

    # Frame it
    config = FrameConfig(
        max_width=1000,
        image_height=1000,
        padding=Padding(0, 0, 0, 0),
        wimage_horizontal_align=HorizontalAlignment.LEFT,
        wimage_vertical_align=VerticalAlignment.TOP,
    )
    frame = Frame(config)

    # Layer the Layerable (VImage)
    frame.layer(vimg, word_config=word_config, rows_to_render=rows)

    # In VImage.layer:
    # total_width = 100.
    # Anchor x=0, y=0.
    # Word 1: current_x = 0 + 100 = 100.
    # paste(color, (current_x - w_img.width, ry)) -> (100-100, 0) = (0,0)
    assert frame.image.getpixel((0, 0)) != (0, 0, 0, 0)
    assert frame.image.getpixel((99, 0)) != (0, 0, 0, 0)
