"""Exhaustive functional testing for all package presets.

Validates that every combination of Preset (Landscape, Story, Square),
Mode (Default, Arabic, Translation), and Resolution actually works
and produces valid images with expected dimensions.
"""

import pytest

from quranmedialib import LANDSCAPE_PRESET, SQUARE_PRESET, STORY_PRESET, VerseWorkflow

# Collect all preset sets
PRESET_SETS = {"LANDSCAPE": LANDSCAPE_PRESET, "STORY": STORY_PRESET, "SQUARE": SQUARE_PRESET}

# Resolutions and Modes to test
RESOLUTIONS = ["720p", "1080p", "1440p", "2160p"]
MODES = ["default", "arabic", "translation"]


@pytest.mark.parametrize("preset_name, preset_set", PRESET_SETS.items())
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("res", RESOLUTIONS)
def test_preset_execution(preset_name, preset_set, mode, res) -> None:
    """Verify that every preset-mode-res combination can render a verse."""
    try:
        layout, text, word = preset_set[mode][res]
    except KeyError:
        pytest.skip(f"Preset {preset_name} does not support mode={mode} res={res}")
        return

    # Use Surah 108:1 for a quick check
    workflow = VerseWorkflow(layout, text, word)

    # We don't save output here to stay fast, just ensure no exceptions
    # and check result structure
    results = list(workflow.get_iterator(surah=108, ayah=1, translations=["Test Translation"]))

    assert len(results) > 0, f"No pages yielded for {preset_name}-{mode}-{res}"
    pages = results[0]
    assert len(pages) > 0, f"Empty page list for {preset_name}-{mode}-{res}"

    # Verify dimensions match LayoutConfig
    img = pages[0]
    assert img.width == layout.max_width
    assert img.height == layout.image_height


def test_preset_definitions_completeness() -> None:
    """Ensure PRESET_SETS contain all expected keys."""
    for name, pset in PRESET_SETS.items():
        assert "default" in pset
        assert "arabic" in pset
        assert "translation" in pset

        for mode in MODES:
            for res in RESOLUTIONS:
                assert res in pset[mode], f"Missing {res} in {name}-{mode}"
