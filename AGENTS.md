---
trigger: always_on
---

# Quran Media Library – Repository Style Guide

This is a **repo‑specific** style guide for AI agents working on this project.
It complements PEP 8 and Ruff, and is based on existing code.

**Engineering Standards**: Write code that a senior engineer would be proud to maintain.
Optimize for correctness first, then performance—never sacrifice clarity for cleverness.
Security is not an afterthought; it is engineered into every layer.

## Workflow Rule: Baseline Performance Check

**Before starting any feature work**, fetch the baseline speed of the existing codebase:

```powershell
uv run -m pytest; uv run -m pytest --benchmark
```

**Stop immediately if you encounter any errors** before proceeding with feature work.

**Ensure all changes meet these criteria:**

- No regressions in performance (compare against baseline)
- No regressions in security
- No regressions in functionality (all tests pass)

### Performance Baseline Protocol

**Before adding any new constraint (monitoring, capping, checkpointing):**

1. Check v3 baseline behavior first — it used `output_dir` (file-based render), natural chunking, every-10-verse flush, no SHA-256 in benchmark.
2. Profile the overhead of the constraint on the full Al-Baqarah benchmark (~286 verses at 1080p) before committing.
3. If overhead >1% of total runtime, reconsider the approach.

**Known anti-patterns (do not repeat):**

- `max_batch_size=5` — added ~0.5s (58 IPC rounds instead of ~12). Use `ceil(tasks / workers)` as the default.
- Per-verse `get_current_rss_mb()` + `worker_heartbeat()` — added ~0.5s. Check every 10 verses; the extra resolution never caught a spike that the 10-verse check missed.
- SHA-256 in `benchmark_scenario()` — added ~3s. Only compute hashes during `update_references`, from saved files, outside timing.
- `render_scenario()` collecting all pages into a list — caused 3.7GB main-process RSS. Use `_iter_pages()` generator (yield one-at-a-time) for validate and update paths.

---

## 0. Engineering Principles

### 0.1 Performance and Optimization

- **Profile before optimizing**: Measure first, optimize second. Use `@pytest.mark.benchmark` for hot paths.
- **Memory efficiency**: Use `__slots__` on frequently instantiated classes (`StyledWord`, `Line`).
- **Caching strategy**: Cache at the appropriate layer:
  - `@lru_cache` for deterministic pure functions (database queries, font loading)
  - `@functools.cache` when arguments are hashable and memoization aids repeated calls
  - Invalidate caches explicitly when underlying data changes (`minimize_caches()`)
- **Batch processing**: Use `map_batches()` to chunk tasks matching worker count. Default to `ceil(tasks / workers)`. Never hardcode `max_batch_size` below the natural chunk unless per-worker memory limits force it.
- **Streaming over accumulation**: Use generators (`yield`) instead of collecting all pages into a list. A single 1080p verse is ~6MB — accumulating 286 verses in the main process causes 3.7GB RSS.
- **Lazy evaluation**: Use `LazyTranslationImages` to defer expensive image generation until needed.
- **SQLite tuning**: Enable `SQLITE_MMAP_SIZE` (256MB) for faster reads; use `json_group_array()` for aggregations.
- **Throttled monitoring**: Check memory every 10 verses during bulk rendering to avoid OOM crashes. Per-iteration monitoring adds measurable overhead; the extra resolution has never caught a spike that the 10-verse check missed.

### 0.2 Security Considerations

- **Never trust external input**: Validate all paths, configs, and user data at boundaries.
- **Path traversal prevention**: Use `_ensure_within_working_dir()` with `realpath` to block symlink attacks.
- **`unsafe_paths` guard**: Require explicit opt-in for paths outside working directory; never default to True.
- **`trust_config` guard**: Validate SQL identifiers; reject custom table/column names by default.
- **Resource limits**: Enforce `MAX_FONT_SIZE` to prevent decompression bomb attacks.
- **Dual-inheritance exceptions**: `ValidationError` inherits from both `QuranMediaLibError` and `ValueError`—catch accordingly.
- **Working directory isolation**: Cache working directory lazily; never allow path escaping.

### 0.3 Code Clarity and Maintainability

