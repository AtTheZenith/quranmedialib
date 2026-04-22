---
trigger: always_on
---

# Quran Media Library – v2.0.0 Style Guide

Terse architectural mandates for QuranMediaLib agents.

## 1. Syntax & Core Standards
- **Python 3.13**: Use `type` aliases and `|` union operators.
- **Typing**: Mandatory on all functions. Use built-in generics (`list[int]`).
- **Imports**: `from __future__ import annotations` required. Order: stdlib → PIL → local.
- **Naming**: No abbreviations for core concepts. `snake_case` (fn/var), `PascalCase` (class), `UPPER_SNAKE_CASE` (const).

## 2. Resource & Type Safety
- **Constants**: Use centralized constants in `types.py` (`MAX_FONT_SIZE`, `MIN_SURAH`, `MAX_SURAH`).
- **Dataclasses**: `@dataclass(frozen=True, slots=True)`. Factory methods `from_packaged()` / `from_path()`.
- **Validation**: Centralize in `types.py` or workflow `_validate_*` methods. Raise `ValidationError`.
- **Exceptions**: Use `exceptions.py` hierarchy (`ResourceError`, `DatabaseError`, `WorkflowError`, `LayoutError`).

## 3. Image & Layout Logic
- **Immutability**: Image fns return new objects; no silent mutation.
- **Types**: Use `Padding` NamedTuple, `HorizontalAlignment`/`VerticalAlignment` Enums.
- **RTL**: Layouts (`frame`, `annotate_words`) follow Right-to-Left Arabic domain logic.
- **Caching**: Use `functools.lru_cache` for expensive rendering/DB ops.

## 4. Parallelism & Resource Safety
- **Engine**: Use `ParallelRenderer` for CPU-bound tasks (e.g., blurs).
- **Scaling**: Detect hardware via `CPU_COUNT`. Avoid hardcoded worker counts.
- **Memory**: Wrap loops in `MemoryMonitor`. Use `worker_heartbeat` in workers for RSS checks.
- **Persistence**: Reuse worker pools via internal `_PoolManager` to minimize spawn overhead.

## 5. Public API & Exports
- **Clean API**: `__init__.py` defines `__all__`. Export types, workflows, and presets at top-level.
- **Docstrings**: Google-style. `Args:`, `Returns:`, `Yields:`, `Raises:` required for public API.
- **Internal**: Private helpers use leading underscore. Document with concise docstrings.

## 6. Tooling & Development
- **Commands**: All entrypoints use `uv run` (e.g., `uv run -m pytest`, `uv run demo.py`).
- **Lint/Format**: Enforced by Ruff (`line-length = 120`).
- **Tests**: Mirror `src/` structure in `tests/`. Standalone execution support: `if __name__ == "__main__":`.

## 7. Terse Do / Do Not
- **Do**: Use explicit PIL types (`Image.Image`). Use `Path` objects for I/O.
- **Do**: Close DB connections (`DatabaseManager.close()`).
- **Do Not**: Duplicated constants. Mutate inputs. Silent errors. Hardcoded magic numbers.
