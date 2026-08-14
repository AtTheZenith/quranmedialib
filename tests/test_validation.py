"""Validation tests: lock rendering contracts against version-specific reference data.

Each test validates that the current library code produces output matching a
specific version's reference images. New versions add new parametrize entries.
"""

from __future__ import annotations

import copy
import json
import shutil

import pytest

from quranmedialib import __version__ as qml_version
from quranmedialib.check import CANONICAL_SCENARIOS, ValidationHarness
from quranmedialib.check._harness import _sidecar_sha256, validate_version_dir_name

SUPPORTED_VERSIONS = ["v4.1.1"]


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
@pytest.mark.parametrize("scenario", CANONICAL_SCENARIOS, ids=lambda s: s.name)
def test_rendering_contract(version: str, scenario) -> None:
    """Validate current output matches version-specific reference images."""
    harness = ValidationHarness(version)
    try:
        if not harness.get_reference_path(scenario, 0).exists():
            pytest.skip(f"[{version}] has no reference for {scenario.name}")
        result = harness.validate_scenario(scenario)
        assert result.passed, f"[{version}] {result.scenario}: " + (result.error or _diff_summary(result))
    finally:
        harness.close()


def test_sidecar_scenarios_validate_against_current() -> None:
    """Sidecar scenarios validate cleanly (pixels + geometry) against current references."""
    version = f"v{qml_version}"
    harness = ValidationHarness(version)
    try:
        sidecar_scenarios = [s for s in CANONICAL_SCENARIOS if s.params.get("emit_sidecar")]
        assert sidecar_scenarios, "expected at least one sidecar canonical scenario"
        for scenario in sidecar_scenarios:
            if not harness.get_reference_path(scenario, 0).exists():
                pytest.skip(f"[{version}] no references for {scenario.name}; run 'check update'")
            result = harness.validate_scenario(scenario)
            assert result.passed, f"[{version}] {result.scenario}: " + (result.error or _diff_summary(result))
            assert result.sidecar_mismatch is False
    finally:
        harness.close()


def test_sidecar_geometry_shift_detected_when_pixels_match() -> None:
    """A shifted word x-coordinate fails geometry validation even when pixels match."""
    scenario = next(s for s in CANONICAL_SCENARIOS if s.params.get("emit_sidecar"))
    version = "v_sidecar_shift"
    harness = ValidationHarness(version)
    try:
        harness.update_references([scenario])

        # Capture the true page-0 sidecar, then shift the first word's x-coordinate.
        rendered = list(harness._iter_pages_with_sidecars(scenario))
        assert rendered, "sidecar scenario must produce pages"
        _, true_sidecar = rendered[0]
        shifted = copy.deepcopy(true_sidecar)
        shifted["rows"][0]["words"][0]["x"] += 2

        # Tamper the stored sidecar hash for page 0 in perf.json.
        perf_path = harness.reference_dir / "perf.json"
        perf = json.loads(perf_path.read_text())
        for entry in perf["scenarios"]:
            if entry["name"] == scenario.name:
                entry["sidecar_hashes"][0] = _sidecar_sha256(shifted)
        perf_path.write_text(json.dumps(perf, indent=2) + "\n")

        # Pixels still match; the geometry hash must not.
        result = harness.validate_scenario(scenario)
        assert not result.passed
        assert result.sidecar_mismatch is True
        assert result.page_diffs is not None
        assert all(d.diff_pixels == 0 for d in result.page_diffs), "pixels must still match"
    finally:
        harness.close()
        shutil.rmtree(harness.reference_dir, ignore_errors=True)


def _diff_summary(result) -> str:
    if not result.page_diffs:
        return f"pages {result.pages_actual}/{result.pages_expected}"
    parts = []
    for d in result.page_diffs:
        if d.diff_pixels == -1:
            parts.append(f"p{d.page}: MISSING")
        elif d.diff_pixels > 0:
            parts.append(f"p{d.page}: {d.diff_percent}% diff")
    return ", ".join(parts)


@pytest.mark.parametrize(
    "version",
    [
        "v4.1.0",
        "v4.2.0.dev1",
        "v_1.2_3",
        "VERSION-2024",
        "v4.2.0",
    ],
)
def test_validate_version_dir_name_accepts_safe(version: str) -> None:
    """Safe version strings (letters, digits, dots, underscores, hyphens) pass."""
    assert validate_version_dir_name(version) == version


@pytest.mark.parametrize(
    "version",
    ["..\\..\\evil", "../../evil", "a/b", "v:1", "i c", "v?1", "abc/xyz"],
)
def test_validate_version_dir_name_rejects_traversal(version: str) -> None:
    """Traversal and separator-laden version strings are rejected."""
    with pytest.raises(ValueError):
        validate_version_dir_name(version)


def test_validation_harness_rejects_traversal_version() -> None:
    """ValidationHarness refuses to construct a version dir outside references/."""
    with pytest.raises(ValueError):
        ValidationHarness("..\\..\\escape")
    with pytest.raises(ValueError):
        ValidationHarness("../../escape")


def test_compare_versions_rejects_traversal() -> None:
    """compare_versions validates both versions before touching the filesystem."""
    harness = ValidationHarness()
    try:
        with pytest.raises(ValueError):
            harness.compare_versions("..\\..\\a", "v4.1.0")
        with pytest.raises(ValueError):
            harness.compare_versions("v4.1.0", "b/c")
    finally:
        harness.close()
