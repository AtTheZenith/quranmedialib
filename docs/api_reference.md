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

All workflows inherit from `BaseWorkflow` and implement `get_iterator(...)` which yields `list[Image.Image]` (pages).

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

**Usage:** `layout, text, word = LANDSCAPE_PRESET["default"]["1080p"]`

### Config Classes
- `LayoutConfig`: Canvas size, padding, and alignment.
- `WordConfig`: Font size, colors, and word-level padding.
- `TextConfig`: Translation font and style settings.
- `FontResource`: Handles font file resolution.

## Utility Tools

### `ParallelRenderer`
Distributed rendering engine for CPU-intensive tasks.
- `map(func, iterable)` $\rightarrow$ Returns a list of processed results.

### `MemoryMonitor`
Context manager for tracking RSS memory usage during bulk processes.

