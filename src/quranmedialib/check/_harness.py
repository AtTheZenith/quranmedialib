"""QuranMediaLib check module — the single source of truth for rendering correctness.

Backward compatibility guarantee: once a version's reference directory is
created (references/v<X.Y.Z>/), it will always be loadable by future versions
of this module. New scenarios may be appended; existing scenario definitions
in already-released versions are never modified.

Usage:
    python -m quranmedialib.check test       # Full suite: pixel compare + unit tests
    python -m quranmedialib.check update     # (Re)generate reference images + perf data
    python -m quranmedialib.check list       # List canonical scenarios
    python -m quranmedialib.check compare    # Cross-version pixel comparison
    python -m quranmedialib.check run        # Quick pixel validation only
    python -m quranmedialib.check benchmark  # Run performance benchmarks
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

from quranmedialib import (
    LANDSCAPE_PRESET,
    SQUARE_PRESET,
    STORY_PRESET,
    DatabaseManager,
    IsolateWordsWorkflow,
    Preset,
    SurahWorkflow,
    VerseRangeWorkflow,
    VerseWorkflow,
)
from quranmedialib import __version__ as qml_version
from quranmedialib.modules.image import color, glow, pad
from quranmedialib.modules.timage import get_timage
from quranmedialib.modules.vimage import QURANIC_STOP_SIGNS, VImage
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import Padding, VerseConfig, WordItem

type Aspect = str
type Mode = str
type Resolution = str
type WorkflowType = str


# ── Performance helpers ──────────────────────────────────────────────────────


def _get_memory_mb() -> float:
    """Return current process RSS in MB, or 0.0 if psutil unavailable."""
    try:
        import psutil

        return psutil.Process().memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0


def _compute_pixel_hash(pages: list[Image.Image]) -> str:
    """SHA-256 of concatenated raw pixel data across all pages."""
    h = hashlib.sha256()
    for p in pages:
        h.update(p.tobytes())
    return f"sha256:{h.hexdigest()}"


# ── Types ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Scenario:
    """An immutable, unchanging validation scenario.

    Once added to CANONICAL_SCENARIOS the definition MUST NOT be altered.
    New scenarios may only be appended.
    """

    name: str
    aspect: Aspect
    mode: Mode
    resolution: Resolution
    workflow_type: WorkflowType
    params: dict[str, Any]
    expected_pages: int


@dataclass(slots=True)
class PageDiff:
    """Per-page pixel-diff details."""

    page: int
    diff_pixels: int
    total_pixels: int
    diff_percent: float
    size_match: bool
    bbox: list[int] | None = None


@dataclass(slots=True)
class ScenarioMetrics:
    """Performance metrics for a single scenario render."""

    name: str
    elapsed_s: float
    pages: int
    peak_rss_mb: float
    pixel_hash: str


@dataclass(slots=True)
class ValidationResult:
    """Result of validating a single scenario."""

    scenario: str
    passed: bool
    pages_expected: int
    pages_actual: int
    page_diffs: list[PageDiff] | None = None
    metrics: ScenarioMetrics | None = None
    error: str | None = None
    elapsed: float = 0.0


@dataclass(slots=True)
class CrossVersionScenarioDiff:
    """Per-scenario diff between two versions."""

    scenario: str
    match: bool
    max_diff_percent: float
    pages_a: int
    pages_b: int
    details: list[PageDiff] | None = None


@dataclass(slots=True)
class CrossVersionReport:
    """Result of comparing two version's reference sets."""

    version_a: str
    version_b: str
    common: list[CrossVersionScenarioDiff]
    only_in_a: list[str]
    only_in_b: list[str]
    all_match: bool


# ── Canonical Scenarios ──────────────────────────────────────────────────────
# Scenarios are ordered intentionally. New scenarios MUST be appended.

