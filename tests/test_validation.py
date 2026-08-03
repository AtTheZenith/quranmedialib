"""Validation tests: lock rendering contracts against version-specific reference data.

Each test validates that the current library code produces output matching a
specific version's reference images. New versions add new parametrize entries.
"""

from __future__ import annotations

import pytest

from quranmedialib.check import CANONICAL_SCENARIOS, ValidationHarness

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
