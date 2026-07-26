# Development Guide

This guide explains how to extend and maintain `QuranMediaLib`.

## Core Philosophy: "Boring Code"
We prioritize linearity and maintainability over clever abstractions. If a piece of logic is not obvious, document it. If it's obvious, don't.

## Extending the Library

### 1. Adding a New Preset
Presets are defined in `src/quranmedialib/presets.py`. To add a new preset:
1. Define the `FrameConfig`, `TextConfig`, `WordConfig`, and `VerseConfig` for the baseline resolution (1080p).
2. Add it to the appropriate preset map (e.g., `LANDSCAPE_PRESET`).
3. The `build_preset` function will automatically handle scaling for other resolutions, returning a `Preset` object.

### 2. Creating a Custom Workflow
Workflows orchestrate the rendering pipeline. To create one:
1. Inherit from `BaseWorkflow`.
2. Implement `get_iterator(...)`.
3. Use `self.frame_cfg`, `self.verse_cfg`, `self.word_cfg`, and `self.text_cfg` for settings.
4. Yield a `list[Image.Image]` representing the pages for each iteration.

### 3. Modifying the Rendering Pipeline
The pipeline follows: `Asset` --> `Rendering` --> `Layout` --> `Composition`.
- **Assets**: Modify `database_manager.py` for data retrieval.
- **Rendering**: Modify `modules/wimage.py` or `timage.py` for glyph generation.
- **Layout**: Modify `modules/vimage.py` for RTL and line balancing logic.
- **Composition**: Modify `modules/frame.py` for the canvas and layering logic.

## Testing & Quality Assurance

We maintain a high bar for correctness and performance. Every PR must pass the full test suite and demonstrate no performance regressions.

### 1. Baseline Performance Check
Before implementing any feature or fix, establish a baseline speed for the existing codebase to ensure no regressions are introduced.
```powershell
# Run all tests, then run benchmarks
uv run -m pytest; uv run -m pytest --benchmark
```

### 2. Writing Tests
Tests are located in `tests/`, mirroring the `src/` directory structure.

**Standard Test Pattern:**
```python
def test_feature_name() -> None:
    """One-line description of the test case."""
    # 1. Setup: Initialize configs and workflows
    # 2. Exercise: Call the function/method under test
    # 3. Verify: Use assert statements to check output
    # 4. Cleanup: Save images to ./output/test/ for visual audit if applicable
```

### 3. Benchmarking
We use `pytest-benchmark` for hot paths. To mark a test as a benchmark:
```python
import pytest

@pytest.mark.benchmark
def test_performance_critical_path(benchmark):
    # Use the benchmark fixture to wrap the function call
    result = benchmark(my_critical_function, arg1, arg2)
    assert result is not None
```
Run benchmarks with: `uv run -m pytest -m benchmark`

### 4. Linting & Formatting
We use `Ruff` and `Sourcery` to maintain a clean, "boring" codebase.
```bash
# Lint and Format
uv run -m ruff check .
uv run -m ruff format .

# Advanced refactoring suggestions
uvx sourcery review .
```

### 5. Docstring Standard
All public functions **must** use Google-style docstrings:
```python
def func(param: int) -> str:
    """Summary.
    
    Args:
        param: Description.
        
    Returns:
        Description.
    """
```