- **Zero surprise**: If code behavior is not obvious from reading it, document it. If obvious, do not document.
- **Self-documenting code**: Prefer descriptive names over comments. A well-named variable removes the need for a comment.
- **Explicit over implicit**: Return new image objects; document mutations. Use keyword arguments for clarity.
- **Fail fast and loud**: Validate inputs early with clear error messages. Raise explicit exceptions rather than returning invalid state or None. Users prefer loud, clear failures over silent quality degradation.
- **Single responsibility**: Each function does one thing well. If describing it requires "and", split it.
- **Linear flow**: Prefer straight-line code over clever abstractions. Clever code is rarely correct on first try.

### 0.4 Defensive API Design

- **Immutable by Default**: Use `frozen=True` for all configuration dataclasses.
- **Explicit Opt-in for Danger**: Use flags like `unsafe_paths` or `trust_config` to explicitly mark boundary-crossing operations.
- **Fail Fast**: Validate inputs at the very first entry point of the public API to prevent deep-stack failures.
- **Resource Capping**: Enforce hard limits on canvas dimensions and font sizes to prevent OOM/DoS attacks.

### 0.5 High-Performance Image Pipelines

- **Mask-First Rendering**: Render text as `'L'` mode masks first, then colorize/composite in a single pass to minimize expensive RGBA operations.
- **Sub-pixel Precision**: Use float values for widths and positions to prevent cumulative rounding errors in long lines.
- **Memory-Aware Parallelism**: When using `ParallelRenderer`, monitor aggregate RSS and explicitly clear caches (`clear_rendering_caches`) to avoid OOM during bulk processing.
- **Thread-Local Resources**: Use `threading.local()` for database connections and other non-thread-safe handles to ensure stability under high concurrency.

### 0.6 The libcurl Standard

- **Absolute Utility**: Focus exclusively on providing a robust, predictable tool.
- **Zero Noise**: Avoid marketing fluff, branding, or "corporate" language in all documentation and communication.
- **Technical Precision**: Prioritize exactness and clarity over accessibility or "friendliness."
- **Tool and Manual**: The project is a tool and its documentation is its manual. No unnecessary preamble or postamble.

## 1. Imports and Modules

- Order imports: standard library → third‑party (PIL) → local modules (`quranmedialib.*`), separated by blank lines.
- Keep imports explicit; avoid wildcards (`*`).
- `__future__` imports (such as `annotations`) go at the very top.
- Module‑level constants are in `UPPER_SNAKE_CASE` (for example, `QURANIC_STOP_SIGNS`).
- Use `TYPE_CHECKING` guard for type-only imports to avoid circular dependencies:

  ```python
  from typing import TYPE_CHECKING
  
  if TYPE_CHECKING:
      from quranmedialib.types import LayoutConfig
  ```

---

## 2. Naming

- **Avoid abbreviations** for anything long‑lived or non‑trivial.
  - Good: `database_manager`, `word_images`, `annotated_images`.
  - Acceptable: short loop indices (`i`, `j`) in very small scopes.
- Use:
  - `snake_case` for functions, methods, variables, and parameters.
  - `PascalCase` for classes.
  - `UPPER_SNAKE_CASE` for constants.
- Functions should describe actions clearly (`get_wimage`, `annotate_words`, `glow`, `pad`).
- Private helpers use a leading underscore (`_normalize_items`, `_greedy_pack`).

### 2.1 Frame vs Canvas

"Frame" is the word for canvas in this project (multimedia-oriented — think picture frame, not UI frame). `Frame` is the RGBA surface that content layers onto. All dimension variables use `frame_*` prefix (`frame_width`, `frame_h`), never `canvas_*`. The PIL-level `canvas` parameter in Layerable methods is the exception (PIL convention).

---

## 3. Types and Signatures

- Use type hints on **all** functions (public and private).
- Prefer built‑in generics (`list[int]`, `tuple[int, int]`) and union operator syntax (`A | B`).
- Use Python 3.13 `type` statement for type aliases:

  ```python
  type Color = tuple[int, int, int] | tuple[int, int, int, int]
  type SurahNumber = Annotated[int, range(1, 115)]
  type AyahNumber = Annotated[int, range(1, 287)]
  ```

- For images, accept and return PIL types explicitly (`Image.Image`).
- Functions that process images generally return new image objects instead of mutating inputs.

### 3.1 Type Aliases (Current)

- `Color` — RGBA or RGB color tuple
- `Padding` — NamedTuple with `.top`, `.bottom`, `.left`, `.right` fields (Project Standard Order: top, bottom, left, right)
- `SurahNumber` — Validated surah number (1–114)
- `AyahNumber` — Validated ayah number (1–286)
- `WordIndex` — Word position index (`int`)
- `FontSize` — Validated font size (1–`MAX_FONT_SIZE`)

