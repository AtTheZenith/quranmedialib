---
trigger: always_on
---

# Quran Media Library – Repository Style Guide

This is a **repo‑specific** style guide for AI agents working on this project.
It complements PEP 8 and Ruff, and is based on existing code.

---

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
- Functions should describe actions clearly (`get_wimage`, `annotate_word`, `frame`, `glow`, `pad`).
- Private helpers use a leading underscore (`_normalize_items`, `_group_items_into_rows`).

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
- `Padding` — NamedTuple with `.top`, `.bottom`, `.left`, `.right` fields
- `SurahNumber` — Validated surah number (1–114)
- `AyahNumber` — Valid ayah number (1–286)
- `WordIndex` — Word position index

### 3.2 Enums

- `HorizontalAlignment` — `LEFT`, `CENTER`, `RIGHT`
- `VerticalAlignment` — `TOP`, `CENTER`, `BOTTOM`

### 3.3 NamedTuples

- `Padding(top, bottom, left, right)` — 4-directional padding with named fields
- `ParsedSegment(flags, hex_color, content, original_had_tag)` — Pre-parsed translation segment

---

## 4. Configuration and Dataclasses

- Use `@dataclass(frozen=True)` for immutable configuration objects.
- Use `init=False` with custom `__init__` for complex initialization (e.g., `WordConfig`, `TextConfig`).
- Use `__post_init__` for type coercion (e.g., string → enum conversion).
- Provide factory classmethods for common patterns:
  - `from_packaged()` — For bundled assets resolved via `importlib.resources`
  - `from_path()` — For user-provided external paths
- Document dataclass attributes with `Attributes:` section in class docstring.

### 4.1 Current Configuration Types

- `FontResource` — Font file reference with metadata
- `DatabaseConfig` — Verse-by-verse database configuration
- `WbwDatabaseConfig` — Word-by-word database configuration (extends DatabaseConfig)
- `LayoutConfig` — Canvas sizing, padding, alignment, offsets
- `WordConfig` — Word rendering config (font sizes, spacing, colors)
- `TextConfig` — Translation text rendering config
- `WordItem` — Data transmission type combining image + text for layout
- `StyledWord` — Word with styling for rich text rendering
- `Line` — Collection of styled words representing a text line

---

## 5. Function Design and API Behavior

- Prefer keyword arguments for parameters such as sizes, colors, paddings, and spacings.
- Provide sensible defaults:
  - Font sizes and colors in `get_wimage`.
  - Padding and color in `pad`.
  - `strength` and `radius` in `glow`.
  - Layout options in `frame`.
- Keep public functions short by delegating to private helpers.
- Use `**kwargs` for extensibility in workflow methods; document expected keys in docstring.
- Functions that process images generally return new objects instead of mutating inputs.

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
    annotate: bool = True,
    separate_translations: bool = False,
    **kwargs,
) -> Iterator[list[Image.Image]]:
    """Processes an entire surah and yields lists of generated images (pages).

    Args:
        surah: Surah number (1-114).
        annotate: Whether to annotate words with word-by-word translations.
        separate_translations: If True, render translations on separate pages.
        **kwargs:
            - annotate: bool (default: True) - Whether to annotate words.
            - separate_translations: bool (default: False) - Separate translation pages.

    Yields:
        list[Image.Image]: List of page images for each verse in the surah.

    Raises:
        ValueError: If no verses are found for the given surah.
    """
```

### 6.2 Dataclass Docstring Pattern

```python
@dataclass(frozen=True)
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

### 7.1 Ruff Configuration

- **Line length**: 120 characters (configured in `pyproject.toml`)
- **Target version**: Python 3.13
- **Lint rules**: `["E", "F", "I"]` (pycodestyle errors, pyflakes, isort)
- **Quote style**: Double quotes
- **Indent style**: Space (4 spaces)
- **Line ending**: LF

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
- **Padding**: Use `Padding` NamedTuple with named fields (`.top`, `.bottom`, `.left`, `.right`).
- **Glow**:
  - Strength ≤ 0 or radius ≤ 0 returns a copy of the original image.
  - RGBA images: glow composed **behind** content with alpha compositing.
  - Opaque images: glow uses screen‑style blending for vibrancy.