CANONICAL_SCENARIOS: list[Scenario] = [
    # ── Single-verse landscape ────────────────────────────────────────────
    Scenario(
        name="bismillah_annotated",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 1,
            "ayah": 1,
            "translations": ["In the name of Allah, the Most Gracious, the Most Merciful."],
            "annotate": True,
        },
        expected_pages=1,
    ),
    Scenario(
        name="bismillah_arabic",
        aspect="landscape",
        mode="arabic",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 1,
            "ayah": 1,
            "translations": [],
            "annotate": False,
        },
        expected_pages=1,
    ),
    Scenario(
        name="kawthar_annotated",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 108,
            "ayah": 1,
            "translations": ["Indeed, We have granted you, [O Muhammad], al-Kawthar."],
            "annotate": True,
        },
        expected_pages=1,
    ),
    Scenario(
        name="ikhlas_v1_annotated",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 112,
            "ayah": 1,
            "translations": ["Say, He is Allah, [who is] One,"],
            "annotate": True,
        },
        expected_pages=1,
    ),
    Scenario(
        name="kursi_partial",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 2,
            "ayah": 255,
            "translations": ["Allah! There is no deity except Him, the Ever-Living, the Self-Sustaining."],
            "annotate": True,
        },
        expected_pages=3,
    ),
    # ── Single-verse story / square ───────────────────────────────────────
    Scenario(
        name="bismillah_story",
        aspect="story",
        mode="default",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 1,
            "ayah": 1,
            "translations": [],
            "annotate": True,
        },
        expected_pages=1,
    ),
    Scenario(
        name="bismillah_square",
        aspect="square",
        mode="default",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 1,
            "ayah": 1,
            "translations": [],
            "annotate": True,
        },
        expected_pages=1,
    ),
    # ── Cross-resolution ──────────────────────────────────────────────────
    Scenario(
        name="bismillah_720p",
        aspect="landscape",
        mode="default",
        resolution="720p",
        workflow_type="verse",
        params={
            "surah": 1,
            "ayah": 1,
            "translations": ["In the name of Allah, the Most Gracious, the Most Merciful."],
            "annotate": True,
        },
        expected_pages=1,
    ),
    # ── Multi-page ────────────────────────────────────────────────────────
    Scenario(
        name="kursi_full",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 2,
            "ayah": 255,
            "translations": [
                "Allah! There is no deity except Him, the Ever-Living, the Self-Sustaining. "
                "Neither drowsiness nor sleep overtakes Him. To Him belongs whatever is in the "
                "heavens and whatever is on the earth. Who is it that can intercede with Him "
                "except by His permission? He knows what is before them and what will be after them, "
                "and they encompass not a thing of His knowledge except for what He wills. "
                "His Kursi extends over the heavens and the earth, and their preservation tires "
                "Him not. And He is the Most High, the Most Great."
            ],
            "annotate": True,
        },
        expected_pages=3,
    ),
    # ── SurahWorkflow ─────────────────────────────────────────────────────
    Scenario(
        name="surah_kawthar",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="surah",
        params={
            "surah": 108,
            "annotate": True,
            "separate_translations": False,
        },
        expected_pages=3,
    ),
    Scenario(
        name="surah_ikhlas",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="surah",
        params={
            "surah": 112,
            "annotate": True,
            "separate_translations": False,
        },
        expected_pages=4,
    ),
    # ── VerseRangeWorkflow ────────────────────────────────────────────────
    Scenario(
        name="range_kawthar",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="verse_range",
        params={
            "surah": 108,
            "start_ayah": 1,
            "end_ayah": 3,
            "annotate": True,
        },
        expected_pages=3,
    ),
    # ── IsolateWordsWorkflow ──────────────────────────────────────────────
    Scenario(
        name="isolate_kawthar_v1",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="isolate",
        params={
            "surah": 108,
            "ayah": 1,
            "annotate": True,
        },
        expected_pages=4,
    ),
    # ── SurahWorkflow with separate translations ──────────────────────────
    Scenario(
        name="surah_kawthar_separate",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="surah",
        params={
            "surah": 108,
            "annotate": True,
            "separate_translations": True,
        },
        expected_pages=6,
    ),
    # ── Full surah stress test (longest surah, 286 verses) ───────────
    Scenario(
        name="surah_albaqarah",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="surah",
        params={
            "surah": 2,
            "annotate": True,
            "separate_translations": False,
        },
        expected_pages=473,
    ),
    # ── Module-level: get_wimage ───────────────────────────────────────────
    Scenario(
        name="wimage_bismillah",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={"module": "wimage", "text": "بِسْمِ"},
        expected_pages=1,
    ),
    Scenario(
        name="wimage_allah",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={"module": "wimage", "text": "الله"},
        expected_pages=1,
    ),
    # ── Module-level: get_timage ───────────────────────────────────────────
    Scenario(
        name="timage_simple",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={"module": "timage", "text": "In the name of Allah, the Most Gracious, the Most Merciful."},
        expected_pages=1,
    ),
    Scenario(
        name="timage_rich",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={"module": "timage", "text": "#b#ffffffff#Bold# and #b#ff0000ff#Red# text"},
        expected_pages=1,
    ),
    # Granular style variants (unit-tested in test_timage.py) promoted to
    # absolute golden refs so `compare` attributes pixel changes precisely.
    Scenario(
        name="timage_styles_italic",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={"module": "timage", "text": "#i#00ff00ff#Italic Green# text"},
        expected_pages=1,
    ),
    Scenario(
        name="timage_styles_bolditalic",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={"module": "timage", "text": "#bi#0000ffff#Bold Italic Blue# text"},
        expected_pages=1,
    ),
    Scenario(
        name="timage_color_six",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={"module": "timage", "text": "#b#ff0000#Red 6-digit# text"},
        expected_pages=1,
    ),
    # ── Module-level: VImage ───────────────────────────────────────────────
    Scenario(
        name="vimage_layout_simple",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={
            "module": "vimage",
            "items": [("W1", 50, 40), ("W2", 60, 40)],
            "content_width": 200,
            "word_spacing": 10,
            "row_spacing": 20,
            "balanced": False,
        },
        expected_pages=1,
    ),
    Scenario(
        name="vimage_layout_balanced",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={
            "module": "vimage",
            "items": [("W1", 40, 40), ("W2", 40, 40), ("W3", 40, 40), ("W4", 40, 40), ("W5", 40, 40)],
            "content_width": 150,
            "word_spacing": 10,
            "row_spacing": 20,
            "balanced": True,
        },
        expected_pages=1,
    ),
    # ── Aspect x mode parity combos (v4.1.1) ─────────────────────────────
    Scenario(
        name="bismillah_translation",
        aspect="landscape",
        mode="translation",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 1,
            "ayah": 1,
            "translations": ["In the name of Allah, the Most Gracious, the Most Merciful."],
            "annotate": False,
        },
        expected_pages=1,
    ),
    Scenario(
        name="bismillah_story_arabic",
        aspect="story",
        mode="arabic",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 1,
            "ayah": 1,
            "translations": [],
            "annotate": False,
        },
        expected_pages=1,
    ),
    Scenario(
        name="bismillah_story_translation",
        aspect="story",
        mode="translation",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 1,
            "ayah": 1,
            "translations": ["In the name of Allah, the Most Gracious, the Most Merciful."],
            "annotate": False,
        },
        expected_pages=1,
    ),
    Scenario(
        name="bismillah_square_arabic",
        aspect="square",
        mode="arabic",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 1,
            "ayah": 1,
            "translations": [],
            "annotate": False,
        },
        expected_pages=1,
    ),
    Scenario(
        name="bismillah_square_translation",
        aspect="square",
        mode="translation",
        resolution="1080p",
        workflow_type="verse",
        params={
            "surah": 1,
            "ayah": 1,
            "translations": ["In the name of Allah, the Most Gracious, the Most Merciful."],
            "annotate": False,
        },
        expected_pages=1,
    ),
    # ── Module-level: image primitives (color / pad / glow) ────────────────
    # Cover the standalone utility functions in modules/image.py, which have
    # no call sites in the render pipeline and previously had zero golden refs.
    Scenario(
        name="image_color",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={
            "module": "image",
            "op": "color",
            "text": "الله",
            "color": (255, 215, 0, 255),
        },
        expected_pages=1,
    ),
    Scenario(
        name="image_pad",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={
            "module": "image",
            "op": "pad",
            "text": "بِسْمِ",
            "padding": [20, 20, 20, 20],
            "color": (0, 0, 0, 0),
        },
        expected_pages=1,
    ),
    Scenario(
        name="image_glow_default",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={
            "module": "image",
            "op": "glow",
            "text": "الله",
            "strength": 1.0,
            "radius": 50,
            "quality": "balanced",
        },
        expected_pages=1,
    ),
    Scenario(
        name="image_glow_quality",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={
            "module": "image",
            "op": "glow_quality",
            "text": "الله",
            "strength": 1.5,
            "radius": 30,
        },
        expected_pages=3,
    ),
    Scenario(
        name="image_glow_comparison",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={
            "module": "image",
            "op": "glow_comparison",
            "text": "الله",
            "strength": 1.0,
            "radius": 50,
        },
        expected_pages=1,
    ),
    # ── Module-level: VImage Quranic stop-sign page breaks ─────────────────
    # W3 carries a stop sign, so a 2-row page pulls the break back to W3
    # (instead of greedy W4). Removing the stop-sign logic changes pixels.
    Scenario(
        name="vimage_stop_signs",
        aspect="landscape",
        mode="default",
        resolution="1080p",
        workflow_type="module",
        params={
            "module": "vimage",
            "items": [
                ("W1", 50, 40),
                ("W2", 50, 40),
                (f"W3{QURANIC_STOP_SIGNS[0]}", 50, 40),
                ("W4", 50, 40),
                ("W5", 50, 40),
            ],
            "content_width": 110,
            "word_spacing": 10,
            "row_spacing": 20,
            "balanced": False,
            "rows_per_page": 2,
        },
        expected_pages=2,
    ),
]


