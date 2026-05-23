# User Guide

Customizing the look and feel of your rendered content.

## The Preset System

Presets are the recommended way to handle layout. They provide a `tuple` of three configuration objects: `(LayoutConfig, TextConfig, WordConfig)`.

### Available Aspect Ratios

- `LANDSCAPE_PRESET`: 16:9 (Ideal for YouTube/Presentations)
- `STORY_PRESET`: 9:16 (Ideal for TikTok/Reels/Shorts)
- `SQUARE_PRESET`: 1:1 (Ideal for Instagram/Posts)

### Modes & Resolutions

Each preset supports:

- **Modes**: `default` (Arabic + Translation), `arabic` (Arabic only), `translation` (Translation only).
- **Resolutions**: `720p`, `1080p`, `1440p`, `2160p`.

---

## ⚙️ Deep Customization

If presets aren't enough, you can modify the config objects directly.

### 1. LayoutConfig (The Canvas)

Controls the "frame" of your image.

- `max_width` / `image_height`: Total pixels of the canvas.
- `padding`: A `Padding` object (top, bottom, left, right).
- `timage_vertical_align`: Set to `TOP`, `CENTER`, or `BOTTOM`.

### 2. WordConfig (Arabic Styling)

Controls how the Quranic text appears.

- `font_size`: Integer pixels.
- `color`: RGBA tuple (e.g., `(255, 215, 0, 255)` for gold).
- `word_padding`: Spacing around individual words.

### 3. TextConfig (Translation Styling)

Controls the translation text.

- `font_size`: Integer pixels.
- `color`: RGBA tuple.
- `highlight_config`: Controls the look of highlighted words.

## ✍️ Rich Text Formatting

The translation engine supports tag-based formatting:

- `#b#Text#b#` $\rightarrow$ **Bold**
- `#i#Text#i#` $\rightarrow$ *Italic*
- `#ff0000#Text#ff0000#` $\rightarrow$ <span style="color:red">Red Text</span>

Example:
`"The #b#Merciful#b# is #ff0000#Kind#ff0000#."`