- **Mode semantics**: Preserve image mode (RGBA/RGB); document any conversions.

### 8.2 Layout (Framing Words)

- `frame` lays out word images into right‑to‑left rows and pages.
- `_group_items_into_rows` ensures first item always placed to avoid infinite loops.
- `_apply_stop_sign_adjustment` uses `QURANIC_STOP_SIGNS` to adjust page breaks.
- `_render_page` canvas is RGBA with transparent background; words placed RTL.

### 8.3 Text Rendering

- **Rich text formatting**: Use tag-based format (`#b#` bold, `#i#` italic, `#hex#` color).
- **Wrapping**: Balanced inverted-pyramid wrapping for centered visual distribution.
- **Font loading**: Use variable fonts with weight axis when possible; fallback to stroke simulation.

---

## 9. Workflows

### 9.1 Overview

Workflows are high-level classes that orchestrate complex rendering operations. They inherit from `BaseWorkflow` and implement `get_iterator()`.

### 9.2 Current Workflows

- **`VerseWorkflow`**: Render single verse with Arabic text and translation
- **`SurahWorkflow`**: Process entire surah (extends VerseRangeWorkflow)
- **`VerseRangeWorkflow`**: Process verse ranges with combined/separate translations
- **`IsolateWordsWorkflow`**: Isolate individual words in layout context

### 9.3 Workflow Pattern

```python
class MyWorkflow(BaseWorkflow):
    def get_iterator(
        self,
        param: int,
        option: bool = True,
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """One-line summary.

        Args:
            param: Description.
            option: Description.
            **kwargs:
                - key: type (default: value) - Description.

        Yields:
            list[Image.Image]: Description of yielded images.
        """
        # Implementation
        yield result
```

### 9.4 Workflow Conventions

- Accept configuration objects (`LayoutConfig`, `TextConfig`, `WordConfig`) in `__init__`.
- Return `Iterator[list[Image.Image]]` (list of pages per iteration).
- Use `**kwargs` for optional parameters to allow future extensibility.
- Delegate complex logic to private helper methods (e.g., `_process_range`, `_prepare_word_images`).

---

## 10. Presets System

### 10.1 Overview

Presets provide pre-configured layouts for common formats and resolutions.

### 10.2 Structure

```python
PRESET[mode][resolution] -> tuple[LayoutConfig, TextConfig, WordConfig]
```

- **Modes**: `"default"` (annotated + translation), `"arabic"` (annotated only), `"translation"` (translation only)
- **Resolutions**: `"720p"`, `"1080p"`, `"1440p"`, `"2160p"`

### 10.3 Available Presets

- `LANDSCAPE_PRESET` — 16:9 aspect ratio
- `STORY_PRESET` — 9:16 aspect ratio
- `SQUARE_PRESET` — 1:1 aspect ratio

### 10.4 Usage

```python
from quranmedialib import LANDSCAPE_PRESET

layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]
```

---

## 11. Database and Resources

### 11.1 DatabaseManager

- **Singleton pattern**: Uses `__new__` with thread-safe initialization (`_lock`).
- **Context manager**: Supports `with DatabaseManager() as db:` protocol.
- **Lifecycle**: Call `db.close()` when done; resets singleton for re-initialization.
- **Active connections**: Manages multiple named connections (quran, wbw, translation).

### 11.2 Database Configuration

- Use `DatabaseConfig.from_packaged()` for bundled databases.
- Use `DatabaseConfig.from_path()` for external database files.
- `WbwDatabaseConfig` extends `DatabaseConfig` with `word_id_col` field.

### 11.3 Resources

- Use `importlib.resources` for asset path resolution.
- `get_font_path(filename)` — Resolve packaged font file paths.
- `get_db_path(filename)` — Resolve packaged database file paths.

---

## 12. Error Handling and Logging

### 12.1 Logging Conventions

- Use `logging.getLogger(__name__)` pattern in each module.
- Log levels:
  - `logger.info()` — Normal operational messages
  - `logger.debug()` — Detailed debugging information
  - `logger.warning()` — Potential issues (e.g., font fallback)
  - `logger.error()` — Error conditions before raising exceptions