# ── Preset / Workflow resolution ────────────────────────────────────────────

_PRESET_MAP: dict[str, dict[str, dict[str, Preset]]] = {
    "landscape": LANDSCAPE_PRESET,
    "story": STORY_PRESET,
    "square": SQUARE_PRESET,
}

_WORKFLOW_MAP: dict[str, type] = {
    "verse": VerseWorkflow,
    "surah": SurahWorkflow,
    "verse_range": VerseRangeWorkflow,
    "isolate": IsolateWordsWorkflow,
}


def _build_preset(scenario: Scenario) -> Preset:
    return _PRESET_MAP[scenario.aspect][scenario.mode][scenario.resolution]


def _build_workflow(scenario: Scenario) -> Any:
    preset = _build_preset(scenario)
    cls = _WORKFLOW_MAP[scenario.workflow_type]
    return cls(preset)


# ── Module-level render helpers ──────────────────────────────────────────


def _create_dummy_word_item(text: str, width: int, height: int) -> WordItem:
    """Create a deterministic grayscale WordItem for VImage golden tests."""
    from PIL import Image

    return WordItem(image=Image.new("L", (width, height), 255), text=text, color=None)


def _render_module_pages(scenario: Scenario) -> Iterator[Image.Image]:
    """Yield one page per module-level scenario (wimage / timage / vimage)."""
    preset = _build_preset(scenario)
    module = scenario.params["module"]

    if module == "wimage":
        yield get_wimage(scenario.params["text"], preset.word)

    elif module == "timage":
        img = get_timage(scenario.params["text"], preset.text)
        if img is not None:
            yield img

    elif module == "vimage":
        items_data: list[tuple[str, int, int]] = scenario.params["items"]
        items = [_create_dummy_word_item(t, w, h) for t, w, h in items_data]
        cfg = VerseConfig(
            word_spacing=scenario.params["word_spacing"],
            row_spacing=scenario.params["row_spacing"],
            balanced_wrapping=scenario.params["balanced"],
        )
        vimg = VImage(items, cfg, scenario.params["content_width"])
        rows_per_page = scenario.params.get("rows_per_page")
        if rows_per_page is None:
            rows, _ = vimg.get_page_chunk(0, len(items))
            yield vimg.render(preset.word, rows_to_render=rows, mode="RGBA")
            return
        # Multi-page rendering honoring Quranic stop-sign page breaks.
        # NOTE: get_page_chunk returns `consumed` relative to `pos`.
        pos = 0
        while pos < len(items):
            rows, consumed = vimg.get_page_chunk(pos, rows_per_page)
            yield vimg.render(preset.word, rows_to_render=rows, mode="RGBA")
            if consumed <= 0:
                break
            pos += consumed

    elif module == "image":
        op = scenario.params["op"]
        # Base is a real rendered Arabic word, padded so glow exercises the
        # RGBA "glow behind content" composite path (transparent borders).
        base = pad(get_wimage(scenario.params["text"], preset.word), Padding(20, 20, 20, 20))

        if op == "color":
            yield color(base, scenario.params["color"])
        elif op == "pad":
            yield pad(base, Padding(*scenario.params["padding"]), scenario.params["color"])
        elif op == "glow":
            yield glow(
                base,
                strength=scenario.params["strength"],
                radius=scenario.params["radius"],
                quality=scenario.params["quality"],
            )
        elif op == "glow_quality":
            for quality in ("fast", "balanced", "quality"):
                yield glow(
                    base,
                    strength=scenario.params["strength"],
                    radius=scenario.params["radius"],
                    quality=quality,
                )
        elif op == "glow_comparison":
            comparison = Image.new("RGBA", (base.width * 4, base.height), (0, 0, 0, 0))
            comparison.paste(base, (0, 0))
            for i, quality in enumerate(("fast", "balanced", "quality"), start=1):
                glowed = glow(
                    base,
                    strength=scenario.params["strength"],
                    radius=scenario.params["radius"],
                    quality=quality,
                )
                comparison.paste(glowed, (base.width * i, 0))
            yield comparison
        else:
            raise ValueError(f"Unknown image op: {op}")

    else:
        raise ValueError(f"Unknown module type: {module}")


