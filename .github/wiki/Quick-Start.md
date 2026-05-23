# Quick Start Guide

Get QuranMediaLib up and running in minutes.

## 1. Installation

We recommend using `uv` for the fastest and most consistent installation.

```bash
# Clone the repo
git clone https://github.com/AtTheZenith/quranmedialib.git
cd quranmedialib

# Install dependencies
uv pip install -e .
```

## 2. Your First Image

The easiest way to start is by using a **Preset**. Presets handle the complex math of canvas sizing, font scales, and padding for you.

```python
from quranmedialib import DatabaseManager, VerseWorkflow, LANDSCAPE_PRESET

# 1. Initialize the database (auto-loads packaged assets)
db = DatabaseManager()

# 2. Load a 1080p Landscape preset
layout, text_cfg, word_cfg = LANDSCAPE_PRESET["default"]["1080p"]

# 3. Create a workflow for a single verse
workflow = VerseWorkflow(layout, text_cfg, word_cfg)

# 4. Render Surah 1, Ayah 1
translations = ["In the name of Allah,", "the Entirely Merciful, the Especially Merciful."]
pages = list(workflow.get_iterator(surah=1, ayah=1, translations=translations))

# 5. Save the result
pages[0][0].save("first_verse.png")

db.close()
```

## 3. Common Use Cases

### Render a Single Arabic Word

Perfect for vocabulary cards or highlights.

```python
from quranmedialib import LANDSCAPE_PRESET
from quranmedialib.modules.wimage import get_wimage

_, _, word_cfg = LANDSCAPE_PRESET["default"]["1080p"]
img = get_wimage("الله", word_cfg)
img.save("word.png")
```

### Render an Entire Surah

Best for creating a series of images for a social media carousel.

```python
from quranmedialib import SurahWorkflow, LANDSCAPE_PRESET

layout, text, word = LANDSCAPE_PRESET["default"]["1080p"]
workflow = SurahWorkflow(layout, text, word)

for page_num, pages in enumerate(workflow.get_iterator(surah=112), 1):
    for img, suffix in pages:
        img.save(f"surah112_p{page_num}_{suffix}.png")
```