### 12.2 Exception Handling

- Use specific exception types (`ValueError`, `OSError`, `sqlite3.Error`).
- Provide meaningful error messages with context.
- Use `raise` or `raise ExceptionType("message")` — avoid bare `raise` without context.
- Log errors before raising for debugging.

### 12.3 Fallback Patterns

- Font loading: Try native variations → fallback to stroke simulation → warn user.
- Database queries: Validate inputs → raise `ValueError` with clear message.
- Image operations: Return copies instead of mutating; document behavior.

---

## 13. Development Commands

All development commands use `uv` for consistency:

```bash
# Run all tests
uv run -m pytest

# Run specific test file
uv run -m pytest tests/modules/test_annotation.py
# OR (shorthand)
uv run tests/modules/test_annotation.py

# Run tests with verbose output
uv run -m pytest -v

# Run tests matching keyword
uv run -m pytest -k "annotation"

# Lint with Ruff
uv run -m ruff check .

# Format with Ruff
uv run -m ruff format .

# Run demo script
uv run demo.py

# Run individual test module directly
uv run tests/modules/test_framer.py
```

---

## 14. Testing Conventions

### 14.1 Test Structure

- Tests live under `tests/` directory, mirroring source structure:
  - `tests/modules/` — Core module tests
  - `tests/workflows/` — Workflow tests
- Test files use `test_*.py` naming.
- Each test module can run standalone with `uv run tests/modules/test_*.py`.

### 14.2 Test Patterns

- Use descriptive test names (`test_color`, `test_glow`, `test_framer`).
- Use `assert` statements for programmatic verification.
- Image-producing tests save outputs under `./output/test/`.
- Use helper functions for common setup (e.g., `_create_default_word_config()`).
- Use `dataclasses.replace()` to create config variants.
- Use `pytest.mark.parametrize` for data-driven tests.

### 14.3 Database in Tests

- `DatabaseManager` is a singleton; tests share the same instance.
- Tests rarely call `db.close()` explicitly (rely on process exit).
- For stress tests, measure performance with `time.perf_counter()`.

### 14.4 Test Organization

```python
def test_feature() -> None:
    """One-line description."""
    # Setup
    # Exercise
    # Verify
    # Save output (for image tests)
```

---

## 15. Public API and Exports

### 15.1 Package-Level Exports

- `__init__.py` defines `__all__` for clean public API.
- Export commonly-used types, configs, presets, and workflows at package level.
- Users should import from top-level when possible:
  ```python
  from quranmedialib import DatabaseManager, VerseWorkflow, LANDSCAPE_PRESET
  ```

### 15.2 Module-Level Exports

- Individual modules should define `__all__` listing public functions.
- Private helpers use leading underscore (not exported).

### 15.3 Deep Imports

- Avoid deep imports when top-level export exists.
- Deep imports are acceptable for internal utilities or when top-level doesn't export it.

---

## 16. Script Entrypoints

- Use `demo.py` at project root for demonstration scripts.
- Protect entry with `if __name__ == "__main__":`.
- Run with `uv run demo.py`.
- Scripts should:
  - Instantiate the database manager.
  - Perform operations with clear progress messages.
  - Close the database before exit (use `try/finally`).

---

## 17. Do / Do‑Not Summary

### Do

- Use descriptive names (especially for parameters and long‑lived variables).
- Document padding and layout conventions explicitly.
- Keep public APIs thin and factor complex logic into private helpers.
- Use type hints consistently (`list[int]`, `A | B`, Python 3.13 `type` statements).
- Use Google-style docstrings with `Args:`, `Returns:`, `Yields:`, `Raises:` sections.
- Preserve image mode semantics and transparency behavior, documenting any conversions.
- Use `uv` for all development commands (`uv run`, `uv run -m pytest`, etc.).
- Use frozen dataclasses for configuration with factory methods.
- Use `Padding` NamedTuple instead of raw tuples.
- Import from package level when possible (`from quranmedialib import ...`).

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
