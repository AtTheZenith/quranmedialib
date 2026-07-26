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
    - `highlight_style` (str, default `"#b#"`).
- **Raises**: `ValidationError` (empty words or out of range).

## Configuration & Presets

### Presets
Pre-configured settings for different media formats.
- `LANDSCAPE_PRESET`: 16:9 aspect ratio.
- `STORY_PRESET`: 9:16 aspect la...
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
- `TextConfig`: Translation font and style settings.
- `FontResource`: Handles font file resolution.

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

`layer()` (old API) is deprecated — use `layer_at()` with a `ResolvedRect` instead.

## Utility Tools

### `ParallelRenderer`
Distributed rendering engine for CPU-intensive tasks.
- `map(func, iterable)` $\rightarrow$ Returns a list of processed results.

### `MemoryMonitor`
Context manager for tracking RSS memory usage during bulk processes.

