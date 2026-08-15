"""Spatial sidecar serialization for QuranMediaLib.

The sidecar is a per-page JSON document that records the resolved geometry of
every content element on that page (Arabic word rows, the translation paragraph)
straight from the renderer's own layout state, so geometry agrees with pixels by
construction. It is machine-readable input for external agents that edit layout
parameters and re-invoke the deterministic render.

The spec defines the schema contract (``spatial-1``); this module is the single
emission point. See the v5 spatial sidecar specification in the master vault.
"""

from __future__ import annotations

import dataclasses
import json
from enum import Enum
from pathlib import Path
from typing import Any

from quranmedialib.types import DatabaseConfig, FontResource, Padding, WordItem

# The schema contract version. Independent of the library version: bump only on
# universal-contract changes (key renames, coordinate semantics, page structure),
# never for type-declared metadata additions.
SIDECAR_SCHEMA = "spatial-1"

# The per-task record schema. Documents the process that produced a page set
# (identity + configs + resources). Documentation only — never hashed by the
# validation harness, which reads only per-page sidecar siblings.
TASK_SCHEMA = "task-1"

__all__ = [
    "SIDECAR_SCHEMA",
    "TASK_SCHEMA",
    "build_sidecar",
    "build_task_sidecar",
    "serialize_sidecar",
    "sidecar_filename",
]


def sidecar_filename(page_num: int) -> str:
    """Return the JSON sidecar filename for a page, mirroring the page naming.

    Args:
        page_num: 1-based page number.

    Returns:
        str: The sidecar filename, e.g. ``page_0001.json``.
    """
    return f"page_{page_num:04d}.json"


def _word_record(item: WordItem, x: int, y: int, wbw: str | None) -> dict[str, Any]:
    """Build the sidecar record for a single word item.

    Args:
        item: The WordItem placed on the page.
        x: Absolute page x of the word's top-left corner.
        y: Absolute page y of the word's top-left corner.
        wbw: Word-by-word translation for this word, if known.

    Returns:
        dict[str, Any]: The word record.
    """
    record: dict[str, Any] = {
        "index": item.index,
        "class_type": item.class_type,
        "text": item.text or "",
        "x": x,
        "y": y,
        "w": item.width,
        "h": item.height,
    }
    if wbw is not None:
        record["wbw"] = wbw
    return record


def _word_records(item: WordItem, x: int, y: int, wbw_by_index: dict[int, str]) -> list[dict[str, Any]]:
    """Build the sidecar records for a word item, expanding combined batches.

    A wimage whose text carries multiple whitespace-separated words is a
    combined annotation batch (consecutive words sharing the same wbw string,
    e.g. ``من دون الله``). The sidecar must emit one record per source word —
    each with its own ``index``, ``text``, and ``wbw`` — all sharing the batch's
    pixel box, so word records map 1:1 onto the wbw database keys.

    Args:
        item: The WordItem placed on the page.
        x: Absolute page x of the top-left corner (shared by all batch words).
        y: Absolute page y of the top-left corner (shared by all batch words).
        wbw_by_index: Map of word index to its word-by-word translation.

    Returns:
        list[dict[str, Any]]: One record for a single word or verse number, or
            one record per source word for a combined batch.
    """
    if item.class_type != "word":
        return [_word_record(item, x, y, wbw_by_index.get(item.index))]
    words = (item.text or "").split()
    if len(words) <= 1:
        return [_word_record(item, x, y, wbw_by_index.get(item.index))]

    records = []
    for offset, word_text in enumerate(words):
        index = item.index + offset
        record = {
            "index": index,
            "class_type": "word",
            "text": word_text,
            "x": x,
            "y": y,
            "w": item.width,
            "h": item.height,
        }
        wbw = wbw_by_index.get(index)
        if wbw is not None:
            record["wbw"] = wbw
        records.append(record)
    return records


def build_sidecar(
    surah: int,
    ayah: int,
    page: int,
    dimensions: tuple[int, int],
    rows: list[tuple[list[WordItem], int, int]],
    translation_geo: dict[str, Any] | None,
    word_items_with_geometry: list[tuple[WordItem, int, int]],
    wbw_by_index: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Build the spatial sidecar document for one rendered page.

    Args:
        surah: Surah number (1-114).
        ayah: Ayah number (1-286).
        page: 1-based page number within the verse.
        dimensions: (width, height) of the page canvas in pixels.
        rows: The VImage row structure — list of (word_items, row_width, row_height).
        translation_geo: Optional translation paragraph geometry with ``bbox``,
            ``position``, and ``exceeded_bounds`` keys; None when no translation
            was placed on this page.
        word_items_with_geometry: Flat list of (item, x, y) captured from the
            VImage geometry sink, in placement order.
        wbw_by_index: Optional map of word index to its word-by-word translation,
            joined by WordIndex at emission.

    Returns:
        dict[str, Any]: The sidecar document (schema, identity, dimensions, rows,
            and the optional translation record).
    """
    geo_by_id = {id(item): (x, y) for item, x, y in word_items_with_geometry}
    wbw = wbw_by_index or {}

    row_records: list[dict[str, Any]] = []
    for row_items, row_width, row_height in rows:
        words = []
        for item in row_items:
            x, y = geo_by_id.get(id(item), (0, 0))
            words.extend(_word_records(item, x, y, wbw))
        row_records.append(
            {
                "width": row_width,
                "height": row_height,
                "words": words,
            }
        )

    sidecar: dict[str, Any] = {
        "schema": SIDECAR_SCHEMA,
        "surah": surah,
        "ayah": ayah,
        "page": page,
        "dimensions": {"width": dimensions[0], "height": dimensions[1]},
        "rows": row_records,
    }
    if translation_geo is not None:
        sidecar["translation"] = translation_geo
    return sidecar


def serialize_sidecar(sidecar: dict[str, Any]) -> str:
    """Serialize a sidecar document to deterministic JSON.

    Deterministic: keys are emitted in insertion order (the builders construct
    in chronological schema order) and no timestamps are present, so the same
    input always produces byte-identical output. Sorted-key reordering is
    intentionally not applied — chronological order is the spec contract.

    Args:
        sidecar: The sidecar document from :func:`build_sidecar`.

    Returns:
        str: The serialized JSON string.
    """
    return json.dumps(sidecar, ensure_ascii=False, indent=2)


def _config_value(value: Any) -> Any:
    """Convert a config field value to a JSON-safe representation.

    Handles Path, FontResource, Padding, enum members, and color tuples. Used by
    :func:`_config_to_dict` to serialize frozen config dataclasses for the
    per-task sidecar.

    Args:
        value: A config field value.

    Returns:
        JSON-safe value (str, int, float, bool, None, list, or dict).
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, FontResource):
        return {"name": value.name, "path": str(value.path)}
    if isinstance(value, Padding):
        return {"top": value.top, "bottom": value.bottom, "left": value.left, "right": value.right}
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, tuple):
        return list(value)
    if dataclasses.is_dataclass(value):
        return _config_to_dict(value)
    return str(value)


