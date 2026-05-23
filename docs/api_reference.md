# API Reference

This document provides a high-level summary of the public API for `QuranMediaLib`. For detailed parameter descriptions, please refer to the docstrings in the source code.

## Data Management

### `DatabaseManager`
The central singleton for all data retrieval.
- `get_verses_from_surah(surah)` --> `list[str]`
- `get_verse(surah, ayah)` --> `str`
- `get_wbw_from_verse(surah, ayah)` --> `list[str]`
- `get_translation_from_surah(surah)` --> `list[str]`
- `close()` --> Closes all connections.

## Rendering Workflows

All workflows inherit from `BaseWorkflow` and implement `get_iterator(...)` which yields `list[Image.Image]` (pages).

| Workflow | Purpose | Key Parameters |
| :--- | :--- | :--- |
| `VerseWorkflow` | Single verse render | `surah`, `ayah`, `translations` |
| `VerseRangeWorkflow` | Bulk verse render | `surah`, `start_ayah`, `end_ayah`, `translations` |
| `SurahWorkflow` | Entire surah render | `surah`, `annotate`, `separate_translations` |
| `IsolateWordsWorkflow` | Word-by-word focus | `surah`, `verse_words`, `translations` |

## Configuration & Presets

### Presets
Pre-configured settings for different media formats.
- `LANDSCAPE_PRESET`: 16:9 aspect ratio.
- `STORY_PRESET`: 9:16 aspect ratio.
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
- `map(func, iterable)` --> Returns a list of processed results.

### `MemoryMonitor`
Context manager for tracking RSS memory usage during bulk processes.
