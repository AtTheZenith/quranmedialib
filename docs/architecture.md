# System Architecture: QuranMediaLib

## Objective

This document provides the high-level "Mental Map" of the QuranMediaLib rendering pipeline. It is designed to help new developers understand how data transforms from raw database entries into a finished, high-resolution image.

## The Rendering Pipeline (The Mental Map)

The library operates as a linear pipeline with four distinct layers. Data flows from the bottom up:

`Asset Layer` --> `Rendering Layer` --> `Layout Layer` --> `Composition Layer`

---

## Layer Breakdown

### 1. Asset Layer (The Foundation)

**Responsibility**: Data retrieval and resource resolution.

- **Databases**: Uses SQLite for high-performance retrieval of Quranic text and word-by-word translations.
- **Resource Resolution**: The `FontResource` and `DatabaseConfig` classes handle the resolution of packaged assets (via `importlib.resources`) or external paths.
- **Output**: Raw text strings, font paths, and configuration objects (`FrameConfig`, `WordConfig`).

### 2. Rendering Layer (The Mask Generator)

**Responsibility**: Transforming text into raw visual shapes.

- **Mask-First Approach**: To optimize performance and flexibility, text is initially rendered as **'L' mode (grayscale) masks**.
- **Separation of Concerns**: This layer only cares about *shape* and *size*, not color. This allows the same mask to be reused with different colors without re-rendering the font.
- **Key Components**: `wimage.py` (Arabic words) and `timage.py` (translations).
- **Input Bounds**: `get_timage` rejects text beyond `MAX_TEXT_CHARS` / `MAX_TEXT_WORDS` before measuring, and clamps any canvas to `MAX_CANVAS_DIMENSION`, so untrusted strings cannot force unbounded measurement, layout, or image allocation.
- **Output**: PIL Images in `'L'` mode.

### 3. Layout Layer (The Orchestrator)

**Responsibility**: Positioning masks into a coherent page structure.

- **Resolution Independence** (v4.0): Layout uses `UDim2` (scale + offset pairs) and `AnchorPoint` (0-1 pivot) defined in `PresetLayout`. One definition works at any resolution — no per-resolution scaling tables.
- **LayoutEngine**: Resolves `PresetLayout` elements to absolute pixel `ResolvedRect` positions for a given frame size at render time.
- **VImage**: The core engine that implements Right-to-Left (RTL) logic and spatial arrangement. Takes `content_width` directly (no longer depends on FrameConfig).
- **Line Balancing** (v4.2.0): Paragraph wrapping is parameterized by `BalancingMode` — `FORWARD` greedy, `SMOOTH` global flattest pyramid (default), or scripted-optimal `KNUTH_PLASS` / `TEX`. **Greedy is always the unconditional fallback**: whatever solver is chosen, a `None` (infeasible) result is replaced by greedy and logged with a reason. This keeps every input renderable even when a solver's model (strict descent, TeX work budget, slack) cannot be satisfied.
- **Page Management**: Calculates when a verse exceeds the available width and automatically handles page breaks.
- **Output**: A coordinate map of where each image mask should be placed on the final frame.

### 4. Composition Layer (The Final Pass)

**Responsibility**: Applying aesthetics, colors, and effects onto a frame.

- **Frame**: The composition class that manages the RGBA surface and handles the layering of images. Accepts `(width, height, bg)` directly — no config object required.
- **Frame.layer_at()** (v4.0): Places content at a resolved `ResolvedRect` position. Replaces the old `layer()` with its manual alignment/offset calculations.
- **Colorization**: The `'L'` mode masks are colorized using the `color` function, preserving the alpha channel.
- **Visual Effects**: Applies high-end effects like Gaussian blurs (Glow), padding, and alpha compositing.
- **Final Assembly**: Pastes the colorized images onto the final RGBA frame.
- **Output**: A final high-resolution `RGBA` image.

---

## Data Flow Example: Rendering a Single Word

1. **Asset**: `DatabaseManager` fetches the Arabic word "الله" and its translation.
2. **Rendering**: `get_wimage()` generates a grayscale mask of "الله" using the specified font.
3. **Layout**: `VImage.get_page_chunk()` groups items into right-to-left rows and `VImage.layer()` positions each mask on the page canvas.
4. **Composition**: `color()` applies a gold hue to the mask, `glow()` adds a soft outer radiance, and the result is pasted onto the canvas.
