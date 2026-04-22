<div align="center">

# QuranMediaLib

</div>

A media producing library for Quranic content. Written in Python. It can generate properly formatted images of Quranic verses along with translations.

## Installation

### From source (development)

```bash
# Clone the repository
git clone https://github.com/yourusername/quranmedialib.git
cd quranmedialib

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

### From PyPI (coming soon)

```bash
pip install quranmedialib
```

## Quick Start

```python
from quranmedialib import DatabaseManager, LANDSCAPE_PRESET
from quranmedialib.modules.wimage import get_wimage

# Initialize database manager (auto-loads packaged databases)
db = DatabaseManager()

# Get preset configuration for 1080p landscape
layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

# Render a single Arabic word
word_img = get_wimage("الله", word_config)

# Get verses from a surah
verses = db.get_verses_from_surah(1)  # Al-Fatiha
print(f"Surah 1 has {len(verses)} verses")

db.close()
```

# Workflows

Workflows are high-level orchestrators that handle data retrieval, image generation, and layout. All workflows inherit from `BaseWorkflow` and provide a `get_iterator()` method.

## Using Built-in Workflows

### SurahWorkflow

Processes an entire surah page by page.

```python
from quranmedialib import SurahWorkflow, LANDSCAPE_PRESET

layout, text, word = LANDSCAPE_PRESET["default"]["1080p"]
workflow = SurahWorkflow(layout, text, word)

# Process Surah Al-Ikhlas (112)
for page_num, page_images in enumerate(workflow.get_iterator(surah=112), 1):
    for img, suffix in page_images:
        img.save(f"output/surah112_p{page_num}_{suffix}.png")
```

### VerseWorkflow

Renders a single verse with custom translations.

```python
from quranmedialib import VerseWorkflow, STORY_PRESET

layout, text, word = STORY_PRESET["default"]["1080p"]
workflow = VerseWorkflow(layout, text, word)

# Render Surah 1, Ayah 1 with custom translation strings
translations = ["In the name of Allah,", "the Entirely Merciful, the Especially Merciful."]
iterator = workflow.get_iterator(surah=1, ayah=1, translations=translations)

for page_num, page_images in enumerate(iterator, 1):
    for img, suffix in page_images:
        img.save(f"verse1_1_p{page_num}_{suffix}.png")
```

### VerseRangeWorkflow

Processes a range of verses, supporting parallel rendering.

```python
from quranmedialib import VerseRangeWorkflow, SQUARE_PRESET

layout, text, word = SQUARE_PRESET["default"]["1080p"]
workflow = VerseRangeWorkflow(layout, text, word)

# Process verses 1-5 of Surah 1
# translations[verse_index][page_index]
translations = [["Trans for V1"], ["Trans for V2"], ["Trans for V3"], ["Trans for V4"], ["Trans for V5"]]
iterator = workflow.get_iterator(surah=1, start_ayah=1, end_ayah=5, translations=translations)

for page_images in iterator:
    # Handle results
    pass
```

## Creating Custom Workflows

Inherit from `BaseWorkflow` to create custom rendering pipelines.

```python
from typing import Iterator
from PIL import Image
from quranmedialib.workflows.base import BaseWorkflow

class MyCustomWorkflow(BaseWorkflow):
    def get_iterator(self, **kwargs) -> Iterator[list[Image.Image]]:
        # 1. Access configs via self.layout_config, self.text_config, self.word_config
        # 2. Retrieve data (e.g., from DatabaseManager)
        # 3. Generate images (e.g., via get_wimage, get_timage)
        # 4. Yield lists of images representing pages
        yield [Image.new("RGBA", (self.layout_config.max_width, self.layout_config.image_height))]
```

## Parallel Processing

QuranMediaLib provides a `ParallelRenderer` for CPU-intensive tasks (like applying blurs/glows) and bulk rendering.

```python
from quranmedialib.utils.parallel import ParallelRenderer, ExecutionMode
from quranmedialib.modules.image import glow

def apply_glow_worker(img):
    return glow(img)

images = [...] # List of PIL Images
renderer = ParallelRenderer(mode=ExecutionMode.PROCESS)

# Process images in parallel across CPU cores
glowed_images = list(renderer.map(apply_glow_worker, images))
```

## Package Structure

```markdown
quranmedialib/
├── types.py           # Configuration dataclasses (LayoutConfig, WordConfig, etc.)
├── presets.py         # Pre-configured layouts (LANDSCAPE_PRESET, STORY_PRESET, etc.)
├── database_manager.py # Stateful database connection manager
├── modules/
│   ├── wimage.py      # Arabic word rendering
│   ├── timage.py      # Translation text rendering
│   ├── framer.py      # Multi-page layout engine
│   ├── image.py       # Image effects (glow, color, pad)
│   ├── annotation.py  # Word-by-word annotation
│   └── verse_number.py # Verse number rendering
└── workflows/
    ├── surah.py       # Surah-level processing
    ├── verse_range.py # Verse range processing
    └── isolate_words.py # Word isolation workflows
```

## Presets

- **LANDSCAPE_PRESET**: 16:9 aspect ratio
- **STORY_PRESET**: 9:16 aspect ratio
- **SQUARE_PRESET**: 1:1 aspect ratio

Each preset supports resolutions `720p`, `1080p`, `1440p`, `2160p` and modes `default`, `arabic`, `translation`.

## Development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests
uv run -m pytest -v

# Run benchmarks
uv run -m pytest -v --run-benchmarks

# Lint and format
uv run -m ruff check .
uv run -m ruff format .
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
