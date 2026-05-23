# Architecture Decision Records (ADR)

This document records the "Why" behind the critical engineering choices made in QuranMediaLib. These decisions prioritize long-term maintainability, memory efficiency, and thread safety.

---

## ADR 001: SQLite for Asset Management

**Status**: Accepted

**Context**: The library needs to store and retrieve thousands of word-by-word translations and Quranic verses with minimal latency.

**Decision**: Use SQLite as the primary storage engine for all bundled assets.

**Rationale**:

- **Zero Configuration**: SQLite is serverless and requires no setup for the end user.
- **Performance**: Using `SQLITE_MMAP_SIZE` and indexed queries allows for near-instantaneous retrieval of verse data.
- **Integrity**: SQL constraints ensure that the relationship between Surahs, Ayahs, and Words remains consistent.

---

## ADR 002: Thread-Local Connection Pooling

**Status**: Accepted

**Context**: SQLite connections in Python cannot be easily shared across threads without risk of race conditions or `sqlite3.ProgrammingError`.

**Decision**: Implement connection pooling using `threading.local()` within the `DatabaseManager`.

**Rationale**:

- **Safety**: Each thread gets its own unique connection, eliminating the need for global locks during query execution.
- **Performance**: Connections are reused within the same thread, avoiding the overhead of repeatedly opening and closing database files.

---

## ADR 003: Memory Efficiency via `__slots__`

**Status**: Accepted

**Context**: During bulk rendering of entire Surahs, the library instantiates thousands of `StyledWord` and `Line` objects.

**Decision**: Use `__slots__` for all high-frequency data classes.

**Rationale**:

- **Memory Footprint**: By preventing the creation of a `__dict__` for every instance, memory usage is reduced by ~40-60% per object.
- **Access Speed**: Attribute access is slightly faster than dictionary lookups.

---

## ADR 004: Mask-First Rendering Pipeline

**Status**: Accepted

**Context**: Rendering high-resolution text is computationally expensive.

**Decision**: Render text as `'L'` (grayscale) masks first, then apply color and effects in a final composition pass.

**Rationale**:

- **Reusability**: A single grayscale mask can be reused for multiple colors/glows without re-calculating font glyphs.
- **Efficiency**: Alpha compositing on grayscale masks is significantly faster than manipulating full RGBA images during the layout phase.

---

## ADR 005: `uv` as the Unified Toolchain

**Status**: Accepted

**Context**: Python dependency management is fragmented (pip, poetry, conda).

**Decision**: Standardize on `uv` for all project management, syncing, and execution.

**Rationale**:

- **Speed**: `uv` is written in Rust and is orders of magnitude faster than `pip`.
- **Consistency**: `uv lock` ensures that every developer and AI agent is working with the exact same dependency tree.