# ── Comparator ──────────────────────────────────────────────────────────────


def _compare_images(ref: Image.Image, rendered: Image.Image) -> PageDiff:
    if ref.size != rendered.size:
        return PageDiff(
            page=0,
            diff_pixels=-1,
            total_pixels=ref.size[0] * ref.size[1],
            diff_percent=100.0,
            size_match=False,
        )

    if ref.tobytes() == rendered.tobytes():
        total = ref.size[0] * ref.size[1]
        return PageDiff(page=0, diff_pixels=0, total_pixels=total, diff_percent=0.0, size_match=True)

    diff = ImageChops.difference(ref, rendered)
    bbox = diff.getbbox()
    # Vectorized diff-pixel count (all C-level ops). A pixel differs iff at
    # least one channel is non-zero; saturating-adding the channels preserves
    # that property (identical pixels sum to 0), and histogram() counts the
    # non-zero bins. The per-pixel Python loop this replaces cost ~1s per
    # 1080p page and only ran on pages that actually differ.
    total_mask = diff.split()[0]
    for channel in diff.split()[1:]:
        total_mask = ImageChops.add(total_mask, channel)
    diff_pixels = sum(total_mask.histogram()[1:])
    total = diff.size[0] * diff.size[1]

    return PageDiff(
        page=0,
        diff_pixels=diff_pixels,
        total_pixels=total,
        diff_percent=round(diff_pixels / total * 100, 4),
        size_match=True,
        bbox=list(bbox) if bbox else None,
    )


# ── Reference metadata I/O ────────────────────────────────────────────────


def _get_reference_root() -> Path:
    return Path(__file__).resolve().parent / "references"


# Version directory names: letters, digits, dot, underscore, hyphen. Blocks
# path traversal via a malicious --version (e.g. "..\\..\\secrets").
_VERSION_DIR_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def validate_version_dir_name(version: str) -> str:
    """Validate a reference version string for safe use as a directory name.

    Args:
        version: The version string to validate.

    Returns:
        The validated version string.

    Raises:
        ValueError: If the version contains characters unsafe for a path segment.
    """
    if not _VERSION_DIR_RE.match(version):
        raise ValueError(
            f"Invalid reference version: {version!r}. Only letters, digits, dots, underscores and hyphens are allowed."
        )
    return version


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _scenarios_metadata(version: str) -> dict[str, Any]:
    return {
        "version": version,
        "qml_version": qml_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenarios": [
            {
                "name": s.name,
                "aspect": s.aspect,
                "mode": s.mode,
                "resolution": s.resolution,
                "workflow_type": s.workflow_type,
                "params": {k: v for k, v in s.params.items() if k != "translations"},
                "expected_pages": s.expected_pages,
            }
            for s in CANONICAL_SCENARIOS
        ],
    }


def _perf_metrics(version: str, metrics: list[ScenarioMetrics]) -> dict[str, Any]:
    import platform

    total_elapsed = sum(m.elapsed_s for m in metrics)
    return {
        "version": version,
        "qml_version": qml_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "summary": {
            "scenarios": len(metrics),
            "total_elapsed_s": round(total_elapsed, 3),
            "avg_elapsed_s": round(total_elapsed / len(metrics), 3) if metrics else 0.0,
            "peak_rss_mb": max((m.peak_rss_mb for m in metrics), default=0.0),
        },
        "scenarios": [
            {
                "name": m.name,
                "elapsed_s": round(m.elapsed_s, 3),
                "pages": m.pages,
                "peak_rss_mb": round(m.peak_rss_mb, 1),
                "pixel_hash": m.pixel_hash,
            }
            for m in metrics
        ],
    }


def _sha256_lines(version_dir: Path) -> str:
    lines: list[str] = []
    for p in sorted(version_dir.glob("*.png")):
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{h}  {p.name}")
    return "\n".join(lines) + "\n"


def _load_perf(path: Path) -> dict[str, Any] | None:
    return _read_json(path / "perf.json")


def _load_scenarios_meta(path: Path) -> list[dict[str, Any]] | None:
    data = _read_json(path / "scenarios.json")
    if data is None:
        return None
    return data.get("scenarios", [])


# ── Harness ─────────────────────────────────────────────────────────────────


