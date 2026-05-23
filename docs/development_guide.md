# Development Guide

This guide explains how to extend and maintain `QuranMediaLib`.

## Core Philosophy: "Boring Code"
We prioritize linearity and maintainability over clever abstractions. If a piece of logic is not obvious, document it. If it's obvious, don't.

## Extending the Library

### 1. Adding a New Preset
Presets are defined in `src/quranmedialib/presets.py`. To add a new preset:
1. Define the `LayoutConfig`, `TextConfig`, and `WordConfig` for the baseline resolution (1080p).
2. Add it to the appropriate preset map (e.g., `LANDSCAPE_PRESET`).
3. The `build_preset` function will automatically handle scaling for other resolutions.

### 2. Creating a Custom Workflow
Workflows orchestrate the rendering pipeline. To create one:
1. Inherit from `BaseWorkflow`.
2. Implement `get_iterator(...)`.
3. Use `self.layout_config`, `self.text_config`, and `self.word_config` for settings.
4. Yield a `list[Image.Image]` representing the pages for each iteration.

### 3. Modifying the Rendering Pipeline
The pipeline follows: `Asset` --> `Rendering` --> `Layout` --> `Composition`.
- **Assets**: Modify `database_manager.py` for data retrieval.
- **Rendering**: Modify `modules/wimage.py` or `timage.py` for glyph generation.
- **Layout**: Modify `modules/framer.py` for RTL and line balancing logic.
- **Composition**: Modify `modules/image.py` for effects like glows and padding.

## Testing & Quality Assurance

### Baseline Performance
Before any change, run:
```powershell
uv run -m pytest; uv run -m pytest -v --b
```
Ensure there are no regressions in speed or functionality.

### Linting & Formatting
We use `Ruff` and `Sourcery`.
```bash
uv run -m ruff check .
uv run -m ruff format .
sourcery review
```

### Docstring Standard
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
