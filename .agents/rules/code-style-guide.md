---
trigger: always_on
---

# Quran Media Library – Repository Style Guide

This is a **repo‑specific** style guide for AI agents working on this project.  
It complements PEP 8 and Ruff, and is based on existing code.

---

## 1. Imports and Modules

- Order imports: standard library modules → third‑party modules (such as wPIL) → local modules (`src.*.*`), separated by blank lines.
- Keep imports explicit; avoid wildcards.
- `__future__` imports (such as annotations) go at the very top.
- Module‑level constants are in `UPPER_SNAKE_CASE` (for example, `QURANIC_STOP_SIGNS`).

---

## 2. Naming

- **Avoid abbreviations** for anything long‑lived or non‑trivial.
  - Good: `database_manager`, `word_images`, `annotated_images`.
  - Acceptable: short loop indices (`i`, `j`) in very small scopes.
- Use:
  - `snake_case` for functions, methods, variables, and parameters.
  - `PascalCase` for classes.
  - `UPPER_SNAKE_CASE` for constants.
- Functions should describe actions clearly (`fetch_all_words_from_verse`, `annotate_word`, `get_wimage`, `frame`, `glow`, `pad`).
- Private helpers use a leading underscore (`_normalize_items`, `_group_items_into_rows`).

---

## 3. Types and Signatures

- Use type hints on all public functions and important helpers.
- Prefer built‑in generics (`list[int]`, `tuple[int, int]`) and union operator syntax (`A | B`).
- Introduce descriptive type aliases for frequently used tuples (`ColorType`, `PaddingType`).
- For images, accept and return PIL types explicitly (`Image.Image`).
- Functions that process images generally return new image objects instead of mutating inputs.

---

## 4. Function Design and API Behavior

- Prefer keyword arguments for parameters such as sizes, colors, paddings, and spacings.
- Provide sensible defaults:
  - Font sizes and colors in `get_wimage`.
  - Padding and color in `pad`.
  - `strength` and `radius` in `glow`.
  - Layout options (`max_rows_per_page`, `max_width`, `image_height`, `padding`, `word_spacing`, `row_spacing`) in `frame`.
- Keep public functions short by delegating to private helpers:
  - Example phases in framing:
    - Normalization (`_normalize_items`).
    - Row grouping (`_group_items_into_rows`).
    - Stop sign adjustments (`_apply_stop_sign_adjustment`).
    - Page rendering (`_render_page`).

---

## 5. Docstrings and Comments

- Use a clear module‑level docstring when the module is conceptually significant (`framer`, `wimage`).
- Each public function has:
  - A one‑line summary.
  - Parameter and return explanations.
  - Any relevant behavior notes (for example, handling transparency, performance caveats).
- Inline comments explain **why**, not just **what**:
  - Guards against infinite loops in layout.
  - Reasoning for glow compositing order.
  - Clarification of padding order.

---

## 6. Formatting (Ruff / PEP 8)

- Respect the configured line length (keep lines compact; use parentheses for wrapping).
- Use 4 spaces for indentation; no tabs.
- Use single spaces around operators and after commas.
- Group related imports and logical code blocks with a single blank line.
- Use two blank lines between top‑level functions and classes.
- Let Ruff handle:
  - Import sorting and unused imports.
  - Basic style issues (spacing, blank lines, etc.).

---

## 7. Image, Layout, and Domain Conventions

### 7.1 Image Processing

- For color:
  - Colorization is luminance‑based, preserving alpha, and returns a new image.
- For padding:
  - `padding` tuples are always `(top, bottom, left, right)` and documented as such.
  - If a 3‑channel color is passed, alpha is defaulted to fully opaque.
- For glow:
  - Strength ≤ 0 or radius ≤ 0 returns a copy of the original image.
  - For RGBA images: glow is composed **behind** the content with alpha compositing.
  - For opaque images: glow uses screen‑style blending to maintain vibrancy.

### 7.2 Layout (Framing Words)

- `frame` lays out word images into right‑to‑left rows and pages:
  - Groups images into rows based on width and word spacing.
  - Observes `max_rows_per_page`, `max_width`, `image_height`, `padding`, `row_spacing`.
- `_group_items_into_rows`:
  - Ensures the first item is always placed if nothing fits, to avoid infinite loops.
  - Tracks items consumed per page precisely.
- `_apply_stop_sign_adjustment`:
  - Uses `QURANIC_STOP_SIGNS` to adjust page breaks backwards so they end on stop signs when possible.
- `_render_page`:
  - The canvas is RGBA with transparent background.
  - Words are placed from right to left.
  - Vertical alignment in a row is centered within the row’s max height.

### 7.3 Text Rendering (`wimage`)

- `get_wimage`:
  - Uses a project‑specific Hafs font path (`./assets/hafs.otf`).
  - Dimensions:
    - Width from text bounding box.
    - Height from `ascent + descent`.
  - Padding is applied consistently as `(top, bottom, left, right)`.
  - Uses baseline alignment for text, appropriate for Arabic.

---

## 8. Database and Resources

- `DatabaseManager` is treated as a process‑wide singleton:
  - In test code, close it explicitly at the end of the full test run (`run_tests`).
  - In scripts (`main`), close the database after use.
- Avoid leaking resources:
  - Close database connections and file handles explicitly.
  - In tests, closing may be centralised rather than per test.

---

## 9. Testing Conventions

- Tests live under `src/modules/tests/` with `test_*.py` naming.
- Each test module:
  - Uses descriptive test names (`test_color`, `test_glow`, `test_framer`).
  - Logs clearly to stdout for progress and results.
- Image‑producing tests:
  - Save outputs under `./output/test/`.
  - Use helper functions for saving and logging where appropriate.
- `run_all_tests` orchestrates test execution and handles final cleanup (database close).

---

## 10. Script Entrypoints

- Use a `main` function in executable scripts (`src/main.py`).
- Protect entry with:

  - `if __name__ == "__main__":`
    - Call `main()` or `run_all_tests()`.

- `main`:
  - Instantiates the database manager.
  - Fetches words, converts to images, annotates, frames, applies glow.
  - Saves output images in a clear directory with progress messages.
  - Closes the database before exit.

---

## 11. Do / Do‑Not Summary

### Do

- Use descriptive names (especially for parameters and long‑lived variables).
- Document padding and layout conventions explicitly.
- Keep public APIs thin and factor complex logic into private helpers.
- Use type hints consistently and introduce type aliases for recurring tuples.
- Preserve image mode semantics and transparency behavior, documenting any conversions.

### Do Not

- Introduce new abbreviations for core concepts (database, images, padding, spacing).
- Mix layout calculation, domain logic, and rendering in a single large function.
- Mutate input images silently without documenting this behavior.
- Leave database connections open after tests or scripts complete.
