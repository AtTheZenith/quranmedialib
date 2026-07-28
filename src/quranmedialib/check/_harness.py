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
import sys
import time
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
            "annotate": True,
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


# ── Render helpers ──────────────────────────────────────────────────────────


def _render_verse(workflow: VerseWorkflow, params: dict[str, Any], db: DatabaseManager) -> list[Image.Image]:
    pages = list(
        workflow.get_iterator(
            surah=params["surah"],
            ayah=params["ayah"],
            translations=params.get("translations", []),
            annotate=params.get("annotate", True),
        )
    )
    return pages[0] if pages else []


def _render_surah(workflow: SurahWorkflow, params: dict[str, Any], db: DatabaseManager) -> list[Image.Image]:
    pages_list = list(
        workflow.get_iterator(
            surah=params["surah"],
            annotate=params.get("annotate", True),
            separate_translations=params.get("separate_translations", False),
        )
    )
    flat: list[Image.Image] = []
    for g in pages_list:
        flat.extend(g)
    return flat


def _render_verse_range(workflow: VerseRangeWorkflow, params: dict[str, Any], db: DatabaseManager) -> list[Image.Image]:
    surah = params["surah"]
    start = params.get("start_ayah", 1)
    end = params.get("end_ayah", start)
    tr: list[list[str]] = []
    for v in range(start, end + 1):
        tr.append([db.get_translation_from_verse(surah, v)])
    pages_list = list(
        workflow.get_iterator(
            surah=surah,
            translations=tr,
            start_ayah=start,
            end_ayah=end,
            annotate=params.get("annotate", True),
        )
    )
    flat: list[Image.Image] = []
    for g in pages_list:
        flat.extend(g)
    return flat


def _render_isolate(workflow: IsolateWordsWorkflow, params: dict[str, Any], db: DatabaseManager) -> list[Image.Image]:
    surah = params["surah"]
    ayah = params["ayah"]
    verse_text = db.get_verse(surah, ayah)
    verse_words = verse_text.split()
    wbw_dict = db.get_wbw_grouped_by_verse(surah)
    wbw = list(wbw_dict.get(ayah, []))
    translation = db.get_translation_from_verse(surah, ayah)
    pages_list = list(
        workflow.get_iterator(
            surah=surah,
            verse_words=verse_words,
            translations=[translation],
            ayah=ayah,
            wbw_translations=wbw,
            annotate=params.get("annotate", True),
        )
    )
    flat: list[Image.Image] = []
    for g in pages_list:
        flat.extend(g)
    return flat


