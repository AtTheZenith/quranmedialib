# FAQ

## Installation & Setup

**Q: Why should I use `uv` instead of `pip`?**
A: `uv` is significantly faster and provides a lockfile (`uv.lock`) that ensures every developer is using the exact same version of every dependency.

**Q: What version of Python is required?**
A: QuranMediaLib requires Python 3.13+. We utilize new features like the `type` statement for cleaner type aliasing.

**Q: How do I install a custom font?**
A: You can use `FontResource.from_path("path/to/font.ttf")`. The library will resolve the path and cache the font for performance.

## Rendering & Layout

**Q: What is the "Descending Line Balancing" layout?**
A: It is a visual style where the first line of text is the widest, and subsequent lines get progressively narrower. This creates a centered, balanced look often seen in Quranic calligraphy.

**Q: My text is being cut off at the edges. What happened?**
A: This usually happens if `max_width` is set too low or if the font size is too large for the canvas. Try increasing the `max_width` in your `LayoutConfig`.

**Q: How do I change the color of the Arabic text?**
A: Update the `color` attribute in your `WordConfig` using an RGBA tuple, e.g., `(255, 215, 0, 255)` for gold.

## Security & Safety

**Q: Can I load a database from a different folder?**
A: Yes, but you must pass `unsafe_paths=True` to `DatabaseConfig.from_path()`. By default, the library blocks access to paths outside the working directory to prevent security vulnerabilities.

**Q: What is `trust_config`?**
A: `trust_config=True` allows the use of custom SQL identifiers in database configurations. This is disabled by default to prevent SQL injection risks.

## Performance

**Q: The rendering is slow for very long Surahs.**
A: Use the `ParallelRenderer` with `ExecutionMode.PROCESS`. This will utilize all your CPU cores to render pages in parallel.

**Q: I am running out of memory (OOM).**
A: Use the `MemoryMonitor` utility to track usage. If you are rendering in bulk, call `clear_rendering_caches()` periodically to free up LRU cache memory.