### 3.2 Enums

- `HorizontalAlignment` — `LEFT`, `CENTER`, `RIGHT`
- `VerticalAlignment` — `TOP`, `CENTER`, `BOTTOM`

### 3.3 NamedTuples

- `Padding(top, bottom, left, right)` — 4-directional padding (Project Standard Order: top, bottom, left, right) with named fields and `.horizontal`/`.vertical` properties

### 3.4 Text Rendering Types (Not Dataclasses)

- `StyledWord` — Class with `__slots__` (text, font, color, width, height, ascent, is_transparent, simulate_bold) for memory-efficient rich text
- `Line` — Class with `__slots__` (words list, width, height) with `add_word()` method

---

## 4. Configuration and Dataclasses

- Use `@dataclass(frozen=True, slots=True)` for immutable configuration objects.
- Use `init=False` with custom `__init__` for complex initialization (e.g., `WordConfig`, `TextConfig`).
- Use `__post_init__` with `object.__setattr__` for type coercion and validation (frozen dataclasses require this).
- Provide factory classmethods for common patterns:
  - `from_packaged()` — For bundled assets resolved via `importlib.resources`
  - `from_path()` — For user-provided external paths (supports `unsafe_paths` and `trust_config` kwargs)
- Document dataclass attributes with `Attributes:` section in class docstring.

### 4.1 Current Configuration Types

- `FontResource` — Font file reference with metadata (`from_packaged`, `from_path` with `unsafe_paths`)
- `DatabaseConfig` — Verse-by-verse database configuration (`from_packaged`, `from_path` with `unsafe_paths`, `trust_config`)
- `WbwDatabaseConfig` — Word-by-word database configuration (extends DatabaseConfig with `word_id_col`)
- `LayoutConfig` — Canvas sizing, padding, alignment, offsets (has `content_width` and `available_height` properties)
- `FrameConfig` — Canvas composition settings (padding, alignment, background color)
- `VerseConfig` — Verse-level layout settings (word spacing, row spacing, max rows per page, balanced wrapping)
- `WordConfig` — Word rendering config (font sizes, spacing, colors, verse number config)
- `TextConfig` — Translation text rendering config (font sizes, colors, paths, highlight config)
- `WordItem` — Data transmission type combining image + text with precomputed width/height

### 4.2 Constants

- `MAX_FONT_SIZE` = 2000
- `MIN_SURAH` = 1, `MAX_SURAH` = 114
- `MIN_AYAH` = 1, `MAX_AYAH` = 286

---

## 5. Function Design and API Behavior

- Prefer keyword arguments for parameters such as sizes, colors, paddings, and spacings.
- Provide sensible defaults:
  - Font sizes and colors in `get_wimage`.
  - Padding and color in `pad`.
  - `strength` and `radius` in `glow`.
  - Layout options in `Frame` and `VImage`.
  - `rendered_width` and `rendered_height` kwargs in `Frame.layer()` for multi-page alignment.
- Keep public functions short by delegating to private helpers.
- Use `**kwargs` for extensibility in workflow methods; document expected keys in docstring.
- Functions that process images generally return new objects instead of mutating inputs.
- Use `@overload` decorator for functions with conditional return types (e.g., `annotation.py` — `annotate_words`, `annotate_words_with_texts`).
- Use `@functools.lru_cache` on expensive pure functions (e.g., database queries with `maxsize` parameter).
- Use `Self` type hint for `__enter__` return type in context managers.

---

## 6. Docstrings and Comments

- Use **Google-style** docstrings with explicit sections.
- Each public function must have:
  - One-line summary
  - `Args:` section documenting all parameters
  - `Returns:` section (or `Yields:` for generators)
  - `Raises:` section if exceptions are raised
- Private helpers should have concise docstrings with Args/Returns.
- Inline comments explain **why**, not just **what**.

### 6.1 Example Function Docstring

```python
def get_iterator(
    self,
    surah: int,
    ayah: int,
    translations: list[str],
    annotate: bool = True,
) -> Iterator[list[Image.Image]]:
    """Render a single verse with Arabic text and translation.

    Args:
        surah: Surah number (1-114).
        ayah: Ayah number (1-286).
        translations: List of translation strings, one per page.
        annotate: Whether to annotate words with word-by-word translations.

    Yields:
        list[Image.Image]: List of page images for the verse.

    Raises:
        ValidationError: If surah or ayah is out of range.
    """
```

