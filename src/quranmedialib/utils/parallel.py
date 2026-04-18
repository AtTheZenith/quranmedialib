"""General-purpose parallel processing engine for QuranMediaLib.

This module provides the ParallelRenderer, a robust utility that manages
worker pools with hardware-aware scaling, optimal chunking, and memory
resource safety.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from enum import Enum, auto
from typing import Callable, Iterable, Iterator, TypeVar

from quranmedialib.utils.memory import (
    DEFAULT_AGGREGATE_LIMIT_MB,
    DEFAULT_PROCESS_LIMIT_MB,
    MemoryMonitor,
    check_process_memory,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class ExecutionMode(Enum):
    """Supported hardware execution strategies."""

    PROCESS = auto()
    THREAD = auto()


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
        memory_limit_mb: float = DEFAULT_AGGREGATE_LIMIT_MB,
        process_limit_mb: float = DEFAULT_PROCESS_LIMIT_MB,
    ):
        """Initializes the parallel engine.

        Args:
            max_workers: Number of workers. Defaults to os.cpu_count().
            mode: PROCESS or THREAD pool.
            memory_limit_mb: Aggregate RAM limit for the entire pool.
            process_limit_mb: Individual RAM limit for each process.
        """
        self.max_workers = max_workers or os.cpu_count() or 1
        self.mode = mode
        self.memory_limit_mb = memory_limit_mb
        self.process_limit_mb = process_limit_mb

    def _get_executor(self) -> ProcessPoolExecutor | ThreadPoolExecutor:
        """Creates the appropriate executor based on mode."""
        if self.mode == ExecutionMode.PROCESS:
            return ProcessPoolExecutor(max_workers=self.max_workers)
        return ThreadPoolExecutor(max_workers=self.max_workers)

    def map(
        self,
        func: Callable[..., R],
        tasks: Iterable[T],
        chunksize: int | None = None,
        use_monitor: bool = True,
    ) -> Iterator[R]:
        """Maps a function over tasks in parallel.

        Args:
            func: The function to execute in workers.
            tasks: Iterable of task arguments.
            chunksize: Number of items per batch. If None, it is calculated
                to ensure the number of batches matches the worker count.
            use_monitor: Whether to enable aggregate memory monitoring.

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

        monitor = MemoryMonitor(limit_mb=self.memory_limit_mb) if use_monitor else None

        try:
            if monitor:
                monitor.__enter__()

            with self._get_executor() as executor:
                # Note: ProcessPoolExecutor.map supports chunksize
                # ThreadPoolExecutor.map ignores chunksize but we pass it for consistency
                results = executor.map(func, task_list, chunksize=chunksize)
                yield from results

        finally:
            if monitor:
                monitor.__exit__(None, None, None)


def worker_heartbeat(process_limit_mb: float = DEFAULT_PROCESS_LIMIT_MB) -> None:
    """Utility for workers to check their own memory budget.

    Should be called inside the worker function at significant milestones.
    """
    try:
        check_process_memory(process_limit_mb)
    except Exception as e:
        logger.warning("Worker heartbeat detected memory issue: %s", e)
        # We don't necessarily want to kill the process immediately if it can finish,
        # but we should log it.
        raise
