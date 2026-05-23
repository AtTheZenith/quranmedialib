# Architecture

## High-Level Pipeline

The library follows a strict unidirectional data flow:

**Assets** -> **Masks** -> **Layout** -> **Composition**

### 1. Assets

Resources (Fonts and SQLite databases) are resolved via `importlib.resources`. The `DatabaseManager` provides a thread-safe, cached interface to retrieve verse and translation text.

### 2. Masks

Text is rendered into grayscale `'L'` mode masks. This is the most computationally expensive part of the pipeline, which is why we use LRU caching for frequently rendered words.

### 3. Layout

The `framer.py` module takes these masks and arranges them into Right-to-Left (RTL) rows. It uses the **Decremental Line Balancing** algorithm to ensure that the text is visually centered and that lines decrease in width as they go down.

### 4. Composition

In the final pass, the masks are colorized, effects (like glow) are applied, and the final result is composited onto an RGBA canvas.

## Performance Optimizations

- **Connection Pooling**: `threading.local` ensures that SQLite connections are thread-safe and efficient.
- **Parallelism**: `ParallelRenderer` uses multi-processing to distribute the heavy composition and effect tasks across all CPU cores.
- **Lazy Loading**: `LazyTranslationImages` defers the rendering of translation text until the moment it is actually needed for a page.
