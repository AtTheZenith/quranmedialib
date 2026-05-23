# Developer Guide

This guide is for those who wish to extend the library's functionality or contribute to its core.

## Core Engineering Principles

QuranMediaLib is built on the principle of **Predictable Performance**.

1. **Mask-First Rendering**: We render text as grayscale masks (`'L' mode`) to decouple shape from color. This allows us to apply glows and colors without re-rendering fonts.
2. **Sub-pixel Precision**: All layout calculations use floats to prevent cumulative rounding errors in long lines.
3. **Memory-First Design**: We use `__slots__` in high-frequency classes like `StyledWord` and `Line` to reduce the memory footprint during bulk rendering.

## 🧪 Testing and Validation

We maintain a zero-regression policy.

### Running Tests

```bash
uv run -m pytest -v
```

### Performance Benchmarking

We use `pytest-benchmark` to track rendering speed. If a change slows down the pipeline, it will be rejected.

```bash
uv run -m pytest -v --benchmark
```

## 🚀 Extending the Library

### Creating a Custom Workflow

Inherit from `BaseWorkflow` and implement `get_iterator`.

- **Step 1**: Use `self.layout_config`, `self.text_config`, and `self.word_config` for sizing.
- **Step 2**: Fetch data via `DatabaseManager`.
- **Step 3**: Generate masks via `get_wimage` and `get_timage`.
- **Step 4**: Layout the masks via `frame()`.

### Adding a New Image Effect

Add your function to `modules/image.py`. Ensure the function:

1. Returns a **new** image object (do not mutate the input).
2. Supports RGBA transparency.
3. Is optimized for large images.