_RENDER_MAP: dict[str, Any] = {
    "verse": _render_verse,
    "surah": _render_surah,
    "verse_range": _render_verse_range,
    "isolate": _render_isolate,
}


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

    ref_data = list(ref.getdata())
    rendered_data = list(rendered.getdata())

    if ref_data == rendered_data:
        return PageDiff(page=0, diff_pixels=0, total_pixels=len(ref_data), diff_percent=0.0, size_match=True)

    diff = ImageChops.difference(ref, rendered)
    bbox = diff.getbbox()

    diff_pixels = sum(1 for p in diff.getdata() if any(c != 0 for c in (p if isinstance(p, tuple) else (p,))))
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
        self._version = version
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
        """Render a scenario and return page images."""
        workflow = _build_workflow(scenario)
        render_fn = _RENDER_MAP[scenario.workflow_type]
        return render_fn(workflow, scenario.params, self._db)

    def _iter_pages(self, scenario: Scenario) -> Iterator[Image.Image]:
        """Yield pages one at a time from a scenario workflow, never accumulating."""
        workflow = _build_workflow(scenario)
        cls = _WORKFLOW_MAP[scenario.workflow_type]
        preset = _build_preset(scenario)
        wf = cls(preset)

        if scenario.workflow_type == "verse":
            it = wf.get_iterator(
                surah=scenario.params["surah"],
                ayah=scenario.params["ayah"],
                translations=scenario.params.get("translations", []),
                annotate=scenario.params.get("annotate", True),
            )
            for batch in it:
                yield from batch
        elif scenario.workflow_type == "surah":
            it = wf.get_iterator(
                surah=scenario.params["surah"],
                annotate=scenario.params.get("annotate", True),
                separate_translations=scenario.params.get("separate_translations", False),
            )
            for batch in it:
                yield from batch
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
            for batch in it:
                yield from batch
        elif scenario.workflow_type == "isolate":
            surah = scenario.params["surah"]
            ayah = scenario.params["ayah"]
            verse_text = self._db.get_verse(surah, ayah)
            verse_words = verse_text.split()
            wbw_dict = self._db.get_wbw_grouped_by_verse(surah)
            wbw = list(wbw_dict.get(ayah, []))
            translation = self._db.get_translation_from_verse(surah, ayah)
            it = wf.get_iterator(
                surah=surah,
                verse_words=verse_words,
                translations=[translation],
                ayah=ayah,
                wbw_translations=wbw,
                annotate=scenario.params.get("annotate", True),
            )
            for batch in it:
                yield from batch

    def benchmark_scenario(self, scenario: Scenario) -> ScenarioMetrics:
        """Render and collect performance metrics without accumulating pages."""
        mem_before = _get_memory_mb()
        start = time.perf_counter()
        hasher = hashlib.sha256()
        count = 0
        for page in self._iter_pages(scenario):
            hasher.update(page.tobytes())
            count += 1
        elapsed = time.perf_counter() - start
        rss = max(_get_memory_mb(), mem_before)
        return ScenarioMetrics(
            name=scenario.name,
            elapsed_s=elapsed,
            pages=count,
            peak_rss_mb=rss,
            pixel_hash=f"sha256:{hasher.hexdigest()}",
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
            page_diffs.append(
                PageDiff(page=i, diff_pixels=-1, total_pixels=0, diff_percent=100.0, size_match=False)
            )
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
            m = self.benchmark_scenario(scenario)
            metrics_list.append(m)
            for i, page in enumerate(self._iter_pages(scenario)):
                if i >= scenario.expected_pages:
                    break
                path = self.get_reference_path(scenario, i)
                page.save(path)
                created.append(path)

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


def cli() -> int:
    """CLI entrypoint for the validation harness."""
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

    args = parser.parse_args()

    # ── list ──────────────────────────────────────────────────────────────
    if args.command == "list":
        print(f"\nCanonical Scenarios ({len(CANONICAL_SCENARIOS)} total):\n")
        for s in CANONICAL_SCENARIOS:
            print(
                f"  {s.name:<28s}  {s.aspect:<10s} {s.mode:<12s} {s.resolution:<6s} "
                f"{s.workflow_type:<12s} {s.expected_pages} page(s)"
            )
        print()
        return 0

    # ── compare ───────────────────────────────────────────────────────────
    if args.command == "compare":
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
                            "details": [
                                {
                                    "page": x.page,
                                    "diff_pixels": x.diff_pixels,
                                    "total_pixels": x.total_pixels,
                                    "diff_percent": x.diff_percent,
                                    "size_match": x.size_match,
                                    "bbox": x.bbox,
                                }
                                for x in (d.details or [])
                            ]
                            if d.details
                            else None,
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

    # ── test ──────────────────────────────────────────────────────────────
    if args.command == "test":
        import pytest as _pytest

        version = getattr(args, "version", None) or f"v{qml_version}"
        hv = ValidationHarness(version)

        all_pass = True
        total_start = time.perf_counter()

        try:
            # 1. Pixel validation (unless --unit)
            if not args.unit:
                scenarios = CANONICAL_SCENARIOS
                if args.scenario:
                    scenarios = [s for s in scenarios if s.name == args.scenario]
                    if not scenarios:
                        print(f"Unknown scenario: {args.scenario}")
                        return 1

                results = hv.run_all(scenarios)
                _print_validation_report(results)
                if not all(r.passed for r in results):
                    all_pass = False

            # 2. Benchmarks (always run unless --no-benchmark)
            if not args.no_benchmark:
                scenarios = CANONICAL_SCENARIOS
                if args.scenario:
                    scenarios = [s for s in scenarios if s.name == args.scenario]
                metrics = hv.benchmark_all(scenarios)
                _print_perf_report(metrics)

            # 3. Unit tests via pytest
            if not args.scenario:
                pytest_args = ["tests/", "-x", "-q", "--tb=short"]
                if args.unit:
                    print("\n  Running unit tests only...")
                else:
                    pytest_args.extend(["--ignore=tests/test_validation.py"])
                    print("\n  Running unit tests...")
                unit_ok = _pytest.main(pytest_args) == 0
                if not unit_ok:
                    all_pass = False

        finally:
            hv.close()

        elapsed = time.perf_counter() - total_start
        print(f"\n{'=' * 60}")
        print(f"  {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}  ({elapsed:.1f}s total)")
        print(f"{'=' * 60}\n")
        return 0 if all_pass else 1

    # ── Commands that need a harness instance ─────────────────────────────
    version = getattr(args, "version", None)
    harness = ValidationHarness(version)

    try:
        # ── update ────────────────────────────────────────────────────────
        if args.command == "update":
            scenarios = CANONICAL_SCENARIOS
            if args.scenario:
                scenarios = [s for s in scenarios if s.name == args.scenario]
                if not scenarios:
                    print(f"Unknown scenario: {args.scenario}")
                    return 1
            paths = harness.update_references(scenarios)
            print(f"\nUpdated {len(paths)} reference images + metadata in {harness.reference_dir}\n")
            return 0

        # ── benchmark ─────────────────────────────────────────────────────
        if args.command == "benchmark":
            scenarios = CANONICAL_SCENARIOS
            if args.scenario:
                scenarios = [s for s in scenarios if s.name == args.scenario]
                if not scenarios:
                    print(f"Unknown scenario: {args.scenario}")
                    return 1
            metrics = harness.benchmark_all(scenarios)
            if args.json:
                json.dump(_perf_metrics(harness.version, metrics), sys.stdout, indent=2)
                print()
            else:
                _print_perf_report(metrics)
            return 0

        # ── run ───────────────────────────────────────────────────────────
        if args.command == "run":
            scenarios = CANONICAL_SCENARIOS
            if args.scenario:
                scenarios = [s for s in scenarios if s.name == args.scenario]
                if not scenarios:
                    print(f"Unknown scenario: {args.scenario}")
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
                            "page_diffs": [
                                {
                                    "page": d.page,
                                    "diff_pixels": d.diff_pixels,
                                    "total_pixels": d.total_pixels,
                                    "diff_percent": d.diff_percent,
                                    "size_match": d.size_match,
                                    "bbox": d.bbox,
                                }
                                for d in (r.page_diffs or [])
                            ]
                            if r.page_diffs
                            else None,
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

    finally:
        harness.close()

    return 1


if __name__ == "__main__":
    sys.exit(cli())
