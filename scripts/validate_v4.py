"""Validation harness for v4.0.0 UDim2+AnchorPoint layout architecture.

Tests all workflow types with the new API and verifies basic output properties.
This is a structural smoke test, not a pixel comparison (v4 layout differs from v3).
"""

import os
import sys
import time

# Ensure we can import from the src directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PIL import Image

from quranmedialib import (
    DatabaseManager,
    IsolateWordsWorkflow,
    LANDSCAPE_PRESET,
    SQUARE_PRESET,
    STORY_PRESET,
    SurahWorkflow,
    VerseRangeWorkflow,
    VerseWorkflow,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "validate_v4")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _save_pages(pages: list[Image.Image], name: str) -> None:
    """Save a list of page images with a common prefix."""
    for i, page in enumerate(pages):
        path = os.path.join(OUTPUT_DIR, f"{name}_page_{i + 1}.png")
        page.save(path)


def validate_verse_workflow(db: DatabaseManager) -> int:
    """Test VerseWorkflow with landscape default preset."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseWorkflow(preset)
    pages = list(workflow.get_iterator(surah=1, ayah=1, translations=["In the name of Allah"]))
    assert len(pages) > 0, "VerseWorkflow should produce at least one page"
    _save_pages(pages[0], "verse_default_1080p")
    return len(pages[0])


def validate_surah_workflow(db: DatabaseManager) -> int:
    """Test SurahWorkflow with a short surah (Al-Fatiha)."""
    preset = LANDSCAPE_PRESET["default"]["720p"]
    workflow = SurahWorkflow(preset)
    pages_list = list(workflow.get_iterator(surah=1, annotate=True))
    assert len(pages_list) > 0, "SurahWorkflow should produce at least one verse of pages"
    return len(pages_list)


def validate_verse_range_workflow(db: DatabaseManager) -> int:
    """Test VerseRangeWorkflow with story preset."""
    preset = STORY_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)
    translations = [["Muhammad is the Messenger of Allah"], ["And those with him are fierce against disbelievers"]]
    pages_list = list(workflow.get_iterator(surah=48, translations=translations, start_ayah=29, end_ayah=29))
    assert len(pages_list) > 0, "VerseRangeWorkflow should produce pages"
    return len(pages_list)


def validate_isolate_words_workflow(db: DatabaseManager) -> int:
    """Test IsolateWordsWorkflow with square preset."""
    preset = SQUARE_PRESET["default"]["1440p"]
    workflow = IsolateWordsWorkflow(preset)
    pages_list = list(workflow.get_iterator(
        surah=1,
        verse_words=["بِسْمِ", "ٱللَّهِ", "ٱلرَّحْمَـٰنِ", "ٱلرَّحِيمِ"],
        translations=["In the name of Allah, the Most Gracious, the Most Merciful"],
        ayah=1,
    ))
    assert len(pages_list) > 0, "IsolateWordsWorkflow should produce pages"
    return len(pages_list)


def validate_all_presets(db: DatabaseManager) -> int:
    """Verify all preset configurations produce output for a single verse."""
    scenarios = [
        (LANDSCAPE_PRESET, "landscape"),
        (STORY_PRESET, "story"),
        (SQUARE_PRESET, "square"),
    ]
    modes = ["default", "arabic", "translation"]
    resolutions = ["720p", "1080p", "1440p", "2160p"]
    count = 0
    for preset_dict, aspect_name in scenarios:
        for mode in modes:
            for res in resolutions:
                preset = preset_dict[mode][res]
                workflow = VerseWorkflow(preset)
                translation_text = "A test translation"
                if mode == "arabic":
                    translation_text = ""  # Arabic mode uses transparent text
                pages = list(workflow.get_iterator(surah=112, ayah=1, translations=[translation_text]))
                assert len(pages) > 0, f"Preset {aspect_name}/{mode}/{res} should produce pages"
                count += 1
    return count


def main() -> int:
    """Run all validation scenarios."""
    db = DatabaseManager()
    try:
        scenarios = [
            ("VerseWorkflow (default, 1080p)", validate_verse_workflow),
            ("SurahWorkflow (Al-Fatiha, 720p)", validate_surah_workflow),
            ("VerseRangeWorkflow (story, 1080p)", validate_verse_range_workflow),
            ("IsolateWordsWorkflow (square, 1440p)", validate_isolate_words_workflow),
            ("All presets (36 combinations)", validate_all_presets),
        ]

        passed = 0
        failed = 0
        start_time = time.perf_counter()

        for name, func in scenarios:
            try:
                result = func(db)
                print(f"  PASS  {name} ({result} pages)")
                passed += 1
            except Exception as e:
                print(f"  FAIL  {name}: {e}")
                import traceback
                traceback.print_exc()
                failed += 1

        elapsed = time.perf_counter() - start_time
        total = passed + failed
        print(f"\n{'='*50}")
        print(f"Results: {passed}/{total} passed in {elapsed:.2f}s")
        print(f"Output: {OUTPUT_DIR}")
        return 0 if failed == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
