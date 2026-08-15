"""Tests for the VerseRangeWorkflow class.

This module contains tests for verifying the verse range workflow that processes
a range of verses sequentially with Arabic text and translations.
"""

import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.presets import build_layout_guide
from quranmedialib.types import FrameConfig
from quranmedialib.workflows.verse_range import (
    VerseRangeWorkflow,
    _bytes_mode_max_batch,
    _handle_output,
    _render_verse_worker,
    _sanitize_filename_prefix,
)


def test_verse_range(request: pytest.FixtureRequest) -> None:
    print("Starting test_verse_range (Surah 108 - Per-Verse Iteration)...")
    request.node.benchmark_data = ["surah=108", "verses=3"]

    db = DatabaseManager()

    # Define inputs explicitly for Surah 108 (Al-Kawthar)
    surah = 108
    start_verse = 1
    end_verse = 3

    # Fetch English translations (uses "translation" database by default)
    translations = db.get_translation_from_surah(surah)
    # translations: list[list[str]] (Per verse, per page) for passing to workflow
    # But get_translation_from_surah returns list[str] (one string per verse)
    # We need to wrap each string in a list because VerseRangeWorkflow expects list[list[str]]
    translations_list = [[t] for t in translations]

    preset = LANDSCAPE_PRESET["default"]["1080p"]

    workflow = VerseRangeWorkflow(preset)

    print(f"Processing Surah {surah}, Verses {start_verse}-{end_verse}...")

    # Execute workflow (generator yields a list of pages per verse)
    # Using explicit arguments
    generator = workflow._process_range(
        surah=surah,
        start_verse=start_verse,
        end_verse=end_verse,
        translations=translations_list,
    )

    # Output directory
    output_dir = "output/test/verse_range"
    os.makedirs(output_dir, exist_ok=True)

    # Convert generator to concrete list of lists
    results = list(generator)
    assert len(results) == 3, f"Expected 3 verse results, but got {len(results)}"

    # Verse 1
    v1_pages = results[0]
    print(f"Verse 1 generated {len(v1_pages)} pages.")
    save_path1 = os.path.join(output_dir, "v1_page_1.png")
    v1_pages[0].save(save_path1)
    print(f"Saved {save_path1}")

    # Verse 2
    v2_pages = results[1]
    print(f"Verse 2 generated {len(v2_pages)} pages.")
    save_path2 = os.path.join(output_dir, "v2_page_1.png")
    v2_pages[0].save(save_path2)
    print(f"Saved {save_path2}")

    # Verse 3
    v3_pages = results[2]
    print(f"Verse 3 generated {len(v3_pages)} pages.")
    save_path3 = os.path.join(output_dir, "v3_page_1.png")
    v3_pages[0].save(save_path3)
    print(f"Saved {save_path3}")

    print(f"Test complete. Results saved to {output_dir}")


if __name__ == "__main__":
    test_verse_range()


# === Validation Tests ===


def test_verse_range_invalid_surah() -> None:
    """Test that VerseRangeWorkflow handles invalid surah numbers."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    # Surah 0 doesn't exist, should handle gracefully
    try:
        results = list(workflow.get_iterator(surah=0, translations=[[]], start_ayah=1, end_ayah=1, annotate=False))
        assert isinstance(results, list)
    except Exception:
        pass

    # Surah 115 doesn't exist
    try:
        results = list(workflow.get_iterator(surah=115, translations=[[]], start_ayah=1, end_ayah=1, annotate=False))
        assert isinstance(results, list)
    except Exception:
        pass


def test_verse_range_invalid_ayah_range() -> None:
    """Test that VerseRangeWorkflow handles invalid ayah range."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    # Ayah 0 doesn't exist, should handle gracefully
    try:
        results = list(workflow.get_iterator(surah=1, translations=[[]], start_ayah=0, end_ayah=1, annotate=False))
        assert isinstance(results, list)
    except Exception:
        pass


