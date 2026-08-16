from PIL import Image, ImageDraw

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
    from quranmedialib.types import ResolvedRect, VerseConfig, WordItem

    verse_cfg = VerseConfig(word_spacing=0, row_spacing=0)
    word_img = Image.new("L", (100, 40), 255)
    items = [WordItem(image=word_img, text="Test")]

    content_width = 500
    vimg = VImage(items, verse_cfg, content_width)
    rows, consumed = vimg.get_page_chunk(0, 10)

    frame = Frame(1000, 1000)
    rect = ResolvedRect(left=0, top=0, width=content_width, height=200)
    # Default center=True: 100px word centred in 500px rect => x=200
    frame.layer_at(vimg, rect, word_config=word_config, rows_to_render=rows)

    assert frame.image.getpixel((200, 0)) != (0, 0, 0, 0)
    assert frame.image.getpixel((299, 0)) != (0, 0, 0, 0)


def test_frame_sidecar_disabled_by_default():
    """sidecar_layers stays None unless collect_sidecar is enabled (zero-cost default)."""
    frame = Frame(100, 100)
    assert frame.sidecar_layers is None


def test_frame_collect_sidecar_records_plain_image_node():
    """A plain image with collect_sidecar records a default image node at the paste box."""
    frame = Frame(1000, 1000, collect_sidecar=True)
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    frame.layer_at(img, ResolvedRect(left=50, top=60, width=100, height=100))

    assert frame.sidecar_layers == [{"class_type": "image", "x": 50, "y": 60, "w": 100, "h": 100}]


def test_frame_sidecar_image_node_reflects_keep_bottom_and_centring():
    """The default image node records the final paste position after adjustments."""
    frame = Frame(1000, 1000, collect_sidecar=True)
    img = Image.new("RGBA", (80, 40), (255, 0, 0, 255))
    # rect wider than image -> centred x; keep_bottom -> bottom-aligned y
    frame.layer_at(img, ResolvedRect(left=100, top=100, width=200, height=200), keep_bottom=True)

    assert frame.sidecar_layers == [{"class_type": "image", "x": 160, "y": 260, "w": 80, "h": 40}]


def test_frame_sidecar_record_is_completed_with_actual_paste_position():
    """A sidecar_record's declared position slot is completed by Frame, not the caller."""
    frame = Frame(1000, 1000, collect_sidecar=True)
    img = Image.new("RGBA", (80, 40), (255, 0, 0, 255))
    record = {"class_type": "translation", "bbox": {"x": 0, "y": 0, "w": 80, "h": 40}, "position": None}
    frame.layer_at(
        img,
        ResolvedRect(left=100, top=100, width=200, height=200),
        keep_bottom=True,
        sidecar_record=record,
    )

    # Frame is the single authority on position: keep_bottom moves y to bottom edge.
    assert frame.sidecar_layers == [
        {"class_type": "translation", "bbox": {"x": 0, "y": 0, "w": 80, "h": 40}, "position": {"x": 160, "y": 260}}
    ]


def test_frame_sidecar_record_preserves_slot_order_when_completed():
    """Completing the position slot keeps the caller's key order (spec chronology)."""
    frame = Frame(1000, 1000, collect_sidecar=True)
    img = Image.new("RGBA", (80, 40), (255, 0, 0, 255))
    record = {"class_type": "translation", "bbox": {"x": 0, "y": 0, "w": 80, "h": 40}, "position": None}
    frame.layer_at(img, ResolvedRect(left=0, top=0, width=80, height=40), sidecar_record=record)

    emitted = frame.sidecar_layers[0]
    assert list(emitted) == ["class_type", "bbox", "position"]
    assert emitted["position"] == {"x": 0, "y": 0}


def test_frame_sidecar_record_without_position_slot_passes_through():
    """A custom record without a position slot is appended unchanged."""
    frame = Frame(1000, 1000, collect_sidecar=True)
    img = Image.new("RGBA", (80, 40), (255, 0, 0, 255))
    record = {"class_type": "watermark", "text": "mark"}
    frame.layer_at(img, ResolvedRect(left=0, top=0, width=80, height=40), sidecar_record=record)

    assert frame.sidecar_layers == [{"class_type": "watermark", "text": "mark"}]


def test_frame_sidecar_record_position_matches_pixels():
    """A completed position must point at actual pasted pixels."""
    frame = Frame(1000, 1000, collect_sidecar=True)
    img = Image.new("RGBA", (80, 40), (255, 0, 0, 255))
    frame.layer_at(
        img,
        ResolvedRect(left=100, top=100, width=200, height=200),
        keep_bottom=True,
        sidecar_record={"class_type": "translation", "position": None},
    )

    pos = frame.sidecar_layers[0]["position"]
    assert frame.image.getpixel((pos["x"], pos["y"])) == (255, 0, 0, 255)


