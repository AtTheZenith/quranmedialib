"""Shared pytest fixtures and helpers for validation tests.

This module provides common fixtures used across validation test files to reduce
duplication and ensure consistent test setup.
"""

import pytest
from PIL import Image

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.types import Padding, WordConfig


@pytest.fixture(scope="session")
def database_manager() -> DatabaseManager:
    """Provide a shared DatabaseManager instance for all tests."""
    return DatabaseManager()


@pytest.fixture(scope="session")
def word_config() -> WordConfig:
    """Provide a default WordConfig for testing."""
    return LANDSCAPE_PRESET["default"]["1080p"].word


@pytest.fixture(scope="session")
def layout_config():
    """Provide a default LayoutConfig for testing."""
    return LANDSCAPE_PRESET["default"]["1080p"].frame


@pytest.fixture(scope="session")
def text_config():
    """Provide a default TextConfig for testing."""
    return LANDSCAPE_PRESET["default"]["1080p"].text


@pytest.fixture
def dummy_rgba_image() -> Image.Image:
    """Create a simple RGBA image for testing."""
    return Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))


@pytest.fixture
def dummy_rgb_image() -> Image.Image:
    """Create a simple RGB image for testing."""
    return Image.new("RGB", (100, 100), color=(255, 0, 0))


@pytest.fixture
def default_padding() -> Padding:
    """Provide default padding for testing."""
    return Padding(10, 10, 10, 10)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command-line options for running benchmarks and heavy tests."""
    parser.addoption(
        "--benchmark",
        "--b",
        action="store_true",
        default=False,
        help="Run performance benchmarks (skipped by default)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Physically removes excluded tests from collection for a clean output.

    If --benchmark is provided:
        - Removes all standard tests (those NOT marked with 'benchmark').
    If --benchmark is NOT provided:
        - Removes all benchmark tests (those marked with 'benchmark').
    """
    if config.getoption("--benchmark"):
        # Exclusive Benchmark Mode: Remove standard tests
        items[:] = [item for item in items if "benchmark" in item.keywords]
    else:
        # Standard Mode: Remove benchmark tests
        items[:] = [item for item in items if "benchmark" not in item.keywords]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hooks into report generation to append test duration to the verbose output."""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        if parts := getattr(item, "benchmark_data", []):
            report.duration_str = f" [{report.duration:.2f}s | {', '.join(parts)}]"
        else:
            report.duration_str = f" [{report.duration:.2f}s]"


def pytest_report_teststatus(report, config):
    """Customizes the character/text shown in the status column."""
    if hasattr(report, "duration_str") and config.getoption("verbose") > 0:
        if report.passed:
            return "passed", "P", f"PASSED{report.duration_str}"
        if report.failed:
            return "failed", "F", f"FAILED{report.duration_str}"
    return None