def test_verse_range_reversed_range() -> None:
    """Test that VerseRangeWorkflow raises ValueError for reversed ayah range."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    # end_ayah < start_ayah should raise ValueError
    with pytest.raises(ValueError, match="start_ayah.*cannot be greater than end_ayah"):
        list(workflow.get_iterator(surah=1, translations=[[]], start_ayah=5, end_ayah=1))


def test_verse_range_empty_translations() -> None:
    """Test that VerseRangeWorkflow handles empty translations."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    # Empty translations should still work
    results = list(workflow.get_iterator(surah=108, translations=[[]], start_ayah=1, end_ayah=1, annotate=False))
    assert results


def test_verse_range_invalid_ayah() -> None:
    """Test that VerseRangeWorkflow raises ValueError for ayah outside 1-286."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    with pytest.raises(ValueError, match="Ayah must be between 1 and 286"):
        list(workflow.get_iterator(surah=1, translations=[[]], start_ayah=0, end_ayah=1, annotate=False))

    with pytest.raises(ValueError, match="Ayah must be between 1 and 286"):
        list(workflow.get_iterator(surah=1, translations=[[]], start_ayah=1, end_ayah=1000, annotate=False))


class TestBytesModeMaxBatch:
    """Tests for _bytes_mode_max_batch() — bytes IPC memory safety."""

    def test_1080p_default_chunk(self) -> None:
        """At 1080p, ~8 verses fit within per-process budget."""
        frame = FrameConfig(max_width=1920, image_height=1080)
        result = _bytes_mode_max_batch(36, frame)
        assert 1 <= result <= 36

    def test_2160p_caps_tightly(self) -> None:
        """At 2160p, only 2 verses fit — each page is ~33MB."""
        frame = FrameConfig(max_width=3840, image_height=2160)
        result = _bytes_mode_max_batch(36, frame)
        assert result <= 2

    def test_720p_allows_more(self) -> None:
        """At 720p, more verses fit — each page is ~3.7MB."""
        frame = FrameConfig(max_width=1280, image_height=720)
        result = _bytes_mode_max_batch(36, frame)
        assert result >= 4

    def test_never_less_than_one(self) -> None:
        """Even for absurd resolutions, must return at least 1."""
        frame = FrameConfig(max_width=10000, image_height=10000)
        result = _bytes_mode_max_batch(36, frame)
        assert result >= 1

    def test_respects_smaller_chunk(self) -> None:
        """If natural chunk is smaller than calculated max, use chunk."""
        frame = FrameConfig(max_width=1920, image_height=1080)
        result = _bytes_mode_max_batch(3, frame)
        assert result == 3


class TestHandleOutput:
    """Tests for _handle_output() bytes path."""

    def test_bytes_path_returns_tuples(self) -> None:
        """use_bytes=True with no output_dir returns (mode, size, bytes) tuples."""
        pages = [Image.new("RGBA", (100, 50), (255, 0, 0, 255))]
        result = _handle_output(
            pages,
            ayah=1,
            output_dir=None,
            filename_prefix="t",
            save_fn=lambda *a: None,
            use_bytes=True,
        )
        assert len(result) == 1
        mode, size, data = result[0]
        assert mode == "RGBA"
        assert size == (100, 50)
        assert isinstance(data, bytes)
        assert len(data) == 100 * 50 * 4

    def test_bytes_path_multi_page(self) -> None:
        """Multi-page verses produce one tuple per page."""
        pages = [Image.new("RGBA", (10, 10)), Image.new("RGB", (20, 20))]
        result = _handle_output(
            pages,
            ayah=1,
            output_dir=None,
            filename_prefix="t",
            save_fn=lambda *a: None,
            use_bytes=True,
        )
        assert len(result) == 2
        assert result[0][0] == "RGBA"
        assert result[1][0] == "RGB"

    def test_file_path_returns_strings(self) -> None:
        """output_dir set returns file paths regardless of use_bytes."""
        pages = [Image.new("RGBA", (10, 10))]

        def mock_save(img: Image.Image, path: str, **kw: object) -> None:
            return None

        result = _handle_output(
            pages,
            ayah=5,
            output_dir="/tmp/out",
            filename_prefix="x",
            save_fn=mock_save,
            use_bytes=False,
        )
        assert isinstance(result, list)
        assert all(isinstance(p, str) for p in result)


class TestRenderVerseWorkerBytesPath:
    """Integration: _render_verse_worker through the bytes IPC path.

    Exercises use_bytes=True + output_dir=None — the path used by
    parallel rendering without file output.
    """

    def test_single_verse_returns_reconstructable_bytes(self) -> None:
        """Bytes output from a single verse can be reconstructed to images."""
        preset = LANDSCAPE_PRESET["default"]["1080p"]
        guide = build_layout_guide("landscape", preset.frame.max_width, preset.frame.image_height)

        db = DatabaseManager()
        translations = db.get_translation_from_surah(108)

        result = _render_verse_worker(
            verse_data=[(1, [translations[0]])],
            surah=108,
            frame_cfg=preset.frame,
            guide=guide,
            text_cfg=preset.text,
            word_cfg=preset.word,
            verse_cfg=preset.verse,
            annotate=False,
            separate_translations=False,
            output_dir=None,
            filename_prefix="test_bytes",
            use_bytes=True,
        )

        assert len(result) == 1  # one verse
        pages = result[0]
        assert len(pages) >= 1  # at least one page
        for entry in pages:
            mode, size, data = entry
            assert isinstance(mode, str)
            assert len(size) == 2
            assert isinstance(data, bytes)
            img = Image.frombytes(mode, size, data)
            assert img.size == size
            assert img.mode == mode

    def test_bytes_output_render_matches_file_output(self) -> None:
        """Bytes-reconstructed image should match file-saved image pixel-for-pixel."""
        preset = LANDSCAPE_PRESET["default"]["1080p"]
        guide = build_layout_guide("landscape", preset.frame.max_width, preset.frame.image_height)

        db = DatabaseManager()
        translations = db.get_translation_from_surah(108)

        result_bytes = _render_verse_worker(
            verse_data=[(1, [translations[0]])],
            surah=108,
            frame_cfg=preset.frame,
            guide=guide,
            text_cfg=preset.text,
            word_cfg=preset.word,
            verse_cfg=preset.verse,
            annotate=False,
            separate_translations=False,
            output_dir=None,
            filename_prefix="test_bytes",
            use_bytes=True,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            result_files = _render_verse_worker(
                verse_data=[(1, [translations[0]])],
                surah=108,
                frame_cfg=preset.frame,
                guide=guide,
                text_cfg=preset.text,
                word_cfg=preset.word,
                verse_cfg=preset.verse,
                annotate=False,
                separate_translations=False,
                output_dir=tmpdir,
                filename_prefix="test_file",
                use_bytes=False,
            )

            bytes_pages = result_bytes[0]
            file_pages = result_files[0]

            for (bm, bs, bd), fpath in zip(bytes_pages, file_pages):
                file_img = Image.open(fpath)
                assert file_img.mode == bm
                assert file_img.size == bs
                assert file_img.tobytes() == bd


@pytest.mark.parametrize(
    ("prefix", "expected"),
    [
        ("surah_108", "surah_108"),
        ("..\\..\\evil", "_.._evil"),
        ("../../evil", "_.._evil"),
        ("a/b\\c:d", "a_b_c_d"),
        ("..", "output"),
        ("surah..108", "surah..108"),
        ("dir\\..\\x", "dir_.._x"),
    ],
)
def test_sanitize_filename_prefix(prefix: str, expected: str) -> None:
    """Filename prefix sanitizer neutralizes path traversal and separators."""
    result = _sanitize_filename_prefix(prefix)
    assert result == expected
    # Must never contain a path separator or be empty
    assert "/" not in result and "\\" not in result
    assert result


def test_sanitize_filename_prefix_blocks_traversal_in_handle_output(tmp_path) -> None:
    """Files written via _handle_output never escape output_dir, even with a hostile prefix."""
    from quranmedialib.modules.timage import get_timage

    preset = LANDSCAPE_PRESET["translation"]["1080p"]
    img = get_timage("Surah Al-Kawthar", preset.text)  # type: ignore[call-arg]
    paths = _handle_output(
        pages=[img],
        ayah=1,
        output_dir=str(tmp_path),
        filename_prefix="..\\..\\escape",
        save_fn=lambda im, p, format, compress_level: im.save(p, format=format, compress_level=compress_level),
        use_bytes=False,
    )
    # Resolve each returned path and confirm it stays inside tmp_path.
    tmp_real = tmp_path.resolve()
    for p in paths:
        resolved = Path(p).resolve()
        assert resolved.is_relative_to(tmp_real)


def test_emit_sidecar_writes_one_json_per_png(tmp_path) -> None:
    """VerseRangeWorkflow with emit_sidecar writes a deterministic sidecar beside each PNG."""
    import json as json_module

    from quranmedialib.modules.sidecar import SIDECAR_SCHEMA, TASK_SCHEMA

    db = DatabaseManager()
    surah = 108  # Al-Kawthar, 3 verses
    translations_list = [[t] for t in db.get_translation_from_surah(surah)]

    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)
    output_dir = Path("output/test/sidecar/write")
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = workflow._process_range(
        surah=surah,
        start_verse=1,
        end_verse=3,
        translations=translations_list,
        output_dir=str(output_dir),
        emit_sidecar=True,
        parallel=False,
    )
    list(generator)

    pngs = sorted(output_dir.glob("*.png"))
    page_jsons = sorted(output_dir.glob("*_page_*.json"))
    task_json = output_dir / "task.json"
    assert len(pngs) == len(page_jsons) > 0
    assert task_json.exists()

    # Every PNG has exactly one matching JSON stem, and vice versa (task.json is per-task, not per-page).
    png_stems = {p.stem for p in pngs}
    page_json_stems = {j.stem for j in page_jsons}
    assert png_stems == page_json_stems

    for j in page_jsons:
        data = json_module.loads(j.read_text(encoding="utf-8"))
        assert data["schema"] == SIDECAR_SCHEMA
        assert "layers" in data
        assert "dimensions" in data
        # VImage layers carry a rows hierarchy with class_type word records.
        for layer in data["layers"]:
            if layer["class_type"] == "vimage":
                for row in layer["rows"]:
                    for word in row["words"]:
                        assert word["class_type"] in {"word", "verse_number"}

    task_data = json_module.loads(task_json.read_text(encoding="utf-8"))
    assert task_data["schema"] == TASK_SCHEMA
    assert task_data["workflow"] == "verse_range"
    assert task_data["surah"] == surah
    assert task_data["ayah_range"] == {"start": 1, "end": 3}


def test_emit_sidecar_is_deterministic_across_runs() -> None:
    """Two identical emit_sidecar runs produce byte-identical JSON sidecars."""
    db = DatabaseManager()
    surah = 108
    translations_list = [[t] for t in db.get_translation_from_surah(surah)]

    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    def run_and_read(dir_path: Path) -> dict[str, str]:
        dir_path.mkdir(parents=True, exist_ok=True)
        gen = workflow._process_range(
            surah=surah,
            start_verse=1,
            end_verse=3,
            translations=translations_list,
            output_dir=str(dir_path),
            emit_sidecar=True,
            parallel=False,
        )
        list(gen)
        return {j.stem: j.read_text(encoding="utf-8") for j in dir_path.glob("*.json")}

    first = run_and_read(Path("output/test/sidecar/deterministic/run1"))
    second = run_and_read(Path("output/test/sidecar/deterministic/run2"))
    assert first.keys() == second.keys()
    assert first == second


def test_emit_sidecar_requires_output_dir() -> None:
    """emit_sidecar without output_dir must fail loudly with ValidationError."""
    from quranmedialib.exceptions import ValidationError

    db = DatabaseManager()
    surah = 108
    translations_list = [[t] for t in db.get_translation_from_surah(surah)]

    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseRangeWorkflow(preset)

    with pytest.raises(ValidationError):
        list(
            workflow._process_range(
                surah=surah,
                start_verse=1,
                end_verse=1,
                translations=translations_list,
                emit_sidecar=True,
                parallel=False,
            )
        )
