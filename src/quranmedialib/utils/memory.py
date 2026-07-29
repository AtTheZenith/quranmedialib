"""Memory monitoring and resource management utilities for QuranMediaLib.

This module provides tools for tracking memory usage across processes and
enforcing hard limits to ensure stability in resource-constrained environments.
"""

from __future__ import annotations

import logging
import os

try:
    import psutil
except ImportError:
    psutil = None

from quranmedialib.config import (
    DEFAULT_AGGREGATE_LIMIT_MB,
    DEFAULT_PROCESS_LIMIT_MB,
)

logger = logging.getLogger(__name__)


class MemoryLimitExceededError(RuntimeError):
    """Exception raised when a process or aggregate memory limit is breached."""

    def __init__(self, message: str, current_mb: float = 0.0, limit_mb: float = 0.0):
        full_msg = f"{message} (Current: {current_mb:.2f}MB, Limit: {limit_mb:.2f}MB)" if current_mb else message
        super().__init__(full_msg)
        self.current_mb = current_mb
        self.limit_mb = limit_mb


_main_process: psutil.Process | None = None


def _get_main_process() -> psutil.Process:
    """Return the cached psutil.Process instance for the current process."""
    global _main_process
    if _main_process is None:
        _main_process = psutil.Process(os.getpid())
    return _main_process


def get_current_rss_mb() -> float:
    """Returns the Resident Set Size (RSS) of the current process in MB."""
    if psutil is None:
        return 0.0
    return _get_main_process().memory_info().rss / (1024 * 1024)


def get_aggregate_rss_mb() -> float:
    """Returns the combined RSS of the current process and all recursive children."""
    if psutil is None:
        return 0.0

    main_process = _get_main_process()
    total_rss = main_process.memory_info().rss

    try:
        for child in main_process.children(recursive=True):
            try:
                total_rss += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    return total_rss / (1024 * 1024)


# Backward-compatible peak-RSS tracker (replaces old background-thread monitor).
# New code should call check_aggregate_memory() directly for enforcement.


class MemoryMonitor:
    """Synchronous peak-RSS tracker. No background thread, no side effects.

    Drop-in replacement for the old threaded monitor. Tracks aggregate RSS
    at enter/exit only — for continuous enforcement use check_aggregate_memory().
    """

    def __init__(self, limit_mb: float = DEFAULT_AGGREGATE_LIMIT_MB, **kwargs: object):
        self.limit_mb = limit_mb
        self._peak_rss = 0.0

    def __enter__(self) -> MemoryMonitor:
        self._peak_rss = get_aggregate_rss_mb()
        return self

    def __exit__(self, *args: object) -> None:
        self._peak_rss = max(self._peak_rss, get_aggregate_rss_mb())

    @property
    def peak_rss(self) -> float:
        return self._peak_rss


def check_process_memory(limit_mb: float = DEFAULT_PROCESS_LIMIT_MB) -> None:
    """Checks current process memory and raises MemoryLimitExceededError if limit breached.

    Args:
        limit_mb: Memory limit in megabytes.

    Raises:
        MemoryLimitExceededError: If current RSS exceeds limit_mb.
    """
    current_mb = get_current_rss_mb()
    if current_mb > limit_mb:
        logger.error("Process memory limit breached: %.2fMB > %.2fMB", current_mb, limit_mb)
        raise MemoryLimitExceededError("Individual process memory limit exceeded", current_mb, limit_mb)


def check_aggregate_memory(limit_mb: float = DEFAULT_AGGREGATE_LIMIT_MB) -> None:
    """Synchronous aggregate memory check — raises immediately if limit breached.

    Call this from the main thread after significant work is done (e.g., between
    batches). Unlike the old background-thread monitor, this gives deterministic
    error propagation without noisy background logging.

    Args:
        limit_mb: Aggregate RSS limit in MB (default: workers x per-process limit).

    Raises:
        MemoryLimitExceededError: If aggregate RSS exceeds limit_mb.
    """
    current_mb = get_aggregate_rss_mb()
    if current_mb > limit_mb:
        logger.error("Aggregate memory limit breached: %.2fMB > %.2fMB", current_mb, limit_mb)
        raise MemoryLimitExceededError("Aggregate memory limit exceeded", current_mb, limit_mb)


def clear_rendering_caches() -> None:
    """Clears all module-level LRU caches used during rendering.

    Flushes:
    - wimage._get_wimage_cached
    - annotation._annotate_word_cached
    - font_cache._load_font_base
    - DatabaseManager lru_caches (via minimize_caches)
    """
    from quranmedialib.database_manager import DatabaseManager
    from quranmedialib.modules.annotation import _annotate_word_cached
    from quranmedialib.modules.font_cache import _load_font_base
    from quranmedialib.modules.wimage import _get_wimage_cached

    _annotate_word_cached.cache_clear()
    _get_wimage_cached.cache_clear()
    _load_font_base.cache_clear()

    db = DatabaseManager()
    db.minimize_caches()
    logger.debug("All rendering caches cleared.")


def clear_rendering_caches() -> None:
    """Clears all module-level LRU caches used during rendering.

    Flushes:
    - wimage._get_wimage_cached
    - annotation._annotate_word_cached
    - font_cache._load_font_base
    - DatabaseManager lru_caches (via minimize_caches)
    """
    from quranmedialib.database_manager import DatabaseManager
    from quranmedialib.modules.annotation import _annotate_word_cached
    from quranmedialib.modules.font_cache import _load_font_base
    from quranmedialib.modules.wimage import _get_wimage_cached

    _annotate_word_cached.cache_clear()
    _get_wimage_cached.cache_clear()
    _load_font_base.cache_clear()

    db = DatabaseManager()
    db.minimize_caches()
    logger.debug("All rendering caches cleared.")