class ValidationHarness:
    """Central orchestrator for the QuranMediaLib check suite.

    Provides rendering, pixel comparison, reference management, and performance
    benchmarking. Backward compatible: old reference directories always load
    correctly with new code.
    """

    def __init__(self, version: str | None = None) -> None:
        if version is None:
            version = f"v{qml_version}"
        self._version = validate_version_dir_name(version)
        self._db = DatabaseManager()
        self._ref_root = _get_reference_root()

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> ValidationHarness:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def version(self) -> str:
        return self._version

    @property
    def reference_dir(self) -> Path:
        return self._ref_root / self._version

    def get_reference_path(self, scenario: Scenario, page: int) -> Path:
        return self.reference_dir / f"{scenario.name}_p{page}.png"

    @property
    def scenarios(self) -> list[Scenario]:
        return list(CANONICAL_SCENARIOS)

    # ── Rendering ─────────────────────────────────────────────────────────

    def render_scenario(self, scenario: Scenario) -> list[Image.Image]:
        """Render a scenario and return page images (materializes from streaming iterator)."""
        return list(self._iter_pages(scenario))

    def _count_pages(self, scenario: Scenario, output_dir: str) -> int:
        """Render a scenario using file-based output to avoid IPC overhead, returns page count."""
        if scenario.workflow_type == "module":
            return sum(1 for _ in _render_module_pages(scenario))

        wf = _build_workflow(scenario)

        if scenario.workflow_type == "surah":
            it = wf.get_iterator(
                surah=scenario.params["surah"],
                annotate=scenario.params.get("annotate", True),
                separate_translations=scenario.params.get("separate_translations", False),
                output_dir=output_dir,
            )
        elif scenario.workflow_type == "verse_range":
            surah = scenario.params["surah"]
            start = scenario.params.get("start_ayah", 1)
            end = scenario.params.get("end_ayah", start)
            tr: list[list[str]] = []
            for v in range(start, end + 1):
                tr.append([self._db.get_translation_from_verse(surah, v)])
            it = wf.get_iterator(
                surah=surah,
                translations=tr,
                start_ayah=start,
                end_ayah=end,
                annotate=scenario.params.get("annotate", True),
                output_dir=output_dir,
            )
        elif scenario.workflow_type == "verse":
            it = wf.get_iterator(
                surah=scenario.params["surah"],
                ayah=scenario.params["ayah"],
                translations=scenario.params.get("translations", []),
                annotate=scenario.params.get("annotate", True),
            )
        elif scenario.workflow_type == "isolate":
            surah = scenario.params["surah"]
            ayah = scenario.params["ayah"]
            verse_text = self._db.get_verse(surah, ayah).split()
            wbw = list(self._db.get_wbw_grouped_by_verse(surah).get(ayah, []))
            translation = self._db.get_translation_from_verse(surah, ayah)
            it = wf.get_iterator(
                surah=surah,
                verse_words=verse_text,
                translations=[translation],
                ayah=ayah,
                wbw_translations=wbw,
                annotate=scenario.params.get("annotate", True),
            )
        else:
            raise ValueError(f"Unknown workflow type: {scenario.workflow_type}")

        return sum(len(batch) for batch in it)

    def _iter_pages(self, scenario: Scenario) -> Iterator[Image.Image]:
        """Render a scenario, yielding pages one at a time (never accumulates)."""
        if scenario.workflow_type == "module":
            yield from _render_module_pages(scenario)
            return

        wf = _build_workflow(scenario)

        if scenario.workflow_type == "surah":
            it = wf.get_iterator(
                surah=scenario.params["surah"],
                annotate=scenario.params.get("annotate", True),
                separate_translations=scenario.params.get("separate_translations", False),
            )
        elif scenario.workflow_type == "verse":
            it = wf.get_iterator(
                surah=scenario.params["surah"],
                ayah=scenario.params["ayah"],
                translations=scenario.params.get("translations", []),
                annotate=scenario.params.get("annotate", True),
            )
        elif scenario.workflow_type == "verse_range":
            surah = scenario.params["surah"]
            start = scenario.params.get("start_ayah", 1)
            end = scenario.params.get("end_ayah", start)
            tr: list[list[str]] = []
            for v in range(start, end + 1):
                tr.append([self._db.get_translation_from_verse(surah, v)])
            it = wf.get_iterator(
                surah=surah,
                translations=tr,
                start_ayah=start,
                end_ayah=end,
                annotate=scenario.params.get("annotate", True),
            )
        elif scenario.workflow_type == "isolate":
            surah = scenario.params["surah"]
            ayah = scenario.params["ayah"]
            verse_text = self._db.get_verse(surah, ayah).split()
            wbw = list(self._db.get_wbw_grouped_by_verse(surah).get(ayah, []))
            translation = self._db.get_translation_from_verse(surah, ayah)
            it = wf.get_iterator(
                surah=surah,
                verse_words=verse_text,
                translations=[translation],
                ayah=ayah,
                wbw_translations=wbw,
                annotate=scenario.params.get("annotate", True),
            )
        else:
            raise ValueError(f"Unknown workflow type: {scenario.workflow_type}")

        for batch in it:
            yield from batch

    def benchmark_scenario(self, scenario: Scenario) -> ScenarioMetrics:
        """Render and collect performance metrics for a single scenario.

        Uses file-based output to avoid IPC deserialization overhead.
        """
        bm_dir = os.path.join(_get_reference_root().parent, ".bm", uuid.uuid4().hex[:12])
        os.makedirs(bm_dir, exist_ok=True)
        try:
            mem_before = _get_memory_mb()
            start = time.perf_counter()
            page_count = self._count_pages(scenario, bm_dir)
            elapsed = time.perf_counter() - start
            rss = max(_get_memory_mb(), mem_before)
        finally:
            shutil.rmtree(bm_dir, ignore_errors=True)

        return ScenarioMetrics(
            name=scenario.name,
            elapsed_s=elapsed,
            pages=page_count,
            peak_rss_mb=rss,
            pixel_hash="",
        )

    # ── Validation (single scenario) ──────────────────────────────────────

    def validate_scenario(self, scenario: Scenario) -> ValidationResult:
        """Render a scenario and compare against its reference images (streaming, no accumulation)."""
        start = time.perf_counter()
        ref_dir = self.reference_dir
        hasher = hashlib.sha256()
        page_diffs: list[PageDiff] = []
        all_pass = True
        i = 0

        if not ref_dir.exists():
            return ValidationResult(
                scenario=scenario.name,
                passed=False,
                pages_expected=scenario.expected_pages,
                pages_actual=0,
                error=f"No references at {ref_dir} (run 'update' first)",
                elapsed=time.perf_counter() - start,
            )

        try:
            for page in self._iter_pages(scenario):
                hasher.update(page.tobytes())

                if i >= scenario.expected_pages:
                    page_diffs.append(
                        PageDiff(page=i, diff_pixels=-1, total_pixels=0, diff_percent=100.0, size_match=False)
                    )
                    all_pass = False
                    i += 1
                    continue

                ref_path = self.get_reference_path(scenario, i)
                if not ref_path.exists():
                    page_diffs.append(
                        PageDiff(page=i, diff_pixels=-1, total_pixels=0, diff_percent=100.0, size_match=False)
                    )
                    all_pass = False
                    i += 1
                    continue

                ref_img = Image.open(ref_path)
                diff = _compare_images(ref_img, page)
                diff.page = i
                page_diffs.append(diff)
                if diff.diff_pixels != 0:
                    all_pass = False
                i += 1

        except Exception as e:
            return ValidationResult(
                scenario=scenario.name,
                passed=False,
                pages_expected=scenario.expected_pages,
                pages_actual=i,
                error=str(e),
                elapsed=time.perf_counter() - start,
            )

        actual = i
        metrics = ScenarioMetrics(
            name=scenario.name,
            elapsed_s=time.perf_counter() - start,
            pages=actual,
            peak_rss_mb=_get_memory_mb(),
            pixel_hash=f"sha256:{hasher.hexdigest()}",
        )

        # Handle missing pages (rendered fewer than expected)
        while i < scenario.expected_pages:
            page_diffs.append(PageDiff(page=i, diff_pixels=-1, total_pixels=0, diff_percent=100.0, size_match=False))
            all_pass = False
            i += 1

        return ValidationResult(
            scenario=scenario.name,
            passed=all_pass and actual == scenario.expected_pages,
            pages_expected=scenario.expected_pages,
            pages_actual=actual,
            page_diffs=page_diffs,
            metrics=metrics,
            elapsed=time.perf_counter() - start,
        )

    # ── Batch operations ──────────────────────────────────────────────────

    def run_all(self, scenarios: list[Scenario] | None = None) -> list[ValidationResult]:
        """Validate all (or given) scenarios against references."""
        if scenarios is None:
            scenarios = CANONICAL_SCENARIOS
        return [self.validate_scenario(s) for s in scenarios]

    def benchmark_all(self, scenarios: list[Scenario] | None = None) -> list[ScenarioMetrics]:
        """Benchmark all (or given) scenarios."""
        if scenarios is None:
            scenarios = CANONICAL_SCENARIOS
        return [self.benchmark_scenario(s) for s in scenarios]

    # ── Reference management ──────────────────────────────────────────────

    def update_references(self, scenarios: list[Scenario] | None = None) -> list[Path]:
        """Render scenarios, save reference images + metadata (streaming, no accumulation)."""
        if scenarios is None:
            scenarios = CANONICAL_SCENARIOS
        ref_dir = self.reference_dir
        ref_dir.mkdir(parents=True, exist_ok=True)

        created: list[Path] = []
        metrics_list: list[ScenarioMetrics] = []

        for scenario in scenarios:
            # Time the render using file-based output
            bm_dir = os.path.join(_get_reference_root().parent, ".bm", uuid.uuid4().hex[:12])
            os.makedirs(bm_dir, exist_ok=True)
            mem_before = _get_memory_mb()
            start = time.perf_counter()
            page_count = self._count_pages(scenario, bm_dir)
            elapsed = time.perf_counter() - start
            rss = max(_get_memory_mb(), mem_before)
            shutil.rmtree(bm_dir, ignore_errors=True)

            # Save reference images (streaming, no accumulation)
            hasher = hashlib.sha256()
            for i, page in enumerate(self._iter_pages(scenario)):
                if i >= scenario.expected_pages:
                    break
                hasher.update(page.tobytes())
                path = self.get_reference_path(scenario, i)
                page.save(path)
                created.append(path)

            metrics_list.append(
                ScenarioMetrics(
                    name=scenario.name,
                    elapsed_s=elapsed,
                    pages=page_count,
                    peak_rss_mb=rss,
                    pixel_hash=f"sha256:{hasher.hexdigest()}",
                )
            )

        _write_json(ref_dir / "scenarios.json", _scenarios_metadata(self._version))
        _write_json(ref_dir / "perf.json", _perf_metrics(self._version, metrics_list))

        sha_path = ref_dir / "sha256sums"
        sha_path.write_text(_sha256_lines(ref_dir))

        return created

    # ── Cross-version comparison ──────────────────────────────────────────

    def compare_versions(self, version_a: str, version_b: str) -> CrossVersionReport:
        """Compare reference image sets between two versions.

        Returns a report of matching, differing, and version-unique scenarios.
        """
        version_a = validate_version_dir_name(version_a)
        version_b = validate_version_dir_name(version_b)
        dir_a = self._ref_root / version_a
        dir_b = self._ref_root / version_b

        scenarios_a = _load_scenarios_meta(dir_a) or []
        scenarios_b = _load_scenarios_meta(dir_b) or []

        names_a = {s["name"] for s in scenarios_a}
        names_b = {s["name"] for s in scenarios_b}
        common_names = names_a & names_b
        only_a = sorted(names_a - names_b)
        only_b = sorted(names_b - names_a)

        common_diffs: list[CrossVersionScenarioDiff] = []
        all_match = True

        for name in sorted(common_names):
            pages_a = sorted(dir_a.glob(f"{name}_p*.png"))
            pages_b = sorted(dir_b.glob(f"{name}_p*.png"))

            if len(pages_a) != len(pages_b):
                common_diffs.append(
                    CrossVersionScenarioDiff(
                        scenario=name,
                        match=False,
                        max_diff_percent=100.0,
                        pages_a=len(pages_a),
                        pages_b=len(pages_b),
                        details=[
                            PageDiff(page=-1, diff_pixels=-1, total_pixels=0, diff_percent=100.0, size_match=False)
                        ],
                    )
                )
                all_match = False
                continue

            details: list[PageDiff] = []
            max_diff = 0.0
            scenario_match = True

            for i, (pa, pb) in enumerate(zip(pages_a, pages_b)):
                img_a = Image.open(pa)
                img_b = Image.open(pb)
                diff = _compare_images(img_a, img_b)
                diff.page = i
                details.append(diff)
                if diff.diff_pixels != 0:
                    scenario_match = False
                    max_diff = max(max_diff, diff.diff_percent)

            common_diffs.append(
                CrossVersionScenarioDiff(
                    scenario=name,
                    match=scenario_match,
                    max_diff_percent=max_diff,
                    pages_a=len(pages_a),
                    pages_b=len(pages_b),
                    details=details,
                )
            )
            if not scenario_match:
                all_match = False

        return CrossVersionReport(
            version_a=version_a,
            version_b=version_b,
            common=common_diffs,
            only_in_a=only_a,
            only_in_b=only_b,
            all_match=all_match,
        )


