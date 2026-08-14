"""Tests for the spatial sidecar serializer."""

import json

from PIL import Image

from quranmedialib.modules.sidecar import (
    SIDECAR_SCHEMA,
    build_sidecar,
    serialize_sidecar,
    sidecar_filename,
)
from quranmedialib.types import WordItem


def _word(text: str, index: int, width: int = 50, height: int = 40, class_type: str = "word") -> WordItem:
    """Helper to build a WordItem with a solid dummy image."""
    img = Image.new("L", (width, height), 255)
    return WordItem(image=img, text=text, index=index, class_type=class_type)


def _sample_rows_and_geometry():
    """Return a small row structure plus matching geometry, mirroring one page."""
    w1 = _word("word1", 1)
    w2 = _word("word2", 2)
    w3 = _word("", 0, class_type="verse_number")
    rows = [([w1, w2], 110, 40), ([w3], 50, 40)]
    geometry = [
        (w1, 135, 0),
        (w2, 75, 0),
        (w3, 15, 60),
    ]
    return rows, geometry


def test_sidecar_filename():
    """sidecar_filename mirrors the page naming convention."""
    assert sidecar_filename(1) == "page_0001.json"
    assert sidecar_filename(12) == "page_0012.json"


def test_build_sidecar_shape():
    """build_sidecar emits the schema contract, identity, and rows hierarchy."""
    rows, geometry = _sample_rows_and_geometry()
    sidecar = build_sidecar(
        surah=2,
        ayah=255,
        page=1,
        dimensions=(1920, 1080),
        rows=rows,
        translation_geo=None,
        word_items_with_geometry=geometry,
    )

    assert sidecar["schema"] == SIDECAR_SCHEMA
    assert sidecar["surah"] == 2
    assert sidecar["ayah"] == 255
    assert sidecar["page"] == 1
    assert sidecar["dimensions"] == {"width": 1920, "height": 1080}
    assert len(sidecar["rows"]) == 2

    first_row = sidecar["rows"][0]
    assert first_row["width"] == 110
    assert first_row["height"] == 40
    assert len(first_row["words"]) == 2

    first_word = first_row["words"][0]
    assert first_word["index"] == 1
    assert first_word["class_type"] == "word"
    assert first_word["text"] == "word1"
    assert first_word["x"] == 135
    assert first_word["y"] == 0
    assert first_word["w"] == 50
    assert first_word["h"] == 40

    verse_number = sidecar["rows"][1]["words"][0]
    assert verse_number["class_type"] == "verse_number"
    assert verse_number["index"] == 0
    assert verse_number["text"] == ""


def test_build_sidecar_includes_wbw_when_joined():
    """wbw joins onto the word record by WordIndex at emission."""
    rows, geometry = _sample_rows_and_geometry()
    sidecar = build_sidecar(
        surah=11,
        ayah=113,
        page=1,
        dimensions=(1920, 1080),
        rows=rows,
        translation_geo=None,
        word_items_with_geometry=geometry,
        wbw_by_index={1: "first", 2: "second"},
    )

    words = sidecar["rows"][0]["words"]
    assert words[0]["wbw"] == "first"
    assert words[1]["wbw"] == "second"
    # The verse number marker carries no wbw.
    assert "wbw" not in sidecar["rows"][1]["words"][0]


def test_build_sidecar_includes_translation_geo():
    """A translation paragraph contributes one page-level record."""
    rows, geometry = _sample_rows_and_geometry()
    translation_geo = {
        "bbox": {"x": 0, "y": 0, "w": 1500, "h": 120},
        "position": {"x": 200, "y": 900},
        "exceeded_bounds": False,
    }
    sidecar = build_sidecar(
        surah=2,
        ayah=255,
        page=1,
        dimensions=(1920, 1080),
        rows=rows,
        translation_geo=translation_geo,
        word_items_with_geometry=geometry,
    )

    assert sidecar["translation"] == translation_geo


def test_serialize_sidecar_is_deterministic():
    """Serialization must be byte-identical for identical input, sorted keys."""
    rows, geometry = _sample_rows_and_geometry()
    sidecar = build_sidecar(
        surah=2,
        ayah=255,
        page=1,
        dimensions=(1920, 1080),
        rows=rows,
        translation_geo=None,
        word_items_with_geometry=geometry,
    )

    serialized_1 = serialize_sidecar(sidecar)
    serialized_2 = serialize_sidecar(sidecar)
    assert serialized_1 == serialized_2

    # Deterministic independent of dict insertion order.
    reordered = {k: sidecar[k] for k in reversed(list(sidecar))}
    assert serialize_sidecar(reordered) == serialized_1

    parsed = json.loads(serialized_1)
    assert parsed["schema"] == SIDECAR_SCHEMA


def test_serialize_sidecar_preserves_arabic():
    """Arabic text must serialize as UTF-8, not \\u escapes."""
    img = Image.new("L", (50, 40), 255)
    item = WordItem(image=img, text="الله", index=1)
    sidecar = build_sidecar(
        surah=11,
        ayah=113,
        page=1,
        dimensions=(1920, 1080),
        rows=[([item], 50, 40)],
        translation_geo=None,
        word_items_with_geometry=[(item, 10, 0)],
    )

    serialized = serialize_sidecar(sidecar)
    assert "الله" in serialized
    assert "\\u" not in serialized


def test_combined_batch_expands_to_one_record_per_source_word():
    """A combined batch (consecutive words sharing wbw) emits one record per source word."""
    img = Image.new("L", (150, 40), 255)
    item = WordItem(image=img, text="من دون الله", index=10)
    sidecar = build_sidecar(
        surah=11,
        ayah=113,
        page=1,
        dimensions=(1920, 1080),
        rows=[([item], 150, 40)],
        translation_geo=None,
        word_items_with_geometry=[(item, 100, 20)],
        wbw_by_index={10: "besides allah", 11: "besides allah", 12: "besides allah"},
    )

    words = sidecar["rows"][0]["words"]
    assert len(words) == 3
    assert [w["index"] for w in words] == [10, 11, 12]
    assert [w["text"] for w in words] == ["من", "دون", "الله"]
    assert all(w["wbw"] == "besides allah" for w in words)
    # All source words share the batch's pixel box.
    assert all((w["x"], w["y"], w["w"], w["h"]) == (100, 20, 150, 40) for w in words)


def test_combined_batch_omits_wbw_when_not_joined():
    """Expanded batch records omit wbw when no join map is supplied."""
    img = Image.new("L", (150, 40), 255)
    item = WordItem(image=img, text="من دون الله", index=10)
    sidecar = build_sidecar(
        surah=11,
        ayah=113,
        page=1,
        dimensions=(1920, 1080),
        rows=[([item], 150, 40)],
        translation_geo=None,
        word_items_with_geometry=[(item, 100, 20)],
    )

    words = sidecar["rows"][0]["words"]
    assert len(words) == 3
    assert all("wbw" not in w for w in words)