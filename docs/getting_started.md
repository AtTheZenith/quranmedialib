# Getting Started with QuranMediaLib

Welcome! `QuranMediaLib` is designed to make it easy to generate high-quality Quranic media. This guide will take you from installation to your first complex render.

## Installation

We recommend using `uv` for the fastest and most consistent experience.

```bash
# Install uv if you haven't already
# https://astral.sh/uv

# Clone and install
git clone https://github.com/AtTheZenith/quranmedialib.git
cd quranmedialib
uv pip install -e .
```

## Basic Concepts

### 1. The Preset System
Instead of worrying about pixels, use **Presets**. A preset defines the look and feel for a specific aspect ratio and resolution.

- **Landscape (16:9)**: Ideal for YouTube/Presentations.
- **Story (9:16)**: Ideal for TikTok/Reels/Shorts.
- **Square (1:1)**: Ideal for Instagram posts.

```python
from quranmedialib import LANDSCAPE_PRESET
# Get preset for 1080p landscape in 'default' mode
preset = LANDSCAPE_PRESET["default"]["1080p"]
```

### 2. Workflows
Workflows are the "engines" of the library. They handle the complexity of fetching data and arranging it.

- **`VerseWorkflow`**: Use this for a single, specific verse.
- **`SurahWorkflow`**: Use this to render an entire chapter automatically.
- **`VerseRangeWorkflow`**: Use this for a specific range (e.g., verses 1-5).

## Your First Render: A Single Verse

Here is a complete example of rendering a verse with a custom translation:

```python
from quranmedialib import VerseWorkflow, STORY_PRESET

# 1. Setup Layout (Story mode for mobile)
preset = STORY_PRESET["default"]["1080p"]
workflow = VerseWorkflow(preset)

# 2. Define Verse and Translation
translations = ["In the name of Allah,", "the Entirely Merciful, the Especially Merciful."]

# 3. Render
iterator = workflow.get_iterator(surah=1, ayah=1, translations=translations)

for page_num, page_images in enumerate(iterator, 1):
    for img in page_images:
        img.save(f"my_first_verse_p{page_num}.png")
```

## Scaling Up: Rendering a Whole Surah

For larger tasks, `SurahWorkflow` handles everything automatically:

```python
from quranmedialib import SurahWorkflow, LANDSCAPE_PRESET

preset = LANDSCAPE_PRESET["default"]["1080p"]
workflow = SurahWorkflow(preset)

# Process Surah Al-Ikhlas (112)
for page_num, page_images in enumerate(workflow.get_iterator(surah=112), 1):
    for img in page_images:
        img.save(f"surah112_p{page_num}.png")
```

## Emitting Spatial Sidecars

File-writing workflows (`SurahWorkflow`, `VerseRangeWorkflow`) can emit a **spatial sidecar** beside every PNG — a deterministic JSON record of the page's exact layout (per-word bounding boxes, verse number placement, translation paragraph box, and row geometry). This is the source of truth an external agent reads to understand and refit the layout.

```python
from quranmedialib import SurahWorkflow, LANDSCAPE_PRESET

preset = LANDSCAPE_PRESET["default"]["1080p"]
workflow = SurahWorkflow(preset)

# emit_sidecar requires output_dir; writes page_N.json beside each page_N.png
iterator = workflow.get_iterator(
    surah=112,
    output_dir="output/surah112",
    emit_sidecar=True,
)
for page_num, page_images in enumerate(iterator, 1):
    for img in page_images:
        img.save(f"surah112_p{page_num}.png")
```

- **`emit_sidecar` defaults to `False`** — explicit opt-in, zero surprise for existing callers.
- Sidecars use `schema: "spatial-1"`, integer page-relative coordinates, and no timestamps/config/fonts, so identical input always produces byte-identical sidecar bytes.
- Bytes mode (`use_bytes=True`) does **not** produce sidecars; they require file output.

## Need Help?
Refer to the [API Reference](api_reference.md) for technical details or the [Architecture Docs](architecture.md) to understand the pipeline.
