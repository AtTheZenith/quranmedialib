"""Validation tests: lock rendering contracts against version-specific reference data.

Each test validates that the current library code produces output matching a
specific version's reference images. New versions add new parametrize entries.
"""

from __future__ import annotations

import pytest

from quranmedialib.check import CANONICAL_SCENARIOS, ValidationHarness
from quranmedialib.check._harness import validate_version_dir_name

SUPPORTED_VERSIONS = ["v4.1.1"]


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
@pytest.mark.parametrize("scenario", CANONICAL_SCENARIOS, ids=lambda s: s.name)
def test_rendering_contract(version: str, scenario) -> None:
    """Validate current output matches version-specific reference images."""
    harness = ValidationHarness(version)
    try:
        result = harness.validate_scenario(scenario)
        assert result.passed, f"[{version}] {result.scenario}: " + (result.error or _diff_summary(result))
    finally:
        harness.close()


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
