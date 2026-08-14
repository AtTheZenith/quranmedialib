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

import json
from typing import Any

from quranmedialib.types import WordItem

# The schema contract version. Independent of the library version: bump only on
# universal-contract changes (key renames, coordinate semantics, page structure),
# never for type-declared metadata additions.
SIDECAR_SCHEMA = "spatial-1"

__all__ = ["SIDECAR_SCHEMA", "build_sidecar", "serialize_sidecar", "sidecar_filename"]


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
            words.append(_word_record(item, x, y, wbw.get(item.index)))
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

    Deterministic: keys are sorted and no timestamps are present, so the same
    input always produces byte-identical output.

    Args:
        sidecar: The sidecar document from :func:`build_sidecar`.

    Returns:
        str: The serialized JSON string.
    """
    return json.dumps(sidecar, ensure_ascii=False, sort_keys=True, indent=2)
