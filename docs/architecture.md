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
- **Output**: Raw text strings, font paths, and configuration objects (`LayoutConfig`, `WordConfig`).

### 2. Rendering Layer (The Mask Generator)

**Responsibility**: Transforming text into raw visual shapes.

- **Mask-First Approach**: To optimize performance and flexibility, text is initially rendered as **'L' mode (grayscale) masks**.
- **Separation of Concerns**: This layer only cares about *shape* and *size*, not color. This allows the same mask to be reused with different colors without re-rendering the font.
- **Key Components**: `wimage.py` (Arabic words) and `timage.py` (translations).
- **Output**: PIL Images in `'L'` mode.

### 3. Layout Layer (The Orchestrator)

**Responsibility**: Positioning masks into a coherent page structure.

- **VImage**: The core engine that implements Right-to-Left (RTL) logic and spatial arrangement.
- **Line Balancing**: Implements the **Descending Line Balancing** algorithm to ensure text is visually centered and aesthetically distributed across lines.
- **Page Management**: Calculates when a verse exceeds the `max_width` and automatically handles page breaks.
- **Output**: A coordinate map of where each image mask should be placed on the final canvas.

### 4. Composition Layer (The Final Pass)

**Responsibility**: Applying aesthetics, colors, and effects onto a canvas.

- **Frame**: The composition class that manages the RGBA canvas and handles the layering of images.
- **Colorization**: The `'L'` mode masks are colorized using the `color` function, preserving the alpha channel.
- **Visual Effects**: Applies high-end effects like Gaussian blurs (Glow), padding, and alpha compositing.
- **Final Assembly**: Pastes the colorized images onto the final RGBA canvas.
- **Output**: A final high-resolution `RGBA` image.

---

## Data Flow Example: Rendering a Single Word

1. **Asset**: `DatabaseManager` fetches the Arabic word "الله" and its translation.
2. **Rendering**: `get_wimage()` generates a grayscale mask of "الله" using the specified font.
3. **Layout**: `VImage.get_page_chunk()` groups items into right-to-left rows and `VImage.layer()` positions each mask on the page canvas.
4. **Composition**: `color()` applies a gold hue to the mask, `glow()` adds a soft outer radiance, and the result is pasted onto the canvas.
