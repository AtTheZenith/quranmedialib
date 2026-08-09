# API Reference

This document provides a detailed summary of the public API for `QuranMediaLib`.

## Exception Hierarchy

The library uses a custom exception hierarchy to allow users to catch specific categories of errors. All exceptions inherit from `QuranMediaLibError`.

| Exception | Inherits From | Description |
| :--- | :--- | :--- |
| `QuranMediaLibError` | `Exception` | Base exception for all library errors. |
| `ResourceError` | `QuranMediaLibError` | Raised when a resource (font, database) is missing or inaccessible. |
| `DatabaseError` | `QuranMediaLibError` | Raised when a database operation fails. |
| `WorkflowError` | `QuranMediaLibError` | Raised when a workflow fails during processing. |
| `ValidationError` | `QuranMediaLibError`, `ValueError` | Raised when input or configuration validation fails. |
| `LayoutError` | `QuranMediaLibError` | Raised when a layout operation fails. |

## Data Management

### `DatabaseManager`
The central thread-safe singleton for all data retrieval.

| Method | Signature | Returns | Description |
| :--- | :--- | :--- | :--- |
| `get_verses_from_surah` | `(surah: int)` | `list[str]` | All Arabic verses in a surah. |
| `get_verse` | `(surah: int, ayah: int)` | `str` | Single Arabic verse text. |
| `get_wbw_from_verse` | `(surah: int, ayah: int)` | `list[str]` | Word-by-word translations for a verse. |
| `get_translation_from_surah` | `(surah: int)` | `list[str]` | All verse translations in a surah. |
| `get_translations_from_verse_range` | `(surah, start, end, translation_name=None)` | `list[str]` | Range of translations. Raises `ValidationError` if any ayah is missing. |
| `close` | `()` | `None` | Closes all active SQLite connections. |
| `minimize_caches` | `()` | `None` | Clears internal LRU caches to free memory. |

## Rendering Workflows

All workflows inherit from `BaseWorkflow` and accept a single `Preset` object in `__init__`. They implement `get_iterator(...)` which yields `list[Image.Image]` (pages).

### Workflow Detail

#### `VerseWorkflow`
Renders a single verse with translation.
- **`get_iterator(surah: int, ayah: int, translations: list[str], annotate: bool = True)`**
- **Raises**: `ValidationError` (out of range), `WorkflowError` (no text found).

#### `VerseRangeWorkflow`
Bulk render for a range of verses.
- **`get_iterator(surah: int, translations: list[list[str]], start_ayah: int = 1, end_ayah: int | None = None, **kwargs)`**
- **Keyword Args**:
    - `annotate` (bool, default `True`): Render word-by-word annotations.
    - `separate_translations` (bool, default `False`): Translation on separate pages.
    - `parallel` (bool, default `True`): Use `ParallelRenderer`.
    - `output_dir` (str | None): Save images to disk instead of returning them.
    - `filename_prefix` (str): Prefix for saved files.
- **Raises**: `ValidationError` (invalid range).

#### `SurahWorkflow`
Processes entire surahs automatically.
- **`get_iterator(surah: int, annotate: bool = True, separate_translations: bool = False, **kwargs)`**
- **Keyword Args**:
    - `parallel` (bool, default `True` if verses > 10).
    - `output_dir` (str | None): Save images to disk.
    - `filename_prefix` (str): Prefix for saved files.
- **Raises**: `ValidationError` (invalid surah), `WorkflowError` (no verses found).

#### `IsolateWordsWorkflow`
Isolates individual words for study tools.
- **`get_iterator(surah: int, verse_words: list[str], translations: list[str], ayah: int | None = None, wbw_translations: list[str] | None = None, **kwargs)`**
- **Keyword Args**:
    - `annotate` (bool, default `True`).
    - `highlight_style` (str, default `"#b#ffd700ff#"`).
- **Raises**: `ValidationError` (empty words or out of range).

## Configuration & Presets

### Presets
Pre-configured settings for different media formats.
- `LANDSCAPE_PRESET`: 16:9 aspect ratio.
- `STORY_PRESET`: 9:16 aspect ratio.
- `SQUARE_PRESET`: 1:1 aspect ratio.

**Usage:** `preset = LANDSCAPE_PRESET["default"]["1080p"]`

### Layout Types (New in v4.0)
Resolution-independent layout primitives inspired by Roblox UDim2.
- `UDim2(scale_x, offset_x, scale_y, offset_y)`: Scale+offset pair. Resolved as `parent_dim * scale + offset`.
- `AnchorPoint(x, y)`: Pivot point (0-1 per axis). `(0.5, 0.5)` = center, `(0, 0)` = top-left.
- `ResolvedRect(left, top, width, height)`: Absolute pixel rectangle after resolution.
- `PresetLayout(position, size, anchor)`: Layout element definition using UDim2 + AnchorPoint.

### Config Classes
- `Preset`: Unified 4-field config container (`frame`, `word`, `verse`, `text`). Access configs as `preset.frame`, `preset.word`, etc.
- `FrameConfig`: Frame-level settings (`background_color`, `max_width`, `image_height`, `aspect_ratio`). No layout logic — position is handled by `PresetLayout` + `LayoutEngine`.
- `VerseConfig`: Verse-level layout settings (word spacing, row spacing, max rows per page, balanced wrapping).
- `WordConfig`: Font size, colors, and word-level padding.
- `TextConfig`: Translation font and style settings. Rich text tags (`#b|i|bi#<hex6|hex8>#text#`) are parsed per segment; stray `#` characters not forming a valid tag log a warning. Set `ignore_non_token_hashtags=True` to silence that warning and render stray hashtags as literal text. `balanced_wrapping` (default `True`) enables paragraph balancing, selected by `balancing_mode`.
- `FontResource`: Handles font file resolution.

