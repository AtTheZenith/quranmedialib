"""Tests for presets module — structure and consistency."""

import pytest

from quranmedialib import LANDSCAPE_PRESET, SQUARE_PRESET, STORY_PRESET
from quranmedialib.types import LayoutConfig, TextConfig, WordConfig

RESOLUTIONS = ["720p", "1080p", "1440p", "2160p"]
MODES = ["default", "arabic", "translation"]
ALL_PRESETS = [
    ("LANDSCAPE", LANDSCAPE_PRESET),
    ("STORY", STORY_PRESET),
    ("SQUARE", SQUARE_PRESET),
]


@pytest.mark.parametrize("preset_name,preset", ALL_PRESETS)
def test_presets_all_keys(preset_name: str, preset: dict) -> None:
    """Test that all presets have 'default', 'arabic', 'translation' modes."""
    for mode in MODES:
        assert mode in preset, f"{preset_name} missing mode '{mode}'"


@pytest.mark.parametrize("preset_name,preset", ALL_PRESETS)
def test_presets_all_resolutions(preset_name: str, preset: dict) -> None:
    """Test that all modes have 720p/1080p/1440p/2160p."""
    for mode in MODES:
        for res in RESOLUTIONS:
            assert res in preset[mode], f"{preset_name}['{mode}'] missing resolution '{res}'"


@pytest.mark.parametrize("preset_name,preset", ALL_PRESETS)
def test_presets_produce_valid_configs(preset_name: str, preset: dict) -> None:
    """Test that all configs have positive dimensions."""
    for mode in MODES:
        for res in RESOLUTIONS:
            preset_obj = preset[mode][res]
            assert isinstance(preset_obj.frame, LayoutConfig)
            assert isinstance(preset_obj.text, TextConfig)
            assert isinstance(preset_obj.word, WordConfig)
            assert preset_obj.frame.max_width > 0, f"{preset_name} {mode} {res}: max_width <= 0"
            assert preset_obj.frame.image_height > 0, f"{preset_name} {mode} {res}: image_height <= 0"
            assert preset_obj.word.font_size > 0, f"{preset_name} {mode} {res}: font_size <= 0"
            assert preset_obj.word.max_rows_per_page > 0, f"{preset_name} {mode} {res}: max_rows_per_page <= 0"


def test_preset_story_1080p_max_rows() -> None:
    """Test that STORY_PRESET default 1080p has consistent max_rows_per_page."""
    preset = STORY_PRESET["default"]["1080p"]
    assert preset.verse.max_rows_per_page == 8, (
        f"STORY_PRESET['default']['1080p'] max_rows_per_page={preset.verse.max_rows_per_page}, "
        f"expected 8 to match 720p/1440p/2160p"
    )



def test_preset_square_1080p_font_sizes() -> None:
    """Test that SQUARE_PRESET translation font sizes scale across resolutions."""
    font_sizes = []
    for res in RESOLUTIONS:
        preset = SQUARE_PRESET["translation"][res]
        font_sizes.append(preset.text.font_size)
    for i in range(len(font_sizes) - 1):
        assert font_sizes[i] < font_sizes[i + 1], (
            f"SQUARE_PRESET['translation'] font_size should increase with resolution: got {font_sizes}"
        )


def test_presets_consistent_scaling() -> None:
    """Test that canvas dimensions scale consistently across resolutions."""
    mode = "default"
    for preset_name, preset in ALL_PRESETS:
        widths = []
        heights = []
        for res in RESOLUTIONS:
            preset_obj = preset[mode][res]
            widths.append(preset_obj.frame.max_width)
            heights.append(preset_obj.frame.image_height)
        for i in range(len(widths) - 1):
            assert widths[i] <= widths[i + 1], f"{preset_name} width should not decrease: {widths}"
        for i in range(len(heights) - 1):
            assert heights[i] <= heights[i + 1], f"{preset_name} height should not decrease: {heights}"
