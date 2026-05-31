# Workflows Guide

Workflows are the high-level orchestrators of QuranMediaLib. They handle the entire pipeline from database retrieval to final image composition.

## Workflow Architecture

Every workflow inherits from `BaseWorkflow` and implements the `get_iterator()` method. This allows you to process content in a memory-efficient, streaming fashion.

### 1. VerseWorkflow

**Purpose**: Render a single verse with specific translations.
**Best for**: Social media quotes or specific verse studies.

```python
from quranmedialib import VerseWorkflow, STORY_PRESET

layout, text, word = STORY_PRESET["default"]["1080p"]
workflow = VerseWorkflow(layout, text, word)

translations = ["In the name of Allah,", "the Entirely Merciful, the Especially Merciful."]
iterator = workflow.get_iterator(surah=1, ayah=1, translations=translations)

for page_num, pages in enumerate(iterator, 1):
    for img, suffix in pages:
        img.save(f"verse_1_1_p{page_num}_{suffix}.png")
```

### 2. SurahWorkflow

**Purpose**: Process an entire Surah automatically.
**Best for**: Creating complete digital copies of a chapter.

```python
from quranmedialib import SurahWorkflow, LANDSCAPE_PRESET

layout, text, word = LANDSCAPE_PRESET["default"]["1080p"]
workflow = SurahWorkflow(layout, text, word)

# Automatically fetches verses and translations for Surah 112 (Al-Ikhlas)
for page_num, pages in enumerate(workflow.get_iterator(surah=112), 1):
    for img, suffix in pages:
        img.save(f"surah112_p{page_num}_{suffix}.png")
```

### 3. VerseRangeWorkflow

**Purpose**: Render a specific range of verses.
**Best for**: Custom selections or themed collections.

```python
from quranmedialib import VerseRangeWorkflow, SQUARE_PRESET

layout, text, word = SQUARE_PRESET["default"]["1080p"]
workflow = VerseRangeWorkflow(layout, text, word)

# Process verses 1-5 of Surah 1
translations = [["V1 Trans"], ["V2 Trans"], ["V3 Trans"], ["V4 Trans"], ["V5 Trans"]]
iterator = workflow.get_iterator(
    surah=1, 
    start_ayah=1, 
    end_ayah=5, 
    translations=translations,
    output_dir="output/range_test" # Optional: Save images directly to disk
)
```

**Note**: When `output_dir` is provided, the iterator yields lists of file paths instead of image objects.

### 4. IsolateWordsWorkflow

**Purpose**: Focus on individual words with high-visibility highlighting.
**Best for**: Educational tools and word-by-word vocabulary learning.

```python
from quranmedialib import IsolateWordsWorkflow, STORY_PRESET

layout, text, word = STORY_PRESET["default"]["1080p"]
workflow = IsolateWordsWorkflow(layout, text, word)

# Isolates words in a specific verse
iterator = workflow.get_iterator(surah=1, ayah=1, verse_words=["الله", "الرحمن", "الرحيم"])
```