# ── Report printers ────────────────────────────────────────────────────────


def _print_validation_report(results: list[ValidationResult]) -> None:
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    total_time = sum(r.elapsed for r in results)

    print(f"\n{'=' * 60}")
    print(f"  VALIDATION REPORT  ({qml_version})")
    print(f"{'=' * 60}")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if r.error:
            print(f"  [{status}] {r.scenario}: ERROR — {r.error}")
        elif not r.passed and r.page_diffs:
            issues = []
            for d in r.page_diffs:
                if d.diff_pixels == -1:
                    issues.append(f"p{d.page}: MISSING")
                elif d.diff_pixels > 0:
                    issues.append(f"p{d.page}: {d.diff_percent}% diff")
            detail = ", ".join(issues) if issues else f"pages {r.pages_actual}/{r.pages_expected}"
            print(f"  [{status}] {r.scenario}: {detail}")
        else:
            perf = f" ({r.elapsed:.2f}s" + (f", {r.metrics.peak_rss_mb:.0f}MB)" if r.metrics else ")")
            print(f"  [{status}] {r.scenario}: {r.pages_actual} page(s){perf}")
    print(f"{'=' * 60}")
    print(f"  {passed}/{total} passed  ({total_time:.2f}s total)")
    print()


def _print_perf_report(metrics: list[ScenarioMetrics]) -> None:
    total = sum(m.elapsed_s for m in metrics)
    print(f"\n{'=' * 60}")
    print(f"  BENCHMARK REPORT  ({qml_version})")
    print(f"{'=' * 60}")
    for m in metrics:
        print(
            f"  {m.name:<28s}  {m.pages} page(s)  {m.elapsed_s:>7.3f}s  {m.peak_rss_mb:>7.1f}MB  {m.pixel_hash[:16]}..."
        )
    print(f"{'=' * 60}")
    print(f"  {len(metrics)} scenarios  {total:.2f}s total")
    print()