### 6.2 Dataclass Docstring Pattern

```python
@dataclass(frozen=True, slots=True)
class LayoutConfig:
    """Stores canvas sizing and top-level layout offsets.

    Attributes:
        max_width: Total canvas width in pixels.
        image_height: Total canvas height in pixels.
        padding: Internal canvas margins (top, bottom, left, right).
    """
```

---

## 7. Formatting and Tooling

### 7.1 Ruff and Sourcery Configuration

- **Ruff**:
  - **Line length**: 120 characters (configured in `pyproject.toml`)
  - **Target version**: Python 3.13
  - **Lint rules**: `["E", "F", "I"]` (pycodestyle errors, pyflakes, isort)
  - **Quote style**: Double quotes
  - **Indent style**: Space (4 spaces)
  - **Line ending**: LF
  - **Fixable**: `["ALL"]`
- **Sourcery**:
  - Use Sourcery for advanced refactoring suggestions and complexity reduction.
  - Prioritize "Boring Code" over clever Sourcery suggestions if the latter increases cognitive load.

### 7.2 Formatting Rules

- Use parentheses for line wrapping (not backslashes).
- Single spaces around operators and after commas.
- Two blank lines between top-level functions and classes.
- Group related imports with blank lines between standard/third-party/local.
- Let Ruff handle import sorting and basic style issues.

---

## 8. Image, Layout, and Domain Conventions

### 8.1 Image Processing

- **Color**: Colorization is luminance‑based, preserving alpha; returns new image.
- **Padding**: Use `Padding` NamedTuple with named fields (`.top`, `.bottom`, `.left`, `.right`) following the Project Standard Order: (top, bottom, left, right).
- **Glow**:
  - Strength ≤ 0 or radius ≤ 0 returns a copy of the original image.
  - RGBA images: glow composed **behind** content with alpha compositing.
  - Opaque images: glow uses screen‑style blending for vibrancy.
- **Mode semantics**: `get_wimage` returns `'L'` mode images as masks (not RGBA); document any conversions.

### 8.2 Layout (VImage Composition)

- `VImage` is the verse image layout engine that implements RTL row packing (`_greedy_pack`), Descending Line Balancing (`_balance_rows`), and page chunking (`get_page_chunk`).
- `Frame` manages the RGBA canvas and handles layering of `VImage` objects onto pages (`Frame.layer()`).
- `get_page_chunk` computes rows per-page from remaining items, matching v2's per-page row computation behavior.
- `_apply_stop_sign_adjustment` uses `QURANIC_STOP_SIGNS` to adjust page breaks.
- `VImage.layer()` places rendered word rows onto the page canvas at computed positions.
- `QURANIC_STOP_SIGNS` — List of 7 Unicode characters used for Quranic stop sign detection in `vimage.py`.

### 8.3 Text Rendering

- **Rich text formatting**: Use tag-based format (`#b#` bold, `#i#` italic, `#hex#` color).
- **Wrapping**: Descending Line Balancing wrapping for centered visual distribution; greedy fallback available.
- **Font loading**: Use `modules/font_cache.py` with `get_font()` — LRU-cached font loading with variable weight axis support; fallback to stroke simulation.
- **Lazy rendering**: `LazyTranslationImages` implements `Sequence` ABC for deferred image generation.
- **Text layout module** (`modules/text_layout.py`):
  - `StyledWord`, `Line` — Memory-efficient types with `__slots__`
  - `balance_lines_pyramid()` — Core Descending Line Balancing algorithm (O(K log N log W))
  - `wrap_rich_text_greedy()` — Simple greedy line wrapping
  - `wrap_rich_text_balanced()` — Inverted pyramid balancing

---

## 9. Workflows

### 9.1 Overview

Workflows are high-level classes that orchestrate complex rendering operations. They inherit from `BaseWorkflow` (ABC) and implement `get_iterator()`.

### 9.2 Current Workflows

