"""Shared pytest fixtures and helpers for validation tests.

This module provides common fixtures used across validation test files to reduce
duplication and ensure consistent test setup.
"""

from pathlib import Path

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
    return LANDSCAPE_PRESET["default"]["1080p"][2]


@pytest.fixture(scope="session")
def layout_config():
    """Provide a default LayoutConfig for testing."""
    return LANDSCAPE_PRESET["default"]["1080p"][0]


@pytest.fixture(scope="session")
def text_config():
    """Provide a default TextConfig for testing."""
    return LANDSCAPE_PRESET["default"]["1080p"][1]


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