def _print_compare_report(report: CrossVersionReport) -> None:
    print(f"\n{'=' * 60}")
    print("  CROSS-VERSION COMPARISON")
    print(f"  {report.version_a}  vs  {report.version_b}")
    print(f"{'=' * 60}")
    for d in report.common:
        status = "OK" if d.match else "DIFF"
        print(f"  [{status}] {d.scenario:<28s}  diff: {d.max_diff_percent}%")
    if report.only_in_a:
        print(f"  Only in {report.version_a}: {', '.join(report.only_in_a)}")
    if report.only_in_b:
        print(f"  Only in {report.version_b}: {', '.join(report.only_in_b)}")
    print(f"{'=' * 60}")
    print(f"  All match: {report.all_match}")
    print()


# ── CLI ─────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """Build the harness argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser with all subcommands.
    """
    parser = argparse.ArgumentParser(
        description="QuranMediaLib Validation Harness — permanent rendering correctness checker.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    sub.add_parser("list", help="List canonical scenarios")

    # update
    update_parser = sub.add_parser("update", help="(Re)generate reference images + perf data")
    update_parser.add_argument("--scenario", "-s", help="Update only a specific scenario")
    update_parser.add_argument("--version", help="Reference version (default: current)")

    # run
    run_parser = sub.add_parser("run", help="Validate against reference images")
    run_parser.add_argument("--scenario", "-s", help="Run only a specific scenario by name")
    run_parser.add_argument("--version", help="Reference version (default: current)")
    run_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    # benchmark
    bench_parser = sub.add_parser("benchmark", help="Run performance benchmarks")
    bench_parser.add_argument("--scenario", "-s", help="Benchmark only a specific scenario")
    bench_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    # test — the MAIN entrypoint
    test_parser = sub.add_parser("test", help="Full test suite: pixel validation + perf benchmarks + unit tests")
    test_parser.add_argument("--version", help="Reference version (default: current)")
    test_parser.add_argument("--scenario", "-s", help="Test only a specific scenario")
    test_parser.add_argument("--no-benchmark", action="store_true", help="Skip performance benchmarks")
    test_parser.add_argument("--unit", action="store_true", help="Run unit tests only, skip pixel validation")

    # compare
    compare_parser = sub.add_parser("compare", help="Cross-version pixel comparison")
    compare_parser.add_argument("version_a", help="First version (e.g. v4.1.0)")
    compare_parser.add_argument("version_b", help="Second version (e.g. v4.0.0)")
    compare_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    return parser


def _select_scenarios(scenario_name: str | None) -> list[Scenario] | None:
    """Resolve canonical scenarios, optionally filtered to one by name.

    Args:
        scenario_name: Optional scenario name filter.

    Returns:
        The scenario list, or None if the named scenario is unknown.
    """
    if scenario_name is None:
        return CANONICAL_SCENARIOS
    scenarios = [s for s in CANONICAL_SCENARIOS if s.name == scenario_name]
    if not scenarios:
        print(f"Unknown scenario: {scenario_name}")
        return None
    return scenarios


def _json_diff_detail(page_diffs: list[PageDiff] | None) -> list[dict[str, Any]] | None:
    """Serialize page diff details for JSON output.

    Args:
        page_diffs: The diff details to serialize.

    Returns:
        Serializable list, or None if there are no diffs.
    """
    if not page_diffs:
        return None
    return [
        {
            "page": x.page,
            "diff_pixels": x.diff_pixels,
            "total_pixels": x.total_pixels,
            "diff_percent": x.diff_percent,
            "size_match": x.size_match,
            "bbox": x.bbox,
        }
        for x in page_diffs
    ]


def _cmd_list() -> int:
    """List canonical scenarios."""
    print(f"\nCanonical Scenarios ({len(CANONICAL_SCENARIOS)} total):\n")
    for s in CANONICAL_SCENARIOS:
        print(
            f"  {s.name:<28s}  {s.aspect:<10s} {s.mode:<12s} {s.resolution:<6s} "
            f"{s.workflow_type:<12s} {s.expected_pages} page(s)"
        )
    print()
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    """Compare two versions' reference sets."""
    harness = ValidationHarness()
    report = harness.compare_versions(args.version_a, args.version_b)
    if args.json:
        json.dump(
            {
                "version_a": report.version_a,
                "version_b": report.version_b,
                "all_match": report.all_match,
                "only_in_a": report.only_in_a,
                "only_in_b": report.only_in_b,
                "comparisons": [
                    {
                        "scenario": d.scenario,
                        "match": d.match,
                        "max_diff_percent": d.max_diff_percent,
                        "pages_a": d.pages_a,
                        "pages_b": d.pages_b,
                        "details": _json_diff_detail(d.details),
                    }
                    for d in report.common
                ],
            },
            sys.stdout,
            indent=2,
        )
        print()
    else:
        _print_compare_report(report)
    harness.close()
    return 0 if report.all_match else 1


