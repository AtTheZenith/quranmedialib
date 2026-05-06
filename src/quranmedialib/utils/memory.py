"""Memory monitoring and resource management utilities for QuranMediaLib.

This module provides tools for tracking memory usage across processes and
enforcing hard limits to ensure stability in resource-constrained environments.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Callable

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
        # Ensure arguments are optional for pickling/unpickling safety across processes
        full_msg = f"{message} (Current: {current_mb:.2f}MB, Limit: {limit_mb:.2f}MB)" if current_mb else message
        super().__init__(full_msg)
        self.current_mb = current_mb
        self.limit_mb = limit_mb


def get_current_rss_mb() -> float:
    """Returns the Resident Set Size (RSS) of the current process in MB."""
    if psutil is None:
        return 0.0
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def get_aggregate_rss_mb() -> float:
    """Returns the combined RSS of the current process and all recursive children."""
    if psutil is None:
        return 0.0

    main_process = psutil.Process(os.getpid())
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


class MemoryMonitor:
    """Context manager for background execution memory monitoring.

    Monitors aggregate memory usage of the current process and all its workers.
    Can be used to wrap long-running rendering loops.
    """

    def __init__(
        self,
        limit_mb: float = DEFAULT_AGGREGATE_LIMIT_MB,
        interval: float = 0.5,
        on_breach: Callable[[float, float], Any] | None = None,
    ):
        """Initializes the monitor.

        Args:
            limit_mb: Aggregate memory limit in MB.
            interval: Check interval in seconds.
            on_breach: Optional callback triggered when limit is breached.
                Receives (current_mb, limit_mb).
        """
        self.limit_mb = limit_mb
        self.interval = interval
        self.on_breach = on_breach
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._peak_rss = 0.0

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            current_rss = get_aggregate_rss_mb()
            self._peak_rss = max(self._peak_rss, current_rss)

            if current_rss > self.limit_mb:
                logger.error("Aggregate memory limit reached: %.2fMB > %.2fMB", current_rss, self.limit_mb)
                if self.on_breach:
                    self.on_breach(current_rss, self.limit_mb)
                else:
                    # Default behavior: log and raise in the main thread is hard,
                    # so we just log heavily since this is a background thread.
                    pass
            time.sleep(self.interval)

    def __enter__(self) -> MemoryMonitor:
        """Starts the background monitor thread."""
        if psutil is not None:
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stops the background monitor thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.debug("Memory monitoring finished. Peak Aggregate RSS: %.2fMB", self._peak_rss)

    @property
    def peak_rss(self) -> float:
        """Returns the peak aggregate RSS observed during the session."""
        return self._peak_rss


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