| Class | Inheritance | Purpose |
| ------- | ------------ | --------- |
| `BaseWorkflow` | ABC | Abstract base with config init, surah/ayah validation, `__repr__` |
| `VerseWorkflow` | BaseWorkflow | Single verse with Arabic + translation |
| `VerseRangeWorkflow` | BaseWorkflow | Range of verses with parallel processing, memory management, async I/O |
| `SurahWorkflow` | VerseRangeWorkflow | Entire surah, auto-fetches verses + translations, auto-enables parallel for >10 verses |
| `IsolateWordsWorkflow` | BaseWorkflow | Isolates individual words with highlight formatting |

### 9.3 Workflow Pattern

```python
class MyWorkflow(BaseWorkflow):
    def get_iterator(
        self,
        surah: int,
        ayah: int,
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """One-line summary.

        Args:
            surah: Description.
            ayah: Description.
            **kwargs:
                - key: type (default: value) - Description.

        Yields:
            list[Image.Image]: Description of yielded images.
        """
        # Implementation
        yield result
```

### 9.4 Workflow Signatures

**VerseWorkflow:**

```python
def get_iterator(surah: int, ayah: int, translations: list[str], annotate: bool = True) -> Iterator[list[Image.Image]]
```

**VerseRangeWorkflow:**

```python
def get_iterator(
    surah: int,
    translations: list[list[str]],
    start_ayah: int = 1,
    end_ayah: int | None = None,
    **kwargs,                    # annotate, separate_translations, parallel
) -> Iterator[list[Image.Image]]
```

**SurahWorkflow:**

```python
def get_iterator(
    surah: int,
    annotate: bool = True,
    separate_translations: bool = False,
    **kwargs,                    # parallel, output_dir, filename_prefix
) -> Iterator[list[Image.Image]]
```

**IsolateWordsWorkflow:**

```python
def get_iterator(
    surah: int,
    verse_words: list[str],
    translations: list[str],
    ayah: int | None = None,
    wbw_translations: list[str] | None = None,
    **kwargs,                    # annotate, highlight_style
) -> Iterator[list[Image.Image]]
```

### 9.5 Workflow Conventions

- Accept a single `Preset` object in `__init__` (contains `frame`, `word`, `verse`, `text` configs).
- Return `Iterator[list[Image.Image]]` (list of pages per iteration).
- Use `**kwargs` for optional parameters to allow future extensibility.
- Delegate complex logic to private helper methods (e.g., `_process_range`, `_prepare_word_images`).
- `VerseRangeWorkflow` supports `output_dir` parameter returning `Iterator[list[Image.Image] | list[str]]` (paths when output_dir set).
- `SurahWorkflow` auto-enables parallel processing for surahs with >10 verses.
- `IsolateWordsWorkflow` supports `highlight_style` kwarg for word highlighting format.

---

## 10. Presets System

### 10.1 Overview

Presets provide pre-configured layouts for common formats and resolutions. The builder uses 1080p as the reference resolution; all sizing parameters scale linearly with canvas height.

### 10.2 Structure

```python
PRESET[aspect_ratio][mode][resolution] -> Preset
```

- **Aspect ratios**: `"landscape"` (16:9), `"story"` (9:16), `"square"` (1:1)
- **Modes**: `"default"` (annotated + translation), `"arabic"` (annotated only), `"translation"` (translation only)
- **Resolutions**: `"720p"`, `"1080p"`, `"1440p"`, `"2160p"`

### 10.3 Available Presets

- `LANDSCAPE_PRESET` — 16:9 aspect ratio
- `STORY_PRESET` — 9:16 aspect ratio
- `SQUARE_PRESET` — 1:1 aspect ratio

### 10.4 Builder Function

```python
from quranmedialib.presets import build_preset

preset = build_preset("landscape", "default", 1920, 1080)
```

### 10.5 Font and Database Presets

- `FONT_HAFS`, `FONT_INTER`, `FONT_INTER_ITALIC` — `FontResource` instances
- `DATABASE_QURAN`, `DATABASE_EN_SAHIH`, `DATABASE_WBW_EN` — `DatabaseConfig`/`WbwDatabaseConfig` instances

### 10.6 Usage

```python
from quranmedialib import LANDSCAPE_PRESET

preset = LANDSCAPE_PRESET["default"]["1080p"]
```

---

## 11. Database and Resources

### 11.1 DatabaseManager

