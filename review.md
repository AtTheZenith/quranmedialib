# Code Review: feat/input_validation (v2.0.0)

## 📋 Review Summary
Significant performance and architecture upgrade. The introduction of `ParallelRenderer`, `MemoryMonitor`, and asynchronous I/O is well-executed and critical for the v2.0.0 milestone. The library is now much more robust for bulk processing.

## 🔍 General Feedback
- **Hardware Awareness**: Excellent use of `os.cpu_count()` and `psutil` for scaling.
- **Resource Safety**: Heartbeat and cache flushing mechanisms are professional-grade.
- **Validation**: Good shift towards `ValidationError` and centralized range checks.

---

## 🛠️ Issues & Suggested Fixes

### 1. [HIGH] Security: Path Traversal in Workflows
`output_dir` in `VerseRangeWorkflow` and `SurahWorkflow` is used without validation. Users could pass arbitrary paths (e.g., `../../etc/passwd`).
- **Location**: `src/quranmedialib/workflows/verse_range.py`
- **Fix**: Implement the same path-tree validation seen in `demo.py` at the workflow level.

### 2. [MEDIUM] Logic: Separate Translation Consistency
`_render_verse_worker` reimplements separate translation logic instead of calling `_render_separate_translation_pages`. It also uses `alpha_composite` without checking if the canvas is RGBA, which might cause errors if the preset changes.
- **Location**: `src/quranmedialib/workflows/verse_range.py`
- **Fix**: Refactor `_render_separate_translation_pages` into a static method or standalone utility that both the workflow and worker can use.

### 3. [LOW] Efficiency: Redundant `os.makedirs`
`os.makedirs(output_dir, exist_ok=True)` is called inside the loop for every verse in `_render_verse_worker`.
- **Location**: `src/quranmedialib/workflows/verse_range.py`
- **Fix**: Move `os.makedirs` outside the `for i, (ayah, verse_translations) in enumerate(verse_data):` loop.

### 4. [LOW] Maintenance: Constant Duplication
Validation constants (`MIN_SURAH`, `MAX_SURAH`, etc.) are duplicated between `database_manager.py` and `base.py`.
- **Location**: `src/quranmedialib/database_manager.py`, `src/quranmedialib/workflows/base.py`
- **Fix**: Move these constants to `src/quranmedialib/types.py` or a dedicated `constants.py`.

### 5. [LOW] Performance: Serial Byte Overhead
When `parallel=False`, `_process_range` still calls `_render_verse_worker` which converts images to bytes and back.
- **Location**: `src/quranmedialib/workflows/verse_range.py`
- **Fix**: Bypass byte conversion if not using multi-processing.
