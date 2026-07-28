"""QuranMediaLib check module.

Backward compatibility guarantee: once a version's reference directory is
created (references/v<X.Y.Z>/), it will always be loadable by future versions
of this module.

Commands:
    python -m quranmedialib.check test       # Full suite: pixel compare + unit tests
    python -m quranmedialib.check update     # (Re)generate reference images
    python -m quranmedialib.check list       # List canonical scenarios
    python -m quranmedialib.check compare    # Cross-version pixel comparison
    python -m quranmedialib.check benchmark  # Run performance benchmarks
"""

from quranmedialib.check._harness import (
    CANONICAL_SCENARIOS,
    PageDiff,
    Scenario,
    ScenarioMetrics,
    ValidationHarness,
    ValidationResult,
)

__all__ = [
    "CANONICAL_SCENARIOS",
    "PageDiff",
    "Scenario",
    "ScenarioMetrics",
    "ValidationHarness",
    "ValidationResult",
]
