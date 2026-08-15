"""Tests for the spatial sidecar serializer."""

import json

from quranmedialib.modules.sidecar import (
    SIDECAR_SCHEMA,
    TASK_SCHEMA,
    build_sidecar,
    build_task_sidecar,
    serialize_sidecar,
    sidecar_filename,
)


def _flat_record(index: int, class_type: str, text: str, x: int, y: int, w: int = 50, h: int = 40) -> dict:
    """Build a flat word record exactly as VImage's sidecar sink emits it."""
    return {
        "index": index,
        "class_type": class_type,
        "text": text,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
    }


def _sample_vimage_layer():
    """Return a vimage layer node matching one rendered page, as the sink emits it."""
    return {
        "class_type": "vimage",
        "x": 15,
        "y": 0,
        "w": 110,
        "h": 100,
        "rows": [
            {
                "x": 15,
                "y": 0,
                "width": 110,
                "height": 40,
                "words": [
                    _flat_record(1, "word", "word1", 135, 0),
                    _flat_record(2, "word", "word2", 75, 0),
                ],
            },
            {
                "x": 15,
                "y": 60,
                "width": 50,
                "height": 40,
                "words": [_flat_record(0, "verse_number", "", 15, 60)],
            },
        ],
    }


def test_sidecar_filename():
    """sidecar_filename mirrors the page naming convention."""
    assert sidecar_filename(1) == "page_0001.json"
    assert sidecar_filename(12) == "page_0012.json"


def test_build_sidecar_shape():
    """build_sidecar emits the schema contract, identity, and layers hierarchy."""
    sidecar = build_sidecar(
        surah=2,
        ayah=255,
        page=1,
        dimensions=(1920, 1080),
        layers=[_sample_vimage_layer()],
    )

    assert sidecar["schema"] == SIDECAR_SCHEMA
    assert sidecar["surah"] == 2
    assert sidecar["ayah"] == 255
    assert sidecar["page"] == 1
    assert sidecar["dimensions"] == {"width": 1920, "height": 1080}
    assert len(sidecar["layers"]) == 1

    vimage = sidecar["layers"][0]
    assert vimage["class_type"] == "vimage"
    assert vimage["x"] == 15
    assert vimage["y"] == 0
    assert vimage["w"] == 110
    assert vimage["h"] == 100
    assert len(vimage["rows"]) == 2

    first_row = vimage["rows"][0]
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

    verse_number = vimage["rows"][1]["words"][0]
    assert verse_number["class_type"] == "verse_number"
    assert verse_number["index"] == 0
    assert verse_number["text"] == ""


def test_build_sidecar_includes_wbw_when_joined():
    """wbw joins onto the word record by WordIndex at emission."""
    sidecar = build_sidecar(
        surah=11,
        ayah=113,
        page=1,
        dimensions=(1920, 1080),
        layers=[_sample_vimage_layer()],
        wbw_by_index={1: "first", 2: "second"},
    )

    words = sidecar["layers"][0]["rows"][0]["words"]
    assert words[0]["wbw"] == "first"
    assert words[1]["wbw"] == "second"
    # The verse number marker carries no wbw.
    assert "wbw" not in sidecar["layers"][0]["rows"][1]["words"][0]


def test_build_sidecar_includes_translation_layer():
    """A translation paragraph contributes one layer node with its text."""
    translation_geo = {
        "class_type": "translation",
        "bbox": {"x": 0, "y": 0, "w": 1500, "h": 120},
        "position": {"x": 200, "y": 900},
        "exceeded_bounds": False,
        "text": "Allah - there is no deity except Him, the Ever-Living.",
    }
    sidecar = build_sidecar(
        surah=2,
        ayah=255,
        page=1,
        dimensions=(1920, 1080),
        layers=[_sample_vimage_layer(), translation_geo],
    )

    assert len(sidecar["layers"]) == 2
    assert sidecar["layers"][1] == translation_geo
    assert sidecar["layers"][1]["text"].startswith("Allah - there is no deity")


def test_serialize_sidecar_is_deterministic():
    """Serialization must be byte-identical for identical input, in chronological key order."""
    sidecar = build_sidecar(
        surah=2,
        ayah=255,
        page=1,
        dimensions=(1920, 1080),
        layers=[_sample_vimage_layer()],
    )

    serialized_1 = serialize_sidecar(sidecar)
    serialized_2 = serialize_sidecar(sidecar)
    assert serialized_1 == serialized_2

    # Keys are emitted in chronological insertion order (spec contract), not sorted.
    parsed = json.loads(serialized_1)
    assert list(parsed) == list(sidecar)
    assert list(parsed) == ["schema", "surah", "ayah", "page", "dimensions", "layers"]
    assert parsed["schema"] == SIDECAR_SCHEMA


