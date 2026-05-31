# Architecture

## High-Level Pipeline

The library follows a strict unidirectional data flow:

**Assets** -> **Masks** -> **Layout** -> **Composition**

### 1. Assets

Resources (Fonts and SQLite databases) are resolved via `importlib.resources`. The `DatabaseManager` provides a thread-safe, cached interface to retrieve verse and translation text. We use `SQLITE_MMAP_SIZE` (256MB) to accelerate read operations.

### 2. Masks

Text is rendered into grayscale `'L'` mode masks. This is the most computationally expensive part of the pipeline, which is why we use LRU caching for frequently rendered words.

### 3. Layout

The `VImage` class takes these masks and arranges them into Right-to-Left (RTL) rows. It implements the **Descending Line Balancing** algorithm to ensure that the text is visually centered and that lines decrease in width as they go down.

### 4. Composition

The `Frame` class acts as the final RGBA canvas. It handles the alignment, padding, and layering of `VImage` objects and other masks to produce the final output image.

## Security Layer

To prevent path traversal and symlink attacks, the library implements a strict working directory isolation policy. All file system access is routed through `_ensure_within_working_dir()`, which validates that the resolved real path remains within the project's root. Sensitive operations (like loading external databases) require explicit opt-in via `unsafe_paths` or `trust_config` flags.

## Performance Optimizations

- **Connection Pooling**: `threading.local` ensures that SQLite connections are thread-safe and efficient.
- **Parallelism**: `ParallelRenderer` uses multi-processing to distribute the heavy composition and effect tasks across all CPU cores.
- **Lazy Loading**: `LazyTranslationImages` defers the rendering of translation text until the moment it is actually needed for a page.
- **Memory Safeguards**: The system performs throttled memory checks every 10 verses during bulk rendering to prevent OOM (Out of Memory) crashes.