def test_frame_sidecar_no_record_no_image_node():
    """A custom record with no default node means no image node is emitted."""
    frame = Frame(1000, 1000, collect_sidecar=True)
    img = Image.new("RGBA", (80, 40), (255, 0, 0, 255))
    frame.layer_at(img, ResolvedRect(left=0, top=0, width=80, height=40), sidecar_record=None)

    assert frame.sidecar_layers == [{"class_type": "image", "x": 0, "y": 0, "w": 80, "h": 40}]


def test_frame_sidecar_layerable_records_own_node(word_config):
    """A Layerable emits its own node through the sink while collect_sidecar is on."""
    from quranmedialib.modules.vimage import VImage
    from quranmedialib.types import ResolvedRect, VerseConfig, WordItem

    verse_cfg = VerseConfig(word_spacing=0, row_spacing=0)
    word_img = Image.new("L", (100, 40), 255)
    items = [WordItem(image=word_img, text="Test", index=1)]
    vimg = VImage(items, verse_cfg, 500)
    rows, consumed = vimg.get_page_chunk(0, 10)

    frame = Frame(1000, 1000, collect_sidecar=True)
    frame.layer_at(
        vimg,
        ResolvedRect(left=0, top=0, width=500, height=200),
        word_config=word_config,
        rows_to_render=rows,
    )

    assert len(frame.sidecar_layers) == 1
    node = frame.sidecar_layers[0]
    assert node["class_type"] == "vimage"
    assert node["rows"][0]["words"][0]["class_type"] == "word"
    assert node["rows"][0]["words"][0]["index"] == 1


def test_frame_sidecar_custom_layerable_extension_contract():
    """A custom (non-VImage) Layerable self-describes through the sink, no sidecar.py changes."""
    from quranmedialib.types import ResolvedRect

    class StampLayerable:
        """Minimal Layerable: draws a stamp and emits its own node via sidecar_sink."""

        def layer(self, canvas, x, y, **kwargs):
            ImageDraw.Draw(canvas).rectangle((x, y, x + 40, y + 20), fill=(0, 128, 255, 255))
            sidecar_sink = kwargs.get("sidecar_sink")
            if sidecar_sink is not None:
                sidecar_sink({"class_type": "stamp", "x": x, "y": y, "w": 40, "h": 20})

    frame = Frame(1000, 1000, collect_sidecar=True)
    frame.layer_at(StampLayerable(), ResolvedRect(left=10, top=20, width=40, height=20))

    assert frame.sidecar_layers == [{"class_type": "stamp", "x": 10, "y": 20, "w": 40, "h": 20}]
    assert frame.image.getpixel((25, 30)) == (0, 128, 255, 255)


def test_frame_sidecar_custom_layerable_without_sink_no_node():
    """A Layerable that ignores sidecar_sink simply emits no node (opt-out)."""
    from quranmedialib.types import ResolvedRect

    class SilentLayerable:
        def layer(self, canvas, x, y, **kwargs):
            ImageDraw.Draw(canvas).rectangle((x, y, x + 10, y + 10), fill=(255, 0, 0, 255))

    frame = Frame(1000, 1000, collect_sidecar=True)
    frame.layer_at(SilentLayerable(), ResolvedRect(left=0, top=0, width=10, height=10))

    assert frame.sidecar_layers == []


def test_frame_sidecar_layerable_node_matches_pixels(word_config):
    """The vimage node box must cover the pixels actually drawn."""
    from quranmedialib.modules.vimage import VImage
    from quranmedialib.types import ResolvedRect, VerseConfig, WordItem

    verse_cfg = VerseConfig(word_spacing=0, row_spacing=0)
    word_img = Image.new("L", (100, 40), 255)
    items = [WordItem(image=word_img, text="Test", index=1)]
    vimg = VImage(items, verse_cfg, 500)
    rows, consumed = vimg.get_page_chunk(0, 10)

    frame = Frame(1000, 1000, collect_sidecar=True)
    frame.layer_at(
        vimg,
        ResolvedRect(left=0, top=0, width=500, height=200),
        word_config=word_config,
        rows_to_render=rows,
    )

    node = frame.sidecar_layers[0]
    assert frame.image.getpixel((node["x"], node["y"])) != (0, 0, 0, 0)
    assert frame.image.getpixel((node["x"] + node["w"] - 1, node["y"])) != (0, 0, 0, 0)
