# Developer Guide

This guide is for those who wish to extend the library's functionality or contribute to its core.

## Core Engineering Principles

QuranMediaLib is built on the principle of **Predictable Performance**.

1. **Mask-First Rendering**: We render text as grayscale masks (`'L' mode`) to decouple shape from color. This allows us to apply glows and colors without re-rendering fonts.
2. **Sub-pixel Precision**: All layout calculations use floats to prevent cumulative rounding errors in long lines.
3. **Memory-First Design**: We use `__slots__` in high-frequency classes like `StyledWord` and `Line` to reduce the memory footprint during bulk rendering.
4. **Boring Code Rule**: We prioritize clarity and maintainability over "clever" abstractions. If a piece of logic is not immediately obvious, it is considered a liability.

## 🛡️ Security Standards

We implement a "zero-trust" approach to external input and file system access.

- **Path Validation**: All paths are validated using `_ensure_within_working_dir()` to block path traversal attacks.
- **Explicit Opt-in**: Accessing resources outside the working directory requires the `unsafe_paths=True` flag.
- **Config Trust**: Custom SQL identifiers in database configurations are rejected by default unless `trust_config=True` is provided.
- **Resource Capping**: Hard limits (e.g., `MAX_FONT_SIZE`) are enforced to prevent decompression bomb attacks.

## 🧪 Testing and Validation

We maintain a zero-regression policy.

### Running Tests

```bash
# Standard test run
uv run -m pytest -v

# Performance benchmarking
uv run -m pytest -v --benchmark
```

### Linting and Formatting

We use Ruff for fast, consistent linting and formatting.

```bash
# Check for lint errors
uv run -m ruff check .

# Format code
uv run -m ruff format .
```

## 🚀 Extending the Library

### Type System (Python 3.13+)

We use Python 3.13 `type` statements for clear, validated type aliases. When adding new types, follow this pattern:

```python
type Color = tuple[int, int, int] | tuple[int, int, int, int]
type SurahNumber = Annotated[int, range(1, 115)]
```

### Creating a Custom Workflow

Inherit from `BaseWorkflow` and implement `get_iterator`.

- **Step 1**: Use `self.layout_config`, `self.text_config`, and `self.word_config` for sizing.
- **Step 2**: Fetch data via `DatabaseManager`.
- **Step 3**: Generate masks via `get_wimage` and `get_timage`.
- **Step 4**: Create a `VImage` to handle RTL and balanced layout, then layer it onto a `Frame` canvas.

### Adding a New Image Effect

Add your function to `modules/image.py`. Ensure the function:

1. Returns a **new** image object (do not mutate the input).
2. Supports RGBA transparency.
3. Is optimized for large images.