def _cmd_test(args: argparse.Namespace) -> int:
    """Run the full test suite: pixel validation + benchmarks + unit tests."""
    version = getattr(args, "version", None) or f"v{qml_version}"
    hv = ValidationHarness(version)

    all_pass = True
    total_start = time.perf_counter()

    try:
        if not args.unit:
            scenarios = _select_scenarios(args.scenario)
            if scenarios is None:
                return 1
            results = hv.run_all(scenarios)
            _print_validation_report(results)
            if not all(r.passed for r in results):
                all_pass = False

        if not args.no_benchmark:
            scenarios = CANONICAL_SCENARIOS
            if args.scenario:
                scenarios = [s for s in scenarios if s.name == args.scenario]
            metrics = hv.benchmark_all(scenarios)
            _print_perf_report(metrics)

        if not args.scenario and not _cmd_pytest_unit(args):
            all_pass = False
    finally:
        hv.close()

    elapsed = time.perf_counter() - total_start
    print(f"\n{'=' * 60}")
    print(f"  {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}  ({elapsed:.1f}s total)")
    print(f"{'=' * 60}\n")
    return 0 if all_pass else 1


def _cmd_pytest_unit(args: argparse.Namespace) -> bool:
    """Run the pytest unit gate (excludes the git-ignored golden tests).

    Args:
        args: Parsed CLI arguments.

    Returns:
        True if the pytest run succeeded.
    """
    import pytest as _pytest

    pytest_args = ["tests/", "-x", "-q", "--tb=short"]
    if args.unit:
        # Pure unit gate: excludes the golden-contract test, which needs
        # git-ignored reference images (developer-local only).
        pytest_args.append("--ignore=tests/test_validation.py")
        print("\n  Running unit tests only...")
    else:
        pytest_args.extend(["--ignore=tests/test_validation.py"])
        if not args.no_benchmark:
            pytest_args.append("--benchmark")
            print("\n  Running unit tests with module benchmarks...")
        else:
            print("\n  Running unit tests...")
    return _pytest.main(pytest_args) == 0


def _cmd_update(args: argparse.Namespace, harness: ValidationHarness) -> int:
    """(Re)generate reference images + perf data."""
    scenarios = _select_scenarios(args.scenario)
    if scenarios is None:
        return 1
    paths = harness.update_references(scenarios)
    print(f"\nUpdated {len(paths)} reference images + metadata in {harness.reference_dir}\n")
    return 0


def _cmd_benchmark(args: argparse.Namespace, harness: ValidationHarness) -> int:
    """Run performance benchmarks."""
    scenarios = _select_scenarios(args.scenario)
    if scenarios is None:
        return 1
    metrics = harness.benchmark_all(scenarios)
    if args.json:
        json.dump(_perf_metrics(harness.version, metrics), sys.stdout, indent=2)
        print()
    else:
        _print_perf_report(metrics)
    return 0


def _cmd_run(args: argparse.Namespace, harness: ValidationHarness) -> int:
    """Validate against reference images."""
    scenarios = _select_scenarios(args.scenario)
    if scenarios is None:
        return 1
    results = harness.run_all(scenarios)
    if args.json:
        json.dump(
            [
                {
                    "scenario": r.scenario,
                    "passed": r.passed,
                    "pages_expected": r.pages_expected,
                    "pages_actual": r.pages_actual,
                    "error": r.error,
                    "elapsed": round(r.elapsed, 3),
                    "metrics": {
                        "elapsed_s": round(r.metrics.elapsed_s, 3),
                        "pages": r.metrics.pages,
                        "peak_rss_mb": round(r.metrics.peak_rss_mb, 1),
                        "pixel_hash": r.metrics.pixel_hash,
                    }
                    if r.metrics
                    else None,
                    "page_diffs": _json_diff_detail(r.page_diffs),
                }
                for r in results
            ],
            sys.stdout,
            indent=2,
        )
        print()
    else:
        _print_validation_report(results)
    return 0 if all(r.passed for r in results) else 1


def cli() -> int:
    """CLI entrypoint for the validation harness."""
    args = _build_parser().parse_args()

    if args.command == "list":
        return _cmd_list()

    if args.command == "compare":
        return _cmd_compare(args)

    if args.command == "test":
        return _cmd_test(args)

    version = getattr(args, "version", None)
    harness = ValidationHarness(version)
    try:
        if args.command == "update":
            return _cmd_update(args, harness)
        if args.command == "benchmark":
            return _cmd_benchmark(args, harness)
        if args.command == "run":
            return _cmd_run(args, harness)
    finally:
        harness.close()

    return 1


if __name__ == "__main__":
    sys.exit(cli())