def _config_to_dict(config: Any) -> dict[str, Any]:
    """Serialize a frozen config dataclass to a JSON-safe dict.

    Args:
        config: A frozen dataclass config (FrameConfig, WordConfig, etc.).

    Returns:
        dict[str, Any]: Field name to JSON-safe value.
    """
    return {field.name: _config_value(getattr(config, field.name)) for field in dataclasses.fields(config)}


def _font_records(
    word_cfg: Any,
    text_cfg: Any,
) -> list[dict[str, str]]:
    """Collect the fonts referenced by the word and text configs.

    Args:
        word_cfg: WordConfig (font, annotation font path).
        text_cfg: TextConfig (regular, italic, highlight font paths).

    Returns:
        list[dict[str, str]]: Font records with ``role``, ``name``, and ``path``.
    """
    records: list[dict[str, str]] = []
    candidates: list[tuple[str, Path | FontResource | None]] = [
        ("word", word_cfg.font),
        ("annotation", word_cfg.annotation_font_path),
        ("translation", text_cfg.font_path),
        ("translation_italic", text_cfg.italic_font_path),
        ("translation_highlight", text_cfg.highlight_font_path),
    ]
    for role, resource in candidates:
        if isinstance(resource, FontResource):
            records.append({"role": role, "name": resource.name, "path": str(resource.path)})
        elif isinstance(resource, Path):
            records.append({"role": role, "name": resource.stem, "path": str(resource)})
    return records


def build_task_sidecar(
    workflow: str,
    surah: int,
    start_ayah: int,
    end_ayah: int,
    annotate: bool,
    separate_translations: bool,
    parallel: bool,
    frame_cfg: Any,
    word_cfg: Any,
    verse_cfg: Any,
    text_cfg: Any,
    database_configs: dict[str, DatabaseConfig],
) -> dict[str, Any]:
    """Build the per-task sidecar documenting the process that produced a page set.

    Emitted once per render task (``task.json`` at the output_dir root) when
    ``emit_sidecar=True``. Records identity, the resolved configs, and the
    database/font resources used — so an agent or human auditing a page set can
    reproduce or adjust it without re-deriving parameters from the API.

    This record is documentation, not a validation contract: absolute paths are
    expected (machine-specific), and the harness hashes only per-page sidecars.

    Args:
        workflow: Workflow type, ``"surah"`` or ``"verse_range"``.
        surah: Surah number (1-114).
        start_ayah: First ayah rendered (inclusive).
        end_ayah: Last ayah rendered (inclusive).
        annotate: Whether word-by-word annotations were rendered.
        separate_translations: Whether translations were rendered on separate pages.
        parallel: Whether parallel processing was used.
        frame_cfg: FrameConfig used for the render.
        word_cfg: WordConfig used for the render.
        verse_cfg: VerseConfig used for the render.
        text_cfg: TextConfig used for the render.
        database_configs: Registered database configs keyed by connection name.

    Returns:
        dict[str, Any]: The task-1 sidecar document.
    """
    resolution = f"{frame_cfg.image_height}p"
    return {
        "schema": TASK_SCHEMA,
        "workflow": workflow,
        "surah": surah,
        "ayah_range": {"start": start_ayah, "end": end_ayah},
        "annotate": annotate,
        "separate_translations": separate_translations,
        "parallel": parallel,
        "mode": frame_cfg.mode,
        "aspect_ratio": frame_cfg.aspect_ratio,
        "resolution": resolution,
        "config": {
            "frame": _config_to_dict(frame_cfg),
            "word": _config_to_dict(word_cfg),
            "verse": _config_to_dict(verse_cfg),
            "text": _config_to_dict(text_cfg),
        },
        "database": [
            {"name": name, "filepath": str(config.filepath)}
            for name, config in sorted(database_configs.items())
        ],
        "fonts": _font_records(word_cfg, text_cfg),
    }
