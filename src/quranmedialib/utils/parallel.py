"""General-purpose parallel processing engine for QuranMediaLib.

This module provides the ParallelRenderer, a robust utility that manages
worker pools with hardware-aware scaling, optimal chunking, and memory
resource safety.
"""

from __future__ import annotations

import atexit
import logging
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from enum import Enum, auto
from typing import Any, Callable, Iterable, Iterator, TypeVar

from quranmedialib.config import CPU_COUNT, DEFAULT_PROCESS_LIMIT_MB
from quranmedialib.utils.memory import check_process_memory

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class ExecutionMode(Enum):
    """Supported hardware execution strategies."""

    PROCESS = auto()
    THREAD = auto()


class _PoolManager:
    """Internal manager for persistent worker pools.

    This prevents the overhead of repeatedly spawning and destroying
    process pools during a single application lifecycle.
    """

    _executors: dict[tuple[ExecutionMode, int], ProcessPoolExecutor | ThreadPoolExecutor] = {}

    @classmethod
    def get_executor(
        cls,
        mode: ExecutionMode,
        max_workers: int,
        initializer: Callable | None = None,
        initargs: tuple[Any, ...] = (),
    ) -> ProcessPoolExecutor | ThreadPoolExecutor:
        """Returns a cached executor for the given mode and worker count.

        Args:
            mode: PROCESS or THREAD pool.
            max_workers: Number of workers.
            initializer: Optional callable invoked at worker process startup (PROCESS mode only).
            initargs: Arguments passed to the initializer.
        """
        key = (mode, max_workers, initializer, initargs)
        if key not in cls._executors:
            logger.debug("Initializing persistent %s pool with %d workers", mode.name, max_workers)
            if mode == ExecutionMode.PROCESS:
                cls._executors[key] = ProcessPoolExecutor(
                    max_workers=max_workers,
                    initializer=initializer,
                    initargs=initargs,
                )
            else:
                cls._executors[key] = ThreadPoolExecutor(max_workers=max_workers)
        return cls._executors[key]

    @classmethod
    def shutdown_all(cls) -> None:
        """Shuts down all cached executors."""
        for key, executor in cls._executors.items():
            logger.debug("Shutting down persistent %s pool", key[0].name)
            executor.shutdown(wait=True)
        cls._executors.clear()


# Register cleanup on exit
atexit.register(_PoolManager.shutdown_all)


class ParallelRenderer:
    """Orchestrates parallel task execution with memory and hardware awareness.

    Features:
    - Automatic thread/process count detection.
    - Optimal chunking (batches aligned to thread count).
    - Aggregate memory monitoring.
    - Support for both ProcessPool (CPU speed) and ThreadPool (Memory efficiency).
    """

    def __init__(
        self,
        max_workers: int | None = None,
        mode: ExecutionMode = ExecutionMode.PROCESS,
        process_limit_mb: float = DEFAULT_PROCESS_LIMIT_MB,
        initializer: Callable | None = None,
        initargs: tuple[Any, ...] = (),
    ):
        """Initializes the parallel engine.

        Args:
            max_workers: Number of workers. Defaults to CPU_COUNT.
            mode: PROCESS or THREAD pool.
            process_limit_mb: Individual RAM limit for each process.
            initializer: Optional callable invoked at worker startup (PROCESS mode).
            initargs: Arguments passed to the initializer.
        """
        self.max_workers = max_workers or CPU_COUNT
        self.mode = mode
        self.process_limit_mb = process_limit_mb
        self.initializer = initializer
        self.initargs = initargs

    def _get_executor(self) -> ProcessPoolExecutor | ThreadPoolExecutor:
        """Retrieves a persistent executor from the PoolManager."""
        return _PoolManager.get_executor(self.mode, self.max_workers, self.initializer, self.initargs)

    def map_batches(
        self,
        func: Callable[[list[T]], Iterator[R]],
        tasks: Iterable[T],
        max_batch_size: int | None = None,
    ) -> Iterator[R]:
        """Groups tasks into optimal batches and maps a function over them.

        Each worker will receive a list of tasks instead of individual items.
        This is ideal for operations with high setup overhead (e.g., DB connections,
        context managers) that should be shared across multiple items.

        Args:
            func: Function that accepts a list of tasks and yields results.
            tasks: Iterable of task arguments.
            max_batch_size: Maximum tasks per batch. When set, batches are
                further subdivided to cap per-worker memory. Useful for heavy
                workloads where a single worker handling many items would
                exceed per-process memory limits.

        Yields:
            The results yielded by the worker function.
        """
        task_list = list(tasks)
        if not task_list:
            return

        # Calculate chunksize to have exactly one task-list per worker
        chunk_size = max(1, (len(task_list) + self.max_workers - 1) // self.max_workers)
        if max_batch_size is not None:
            chunk_size = min(chunk_size, max_batch_size)

        # Create the batches
        batches = [task_list[i : i + chunk_size] for i in range(0, len(task_list), chunk_size)]

        # Map over batches with chunksize=1 (each batch is one IPC message)
        for batch_results in self.map(func, batches, chunksize=1):
            yield from batch_results

    def map(
        self,
        func: Callable[..., R],
        tasks: Iterable[T],
        chunksize: int | None = None,
    ) -> Iterator[R]:
        """Maps a function over tasks in parallel.

        Args:
            func: The function to execute in workers.
            tasks: Iterable of task arguments.
            chunksize: Number of items per batch. If None, it is calculated
                to ensure the number of batches matches the worker count.

        Returns:
            Iterator of results.
        """
        task_list = list(tasks)
        if not task_list:
            return iter([])

        # Calculate chunksize to align with hardware threads if not provided
        # Formula: total_tasks // workers ensures 'workers' batches.
        if chunksize is None:
            chunksize = max(1, len(task_list) // self.max_workers)
            logger.debug(
                "Dynamic chunking: %d tasks / %d workers = chunksize %d",
                len(task_list),
                self.max_workers,
                chunksize,
            )

        executor = self._get_executor()
        for result in executor.map(func, task_list, chunksize=chunksize):
            yield result


def init_worker_path(path: str) -> None:
    """Worker process initializer: ensures a directory is importable.

    Pass this as the ``initializer`` to ParallelRenderer when worker functions
    live in a non-package directory (e.g., test modules).

    Args:
        path: Absolute directory to add to sys.path in each worker.
    """
    if path not in sys.path:
        sys.path.insert(0, path)


def worker_heartbeat(process_limit_mb: float = DEFAULT_PROCESS_LIMIT_MB) -> None:
    """Check current process RSS and raise if over limit. Must crash the worker.

    Should be called at significant milestones inside the worker function.
    """
    check_process_memory(process_limit_mb)