- **Singleton pattern**: Uses `__new__` with thread-safe initialization (`_lock`).
- **Context manager**: Supports `with DatabaseManager() as db:` protocol (returns `Self`).
- **Lifecycle**: Call `db.close()` when done; resets singleton for re-initialization. Has `minimize_caches()` method.
- **Active connections**: Manages multiple named connections (quran, wbw, translation).
- **Caching**: Uses `@lru_cache` on query methods (`get_verses_from_surah`, `get_verse`, `get_wbw_grouped_by_verse`, `get_translation_from_surah`).
- **JSON aggregation**: Uses `json_group_array()` for ordered word aggregation in queries.
- **Internal caches**: `_schema_cache`, `_query_cache` for performance.

### 11.2 Database Configuration

- Use `DatabaseConfig.from_packaged()` for bundled databases.
- Use `DatabaseConfig.from_path()` for external database files (supports `unsafe_paths`, `trust_config`).
- `WbwDatabaseConfig` extends `DatabaseConfig` with `word_id_col` field.

### 11.3 Resources

- Use `importlib.resources` for asset path resolution.
- `get_font_path(filename)` — Resolve packaged font file paths.
- `get_db_path(filename)` — Resolve packaged database file paths.

### 11.4 Path Security

- `_ensure_within_working_dir()` validates paths are within working directory tree.
- Uses `realpath` to prevent symlink traversal and prefix-matching bypasses.
- Working directory cached lazily on first use via `_get_working_dir()`.

---

## 12. Utility Modules

### 12.1 I/O (`utils/io.py`)

- `async_image_saver()` — Context manager for background image saving via `ThreadPoolExecutor`.
- Supports concurrent disk writes while rendering continues.

### 12.2 Memory (`utils/memory.py`)

- `MemoryMonitor` — Synchronous peak-RSS tracker (enter/exit only, no background thread).
- `get_current_rss_mb()` — Get current process RSS in MB.
- `get_aggregate_rss_mb()` — Get total RSS of all child processes.
- `check_process_memory()` — Raise if current process exceeds per-process limit (called by `worker_heartbeat`).
- `check_aggregate_memory()` — Raise if aggregate RSS exceeds workers × per-process limit (synchronous, called after each batch in `ParallelRenderer.map()`).
- `clear_rendering_caches()` — Clear LRU caches to free memory.
- `MemoryLimitExceededError` — Raised when memory limits are exceeded (not exported at package level).
- Memory-aware rendering with throttled checks (every 10 verses).

### 12.3 Parallel (`utils/parallel.py`)

- `ParallelRenderer` — Process/thread parallel rendering engine with `ExecutionMode` enum.
- `_PoolManager` — Singleton for persistent executor pools with `atexit` cleanup.
- `map_batches()` — Batch processing that chunks tasks to match worker count.
- `worker_heartbeat()` — Worker heartbeat signal for parent process monitoring.

### 12.4 Hardware Config (`config.py`)

- `CPU_COUNT` — Detected CPU count.
- `DEFAULT_WORKERS` — Default parallel worker count (= CPU_COUNT).
- `DEFAULT_IO_THREADS` — Default I/O thread count (min(4, CPU_COUNT)).
- `SQLITE_MMAP_SIZE` — SQLite memory-mapped read size (256MB).
- `DEFAULT_PROCESS_LIMIT_MB` — Per-process memory limit (768MB).
- `DEFAULT_AGGREGATE_LIMIT_MB` — Computed as `DEFAULT_WORKERS * DEFAULT_PROCESS_LIMIT_MB` (not hardcoded).
- `MEMORY_FLUSH_THRESHOLD_RATIO` — Cache flush threshold (0.8 = 80%).
- Memory enforcement is **synchronous**: `check_aggregate_memory()` runs in `ParallelRenderer.map()` after each batch result. No background monitor thread — no log spam. Breach raises `MemoryLimitExceededError` and kills the pipeline cleanly.

---

## 13. Exception Hierarchy

All exceptions are defined in `exceptions.py` (canonical source). Duplicate definitions also exist in `types.py` (lines 32-46) for backward compatibility but are not used internally:

```markdown
QuranMediaLibError (Exception)
├── ResourceError
├── DatabaseError
├── WorkflowError
├── ValidationError (also inherits from ValueError)
└── LayoutError
```

- Use specific exception types for different failure modes.
- Provide meaningful error messages with context.
- Log errors before raising for debugging.

---

## 14. Error Handling and Logging

### 14.1 Logging Conventions

- Use `logging.getLogger(__name__)` pattern in each module.
- Log levels:
  - `logger.info()` — Normal operational messages
  - `logger.debug()` — Detailed debugging information
  - `logger.warning()` — Potential issues (e.g., font fallback)
  - `logger.error()` — Error conditions before raising exceptions

