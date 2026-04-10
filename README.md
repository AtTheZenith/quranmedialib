# QuranMediaLib

Media producing library for Quranic texts. Generates properly formatted images of Quranic verses along with translations.

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
from quranmedialib import DatabaseManager, LayoutConfig, TextConfig, WordConfig
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.modules.framer import frame
from quranmedialib.presets import LANDSCAPE_PRESET

# Initialize database manager (auto-loads packaged databases)
db = DatabaseManager()

# Get preset configuration for 1080p landscape
layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

# Render a single Arabic word
word_img = get_wimage("الله", word_config)

# Get verses from a surah
verses = db.get_verses_from_surah(1)  # Al-Fatiha
print(f"Surah 1 has {len(verses)} verses")

# Get word-by-word translation
wbw = db.get_wbw_from_verse(1, 1)  # First verse, word-by-word
print(f"First verse has {len(wbw)} words")

# Don't forget to close the database when done
db.close()
```

## Usage with Workflows

```python
from quranmedialib import DatabaseManager, SurahWorkflow, LANDSCAPE_PRESET
from quranmedialib.modules.image import glow

db = DatabaseManager()

# Create workflow with preset configuration
layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

workflow = SurahWorkflow(
    layout_config=layout_config,
    text_config=text_config,
    word_config=word_config,
)

# Process Surah Al-Fatiha (surah 1)
data = {"surah": 1}
iterator = workflow.get_iterator(data, annotate=True)

# Save generated pages
for page_num, page_images in enumerate(iterator, 1):
    for img, suffix in page_images:
        # Apply glow effect
        final_img = glow(img)
        final_img.save(f"output/surah1_page{page_num}_{suffix}.png")

db.close()
```

## Package Structure

```markdown
quranmedialib/
├── types.py           # Configuration dataclasses (LayoutConfig, WordConfig, etc.)
├── presets.py         # Pre-configured layouts (LANDSCAPE_PRESET, STORY_PRESET, etc.)
├── database_manager.py # Stateful database connection manager
├── resources.py       # Asset path resolution
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

The library includes pre-configured presets for common formats:

- **LANDSCAPE_PRESET**: 16:9 aspect ratio (1280x720, 1920x1080, etc.)
- **STORY_PRESET**: 9:16 aspect ratio (720x1280, 1080x1920, etc.)
- **SQUARE_PRESET**: 1:1 aspect ratio (720x720, 1080x1080, etc.)

Each preset supports multiple resolutions: `720p`, `1080p`, `1440p`, `2160p`

And three modes per format:

- `default`: Arabic text with annotations + translation
- `arabic`: Arabic text only (no translation)
- `translation`: Translation only (no Arabic)

```python
from quranmedialib.presets import LANDSCAPE_PRESET

# Access preset by mode and resolution
config = LANDSCAPE_PRESET["default"]["1080p"]
layout_config, text_config, word_config = config
```

## Included Data

The library includes default databases for immediate use:

- **Arabic Text**: `quran.db` using sequential tanween.
- **English WBW**: Word-by-word translation for word-level annotation.
- **Sahih International**: English translation of the meanings.

## Custom Database Configuration

Add your own translation databases:

```python
from quranmedialib import DatabaseManager, DatabaseConfig, WbwDatabaseConfig

db = DatabaseManager()

# Add a custom translation database
custom_config = DatabaseConfig(
    filepath="/path/to/custom_translation.db",
    tablename="verses",
    surah_col="sura",
    ayah_col="ayah",
    text_col="text",
)
db.add_connection("my_translation", custom_config)

# Switch to custom translation
db.set_active_translation("my_translation")
verses = db.get_verses_from_surah(1)

# Add custom word-by-word database
wbw_config = WbwDatabaseConfig(
    filepath="/path/to/custom_wbw.db",
    tablename="wbw",
    surah_col="surah",
    ayah_col="ayah",
    text_col="translation",
    word_id_col="word",
)
db.add_connection("my_wbw", wbw_config)
```

## Development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest tests/

# Lint with ruff
ruff check .
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