def test_serialize_sidecar_preserves_arabic():
    """Arabic text must serialize as UTF-8, not \\u escapes."""
    layer = {
        "class_type": "vimage",
        "x": 10,
        "y": 0,
        "w": 50,
        "h": 40,
        "rows": [{"x": 10, "y": 0, "width": 50, "height": 40, "words": [_flat_record(1, "word", "الله", 10, 0)]}],
    }
    sidecar = build_sidecar(
        surah=11,
        ayah=113,
        page=1,
        dimensions=(1920, 1080),
        layers=[layer],
    )

    serialized = serialize_sidecar(sidecar)
    assert "الله" in serialized
    assert "\\u" not in serialized


def test_combined_batch_expands_to_one_record_per_source_word():
    """A combined batch (consecutive words sharing wbw) emits one record per source word."""
    layer = {
        "class_type": "vimage",
        "x": 100,
        "y": 20,
        "w": 150,
        "h": 40,
        "rows": [
            {
                "x": 100,
                "y": 20,
                "width": 150,
                "height": 40,
                "words": [_flat_record(10, "word", "من دون الله", 100, 20, 150, 40)],
            }
        ],
    }
    sidecar = build_sidecar(
        surah=11,
        ayah=113,
        page=1,
        dimensions=(1920, 1080),
        layers=[layer],
        wbw_by_index={10: "besides allah", 11: "besides allah", 12: "besides allah"},
    )

    words = sidecar["layers"][0]["rows"][0]["words"]
    assert len(words) == 3
    assert [w["index"] for w in words] == [10, 11, 12]
    assert [w["text"] for w in words] == ["من", "دون", "الله"]
    assert all(w["wbw"] == "besides allah" for w in words)
    # All source words share the batch's pixel box.
    assert all((w["x"], w["y"], w["w"], w["h"]) == (100, 20, 150, 40) for w in words)


def test_combined_batch_omits_wbw_when_not_joined():
    """Expanded batch records omit wbw when no join map is supplied."""
    layer = {
        "class_type": "vimage",
        "x": 100,
        "y": 20,
        "w": 150,
        "h": 40,
        "rows": [
            {
                "x": 100,
                "y": 20,
                "width": 150,
                "height": 40,
                "words": [_flat_record(10, "word", "من دون الله", 100, 20, 150, 40)],
            }
        ],
    }
    sidecar = build_sidecar(
        surah=11,
        ayah=113,
        page=1,
        dimensions=(1920, 1080),
        layers=[layer],
    )

    words = sidecar["layers"][0]["rows"][0]["words"]
    assert len(words) == 3
    assert all("wbw" not in w for w in words)


def test_build_task_sidecar_shape():
    """task sidecar records identity, configs, database, and fonts."""
    from quranmedialib.presets import DATABASE_EN_SAHIH, DATABASE_QURAN, DATABASE_WBW_EN, LANDSCAPE_PRESET

    preset = LANDSCAPE_PRESET["default"]["1080p"]
    db_configs = {
        "quran": DATABASE_QURAN,
        "wbw": DATABASE_WBW_EN,
        "translation": DATABASE_EN_SAHIH,
    }

    task = build_task_sidecar(
        workflow="surah",
        surah=108,
        start_ayah=1,
        end_ayah=3,
        annotate=True,
        separate_translations=False,
        parallel=True,
        frame_cfg=preset.frame,
        word_cfg=preset.word,
        verse_cfg=preset.verse,
        text_cfg=preset.text,
        database_configs=db_configs,
    )

    assert task["schema"] == TASK_SCHEMA
    assert task["workflow"] == "surah"
    assert task["surah"] == 108
    assert task["ayah_range"] == {"start": 1, "end": 3}
    assert task["annotate"] is True
    assert task["separate_translations"] is False
    assert task["parallel"] is True
    assert task["mode"] == "default"
    assert task["aspect_ratio"] == "landscape"
    assert task["resolution"] == "1080p"
    assert task["config"]["frame"]["image_height"] == 1080
    assert task["config"]["word"]["font_size"] == preset.word.font_size
    assert set(task["database"][0]) == {"name", "filepath"}
    assert any(f["role"] == "word" for f in task["fonts"])
    assert len(task["database"]) == 3


def test_build_task_sidecar_is_deterministic():
    """Serialized task sidecar is byte-identical for identical input."""
    import json as jsonlib

    from quranmedialib.presets import DATABASE_QURAN, LANDSCAPE_PRESET

    preset = LANDSCAPE_PRESET["default"]["1080p"]
    db_configs = {"quran": DATABASE_QURAN}

    task = build_task_sidecar(
        workflow="verse_range",
        surah=2,
        start_ayah=255,
        end_ayah=256,
        annotate=True,
        separate_translations=True,
        parallel=False,
        frame_cfg=preset.frame,
        word_cfg=preset.word,
        verse_cfg=preset.verse,
        text_cfg=preset.text,
        database_configs=db_configs,
    )

    serialized_1 = serialize_sidecar(task)
    serialized_2 = serialize_sidecar(task)
    assert serialized_1 == serialized_2
    assert jsonlib.loads(serialized_1)["schema"] == TASK_SCHEMA