### 14.2 Exception Handling

- Use specific exception types (`ValueError`, `OSError`, `sqlite3.Error`, or custom hierarchy).
- Provide meaningful error messages with context.
- Use `raise` or `raise ExceptionType("message")` — avoid bare `raise` without context.
- Fail loudly: raise explicit exceptions rather than returning invalid state or None. Log errors before raising for debugging.

### 14.3 Fallback Patterns

- Font loading: Try native variations → fallback to stroke simulation → warn user.
- Database queries: Validate inputs → raise `ValueError` with clear message.
- Image operations: Return copies instead of mutating; document behavior.
- Path validation: Working directory check → `ResourceError` if outside.

---

## 15. Environment

The agent is operating in a Windows environment using PowerShell 7 (`pwsh`) as the primary shell. `sqlite3` is available in the system `PATH`.

---

## 16. Development Commands

All development commands use `uv` for consistency.

### 16.1 Project Management

- **Add dependency**: `uv add <package>`
- **Sync environment**: `uv sync`
- **Re-lock dependencies**: `uv lock` (after manual `pyproject.toml` edits)
- **Manage Python versions**: `uv python install <version>` or `uv python pin <version>`
- **Run ephemeral tools**: `uvx <tool>`

### 16.2 Common Commands

```bash
# Full test suite (pixel validation + performance + unit tests)
uv run -m quranmedialib.check test

# Quick pixel validation only
uv run -m quranmedialib.check run

# Skip benchmarks during test
uv run -m quranmedialib.check test --no-benchmark

# (Re)generate reference images for a version
uv run -m quranmedialib.check update --version v4.1.0

# Cross-version pixel comparison
uv run -m quranmedialib.check compare v4.1.0 v4.2.0

# Run performance benchmarks
uv run -m quranmedialib.check benchmark

# List canonical validation scenarios
uv run -m quranmedialib.check list

# Direct pytest (for unit tests, not validation):
uv run -m pytest tests/modules/ -x -q

# Lint with Ruff
uv run -m ruff check .

# Format with Ruff
uv run -m ruff format .

# Refactor with Sourcery
uvx sourcery review . --disable low-code-quality --disable no-loop-in-tests --disable no-conditionals-in-tests

# Run demo script
uv run demo.py
```

---

## 17. Testing Conventions

### 17.1 Test Structure

- Tests live under `tests/` directory, mirroring source structure:
  - `tests/modules/` — Core module tests
  - `tests/workflows/` — Workflow tests
  - `tests/test_api_surface.py` — Public API verification
  - `tests/test_validation.py` — Versioned rendering contract tests (driven by `quranmedialib.check`)
  - `tests/conftest.py` — Shared pytest fixtures
- The primary test entrypoint is `uv run -m quranmedialib.check test` which wraps pixel validation + benchmarks + pytest unit tests.
- Each test module can run standalone with `uv run tests/modules/test_*.py`.

### 17.2 Test Patterns

- Use descriptive test names (`test_color`, `test_glow`, `test_vimage`).
- Use `assert` statements for programmatic verification.
- Image-producing tests save outputs under `./output/test/`.
- Use helper functions for common setup (e.g., `_create_default_word_config()`).
- Use `dataclasses.replace()` to create config variants.
- Use `pytest.mark.parametrize` for data-driven tests.
- Use `@pytest.mark.benchmark` for performance tests (skipped by default).

### 17.3 Database in Tests

- `DatabaseManager` is a singleton; tests share the same instance.
- Tests rarely call `db.close()` explicitly (rely on process exit).
- For stress tests, measure performance with `time.perf_counter()`.

### 17.4 Test Organization

```python
def test_feature() -> None:
    """One-line description."""
    # Setup
    # Exercise
    # Verify
    # Save output (for image tests)
```

---

## 18. Public API and Exports

### 17.1 Package-Level Exports

- `__init__.py` defines `__all__` for clean public API.
- Export commonly-used types, configs, presets, exceptions, and workflows at package level.
- Users should import from top-level when possible:

  ```python
  from quranmedialib import DatabaseManager, VerseWorkflow, LANDSCAPE_PRESET
  ```

### 17.2 Current `__all__` Exports

**Version:** `__version__`

**Type aliases:** `Color`, `Padding`, `SurahNumber`, `AyahNumber`, `WordIndex`

