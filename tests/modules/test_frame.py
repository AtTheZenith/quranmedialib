import pytest
from PIL import Image

from quranmedialib.modules.frame import Frame
from quranmedialib.types import ResolvedRect


def test_frame_initialization():
    """Test canvas initialization (size, transparency)."""
    frame = Frame(1000, 500)

    assert frame.image.size == (1000, 500)
    assert frame.image.mode == "RGBA"
    # Check center pixel is transparent
    assert frame.image.getpixel((500, 250)) == (0, 0, 0, 0)


def test_frame_layer_at_positioning(dummy_rgba_image):
    """Verify layer_at places content at the correct rect."""
    frame = Frame(1000, 1000)
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    rect = ResolvedRect(left=50, top=60, width=100, height=100)
    frame.layer_at(img, rect)
    assert frame.image.getpixel((50, 60)) == (255, 0, 0, 255)
    assert frame.image.getpixel((49, 59)) == (0, 0, 0, 0)


def test_frame_layer_at_offset(dummy_rgba_image):
    """Verify layer_at with offset rect."""
    frame = Frame(1000, 1000)
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    rect = ResolvedRect(left=10, top=20, width=100, height=100)
    frame.layer_at(img, rect)
    assert frame.image.getpixel((10, 20)) == (255, 0, 0, 255)
    frame2 = Frame(1000, 1000)
    rect2 = ResolvedRect(left=50, top=60, width=100, height=100)
    frame2.layer_at(img, rect2)
    assert frame2.image.getpixel((50, 60)) == (255, 0, 0, 255)


def test_frame_layer_at_modes():
    """Test layering modes via layer_at."""
    frame = Frame(100, 100)

    # 1. 'L' mask
    mask = Image.new("L", (20, 20), 0)
    mask.putpixel((5, 5), 255)
    text_color = (123, 234, 56, 255)
    frame.layer_at(mask, ResolvedRect(left=0, top=0, width=20, height=20), text_color=text_color)
    assert frame.image.getpixel((5, 5)) == text_color

    # 2. 'RGBA'
    frame2 = Frame(100, 100)
    rgba_img = Image.new("RGBA", (20, 20), (255, 0, 0, 128))
    frame2.layer_at(rgba_img, ResolvedRect(left=20, top=0, width=20, height=20))
    assert frame2.image.getpixel((25, 5)) == (255, 0, 0, 128)

    # 3. RGB paste
    frame3 = Frame(100, 100)
    rgb_img = Image.new("RGB", (20, 20), (0, 255, 0))
    frame3.layer_at(rgb_img, ResolvedRect(left=40, top=0, width=20, height=20))
    assert frame3.image.getpixel((45, 5)) == (0, 255, 0, 255)


def test_frame_layer_at_stacking():
    """Verify stacking order (last layer on top)."""
    frame = Frame(100, 100)
    img1 = Image.new("RGBA", (50, 50), (255, 0, 0, 255))
    img2 = Image.new("RGBA", (50, 50), (0, 255, 0, 255))
    rect = ResolvedRect(left=0, top=0, width=50, height=50)
    frame.layer_at(img1, rect)
    frame.layer_at(img2, rect)
    assert frame.image.getpixel((10, 10)) == (0, 255, 0, 255)


def test_frame_layerable_integration(word_config, layout_config):
    """Verify Frame correctly handles Layerable objects via layer_at."""
    from quranmedialib.modules.vimage import VImage
    from quranmedialib.types import VerseConfig, WordItem, ResolvedRect

    verse_cfg = VerseConfig(word_spacing=0, row_spacing=0)
    word_img = Image.new("L", (100, 40), 255)
    items = [WordItem(image=word_img, text="Test")]

    content_width = 500
    vimg = VImage(items, verse_cfg, content_width)
    rows, consumed = vimg.get_page_chunk(0, 10)

    frame = Frame(1000, 1000)
    rect = ResolvedRect(left=0, top=0, width=content_width, height=200)
    frame.layer_at(vimg, rect, word_config=word_config, rows_to_render=rows)

    assert frame.image.getpixel((0, 0)) != (0, 0, 0, 0)
    assert frame.image.getpixel((99, 0)) != (0, 0, 0, 0)
