#!/usr/bin/env python3
"""Validation harness: renders scenarios and saves images for comparison.

Usage:
    # From main repo (v2.0.1):
    uv run scripts/validate_v3.py --version v2

    # From v3 worktree:
    uv run scripts/validate_v3.py --version v3
"""

from __future__ import annotations

import argparse
import json
import os

from quranmedialib import (
    LANDSCAPE_PRESET,
    SQUARE_PRESET,
    STORY_PRESET,
    DatabaseManager,
    IsolateWordsWorkflow,
    SurahWorkflow,
    VerseRangeWorkflow,
    VerseWorkflow,
)
from quranmedialib import __version__ as qml_version

# Scenario format: (surah, ayah_or_0, translations, annotate, aspect, mode, desc, workflow_type, resolution)
SCENARIOS: list[tuple[int, int, list[str], bool, str, str, str, str, str]] = [
    # === VerseWorkflow ===
    (1, 1, ["In the name of Allah, the Most Gracious, the Most Merciful."], True, "landscape", "default", "bismillah_annotated", "verse", "1080p"),
    (1, 1, ["In the name of Allah, the Most Gracious, the Most Merciful."], False, "landscape", "arabic", "bismillah_arabic", "verse", "1080p"),
    (108, 1, ["Indeed, We have granted you, [O Muhammad], al-Kawthar."], True, "landscape", "default", "kawthar_annotated", "verse", "1080p"),
    (112, 1, ["Say, He is Allah, [who is] One,"], True, "landscape", "default", "ikhlas_v1_annotated", "verse", "1080p"),
    (2, 255, ["Allah! There is no deity except Him, the Ever-Living, the Self-Sustaining."], True, "landscape", "default", "kursi_partial", "verse", "1080p"),
    (1, 1, [], True, "story", "default", "bismillah_story", "verse", "1080p"),
    (1, 1, [], True, "square", "default", "bismillah_square", "verse", "1080p"),
    (1, 1, ["In the name of Allah, the Most Gracious, the Most Merciful."], True, "landscape", "default", "bismillah_720p", "verse", "720p"),
    # === SurahWorkflow ===
    (108, 0, [], True, "landscape", "default", "surah_kawthar", "surah", "1080p"),
    (112, 0, [], True, "landscape", "default", "surah_ikhlas", "surah", "1080p"),
    # === VerseRangeWorkflow ===
    (108, 0, [], True, "landscape", "default", "range_kawthar", "verse_range", "1080p"),
    # === IsolateWordsWorkflow ===
    (108, 1, ["Indeed, We have granted you al-Kawthar."], True, "landscape", "default", "isolate_kawthar_v1", "isolate", "1080p"),
    # === SurahWorkflow with separate_translations ===
    (108, 0, [], True, "landscape", "default", "surah_kawthar_separate", "surah_separate", "1080p"),
]


def _resolve_preset(aspect: str, mode: str, resolution: str):
    presets = {"landscape": LANDSCAPE_PRESET, "story": STORY_PRESET, "square": SQUARE_PRESET}
    raw = presets[aspect][mode][resolution]
    if qml_version == "3.0.0":
        return raw, raw
    layout_config, text_config, word_config = raw
    return (layout_config, text_config, word_config), (layout_config, text_config, word_config)


def _make_workflow(workflow_class, preset_or_tuple, *args, **kwargs):
    if qml_version == "3.0.0":
        return workflow_class(preset_or_tuple, *args, **kwargs)
    layout_config, text_config, word_config = preset_or_tuple
    return workflow_class(layout_config, text_config, word_config, *args, **kwargs)


def render_scenarios(version: str, output_dir: str) -> list[dict]:
    os.makedirs(output_dir, exist_ok=True)
    results: list[dict] = []
    db = DatabaseManager()

    for surah, ayah, translations, annotate, aspect, mode, desc, wf_type, resolution in SCENARIOS:
        try:
            preset_or_tuple, _ = _resolve_preset(aspect, mode, resolution)

            if wf_type == "verse":
                workflow = _make_workflow(VerseWorkflow, preset_or_tuple)
                page_groups = list(workflow.get_iterator(surah=surah, ayah=ayah, translations=translations, annotate=annotate))
                flat_pages = page_groups[0] if page_groups else []

            elif wf_type == "surah":
                workflow = _make_workflow(SurahWorkflow, preset_or_tuple)
                # SurahWorkflow auto-fetches translations
                page_groups = list(workflow.get_iterator(surah=surah, annotate=annotate, separate_translations=False))
                flat_pages = []
                for g in page_groups:
                    flat_pages.extend(g)

            elif wf_type == "surah_separate":
                workflow = _make_workflow(SurahWorkflow, preset_or_tuple)
                page_groups = list(workflow.get_iterator(surah=surah, annotate=annotate, separate_translations=True))
                flat_pages = []
                for g in page_groups:
                    flat_pages.extend(g)

            elif wf_type == "verse_range":
                workflow = _make_workflow(VerseRangeWorkflow, preset_or_tuple)
                # Need one translation list per verse in range
                tr = []
                for v in range(1, 4):
                    tr.append([db.get_translation_from_verse(surah, v)])
                page_groups = list(workflow.get_iterator(surah=surah, translations=tr, start_ayah=1, end_ayah=3, annotate=annotate))
                flat_pages = []
                for g in page_groups:
                    flat_pages.extend(g)

            elif wf_type == "isolate":
                verse_words = db.get_verse(surah, ayah).split()
                wbw_dict = db.get_wbw_grouped_by_verse(surah)
                wbw = list(wbw_dict.get(ayah, []))
                workflow = _make_workflow(IsolateWordsWorkflow, preset_or_tuple)
                page_groups = list(workflow.get_iterator(
                    surah=surah,
                    verse_words=verse_words,
                    translations=translations,
                    ayah=ayah,
                    wbw_translations=wbw,
                    annotate=annotate,
                ))
                flat_pages = []
                for g in page_groups:
                    flat_pages.extend(g)

            else:
                raise ValueError(f"Unknown workflow type: {wf_type}")

            for i, page in enumerate(flat_pages):
                page.save(os.path.join(output_dir, f"{desc}_p{i}.png"))

            results.append({"scenario": desc, "pages": len(flat_pages), "status": "ok"})
            print(f"  OK  {desc}: {len(flat_pages)} page(s) [{wf_type}]")
        except Exception as e:
            results.append({"scenario": desc, "status": "error", "error": str(e)})
            print(f"  ERR {desc}: {e} [{wf_type}]")

    with open(os.path.join(output_dir, "results.json"), "w") as f:
        json.dump(results, f, indent=2)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Render validation scenarios for QuranMediaLib.")
    parser.add_argument("--version", choices=["v2", "v3"], required=True)
    args = parser.parse_args()

    output_dir = os.path.abspath(f"./output/validation/{args.version}")
    print(f"\nRendering {len(SCENARIOS)} scenarios ({args.version}) -> {output_dir}")
    render_scenarios(args.version, output_dir)
    print("Done.\n")


if __name__ == "__main__":
    main()