**Resource classes:** `FontResource`

**Database classes:** `DatabaseConfig`, `WbwDatabaseConfig`, `DatabaseManager`

**Config classes:** `WordItem`, `LayoutConfig`, `FrameConfig`, `VerseConfig`, `WordConfig`, `TextConfig`, `Preset`

**Enums:** `HorizontalAlignment`, `VerticalAlignment`

**Constants:** `MAX_FONT_SIZE`, `MIN_SURAH`, `MAX_SURAH`, `MIN_AYAH`, `MAX_AYAH`

**Text rendering types:** `StyledWord`, `Line`

**Exceptions:** `QuranMediaLibError`, `ResourceError`, `DatabaseError`, `WorkflowError`, `ValidationError`, `LayoutError`

**Font presets:** `FONT_HAFS`, `FONT_INTER`, `FONT_INTER_ITALIC`

**Database presets:** `DATABASE_QURAN`, `DATABASE_EN_SAHIH`, `DATABASE_WBW_EN`

**Layout presets:** `LANDSCAPE_PRESET`, `STORY_PRESET`, `SQUARE_PRESET`

**Workflows:** `VerseWorkflow`, `VerseRangeWorkflow`, `SurahWorkflow`, `IsolateWordsWorkflow`

### 17.3 Module-Level Exports

- Individual modules should define `__all__` listing public functions.
- Private helpers use leading underscore (not exported).

### 17.4 Deep Imports

- Avoid deep imports when top-level export exists.
- Deep imports are acceptable for internal utilities (`utils.*`) or when top-level doesn't export it.

---

## 19. Script Entrypoints

- Use `demo.py` at project root for demonstration scripts.
- Protect entry with `if __name__ == "__main__":`.
- Run with `uv run demo.py`.
- Scripts should:
  - Instantiate the database manager.
  - Perform operations with clear progress messages.
  - Close the database before exit (use `try/finally`).

---

## 20. Do / Do‑Not Summary

### Do

- Use descriptive names (especially for parameters and long‑lived variables).
- Document padding and layout conventions explicitly.
- Keep public APIs thin and factor complex logic into private helpers.
- Use type hints consistently (`list[int]`, `A | B`, Python 3.13 `type` statements).
- Use Google-style docstrings with `Args:`, `Returns:`, `Yields:`, `Raises:` sections.
- Preserve image mode semantics and transparency behavior, documenting any conversions.
- Use `uv` for all development commands (`uv run`, `uv run -m pytest`, etc.).
- Use frozen dataclasses with `slots=True` for configuration with factory methods.
- Use `Padding` NamedTuple instead of raw tuples.
- Import from package level when possible (`from quranmedialib import ...`).
- Use `object.__setattr__` in `__post_init__` for frozen dataclasses.
- Use `TYPE_CHECKING` guard for type-only imports to avoid circular dependencies.
- Use `@lru_cache` on expensive pure functions with appropriate `maxsize`.
- Use `__slots__` for memory-critical classes (`StyledWord`, `Line`).

### Do Not

- Introduce new abbreviations for core concepts (database, images, padding, spacing).
- Mix layout calculation, domain logic, and rendering in a single large function.
- Mutate input images silently without documenting this behavior.
- Leave database connections open after tests or scripts complete.
- Use deep imports when top-level exports exist.
- Use `Union[A, B]` syntax — prefer `A | B` (Python 3.13).
- Use `List[int]` or `Dict[str, int]` — prefer `list[int]`, `dict[str, int]`.
- Skip docstrings on private helpers — all functions should be documented.
- Hardcode magic numbers — use constants or configuration objects.
- Use `List`/`Dict` from `typing` — use built-in generics (Python 3.13).
- Hardcode `max_batch_size` below natural chunk — measure first, cap only if per-worker memory forces it.
- Add per-iteration monitoring without profiling overhead — throttle to every 10 verses.
- Compute SHA-256 hashes inside benchmark timing — only compute from saved files during reference update.
- Accumulate all pages in a list during validate/update — use generator (`_iter_pages`) to stream one-at-a-time.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **quranmedialib** (1732 symbols, 2937 relationships, 117 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/quranmedialib/context` | Codebase overview, check index freshness |
| `gitnexus://repo/quranmedialib/clusters` | All functional areas |
| `gitnexus://repo/quranmedialib/processes` | All execution flows |
| `gitnexus://repo/quranmedialib/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