### Text Balancing (`BalancingMode`, v4.2.0)
`BalancingMode` drives how multi-line translation text is wrapped. Select it via
`TextConfig.balancing_mode` or `VerseConfig.balancing_mode` (default `SMOOTH`).

| Mode | Notes |
|------|-------|
| `BalancingMode.FORWARD` | Greedy max-fill; always valid, negligible cost. |
| `BalancingMode.SMOOTH` | Global minimal-line, flattest-split "pyramid" (default). Context-limited to `PYRAMID_MAX_WORDS` (256); larger inputs fall back to greedy. |
| `BalancingMode.KNUTH_PLASS` | Optimized guarded quadratic-slack DP. |
| `BalancingMode.TEX` | Micro-optimized faithful TeX port; byte-identical to TeX for small inputs, budget-aborts fall back to greedy. |

**Fallback contract**: every solver returns break indices, `[]` (single line), or
`None` (infeasible). Greedy is the unconditional fallback — when a solver returns
`None`, `balance_lines_pyramid` runs greedy and logs a reason with the first 100
chars of source text; it returns `None` only when greedy itself is unsatisfiable
(a line budget that even one-word-per-line cannot meet).

### Output & Input Limits
Untrusted text is bounded before any measurement so it cannot drive memory,
layout-solver, or canvas cost unbounded:
- `MAX_TEXT_CHARS` (10,000) — `get_timage` raises `ValueError` if longer.
- `MAX_TEXT_WORDS` (1,000) — `get_timage` raises `ValueError` if a text has more tokens.
- `MAX_CANVAS_DIMENSION` (5,000) — a rendered text canvas exceeding this is clamped with a `WARNING` (an over-wide single word cannot force a decompression-bomb image allocation).

### Layout Engine (`modules/layout_engine.py`)
New in v4.0. Resolves `PresetLayout` definitions to absolute pixel rects for any frame size.

| Function / Class | Signature | Returns | Description |
| :--- | :--- | :--- | :--- |
| `LayoutEngine` | `(frame_width, frame_height)` | — | Resolves layout elements for a given frame size. |
| `engine.resolve_rect` | `(elem: PresetLayout)` | `ResolvedRect` | Resolves one element to absolute pixel coords. |
| `LayoutGuide` | `(arabic, translation)` | — | Container holding `ResolvedRect` for both content areas. |
| `build_layout_guide` | `(aspect_ratio, frame_w, frame_h)` | `LayoutGuide` | Convenience: builds a full guide from preset layout definitions. |

## Layout & Composition

### `VImage` (`modules/vimage.py`)
Verse image layout engine that groups rendered word items into right-to-left rows and computes page breaks.

| Method | Signature | Returns | Description |
| :--- | :--- | :--- | :--- |
| `get_page_chunk` | `(start_index: int, max_rows: int)` | `tuple[list, int]` | Computes rows from remaining items (per-page). Returns `(rows, items_consumed)`. |
| `layer` | `(base_image, x, y, word_config, rows_to_render)` | `None` | Renders word rows directly onto the frame canvas at the given position. |

**Constructor** (v4): `VImage(items, verse_config, content_width)` — takes `int` content width instead of a config object.

### `Frame` (`modules/frame.py`)
Frame composition class that manages the RGBA surface and handles layering of images and Layerable objects.

**Constructor** (v4): `Frame(width, height, background_color=(0,0,0,0))`

| Method | Signature | Returns | Description |
| :--- | :--- | :--- | :--- |
| `layer_at` | `(image, rect: ResolvedRect, text_color=None, **kwargs)` | `None` | Places content at a resolved pixel rect. Handles `Layerable`, `'L'` masks, `RGBA` composites. |
| `render` | `()` | `Image.Image` | Returns the final composed RGBA image. |

`Frame.layer()` (old v3 API) was removed in v4.0.0 — use `layer_at()` with a `ResolvedRect` instead.

## Utility Tools

### `ParallelRenderer`
Distributed rendering engine for CPU-intensive tasks.
- `map(func, iterable)` $\rightarrow$ Returns an iterator of processed results.
- `map_batches(func, tasks, max_batch_size=None)` $\rightarrow$ Groups tasks into optimal batches (natural chunking via `ceil(tasks / workers)`). Supply `max_batch_size` to cap per-worker memory (used internally by `_bytes_mode_max_batch` for the IPC bytes path).

### `worker_heartbeat(process_limit_mb=256.0)`
Per-process RSS check called every 10 verses inside worker functions. Raises `MemoryLimitExceededError` (crashes the worker) if current process RSS exceeds the per-process limit. No try/except wrapper — unhandled exception terminates the worker immediately.

### `check_process_memory(limit_mb=256.0)`
Underlying enforcement function. Raises `MemoryLimitExceededError` if `get_current_rss_mb() > limit_mb`.

### `MemoryMonitor`
Synchronous peak aggregate-RSS tracker. Context manager; tracks peak between `__enter__` and `__exit__`. Used in tests to measure memory impact — no enforcement, no background thread.

### `_bytes_mode_max_batch(chunk, frame_cfg)`
Module-level function in `verse_range.py`. Calculates safe per-batch verse count for the bytes IPC path, bounding `batch_results` accumulation to ~80% of the per-process 256MB limit. Adapts to frame dimensions (e.g., 8 verses at 1080p, 2 at 2160p).
