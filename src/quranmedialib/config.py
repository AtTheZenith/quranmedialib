"""Centralized hardware and resource configuration for QuranMediaLib."""

from __future__ import annotations

import os

# Hardware detection
CPU_COUNT = os.cpu_count() or 1
DEFAULT_WORKERS = CPU_COUNT

# I/O Configuration
# Multiple threads for concurrent image compression and disk writes.
# 4 is a safe default for modern SSDs and multi-core CPUs.
DEFAULT_IO_THREADS = min(4, CPU_COUNT)

# SQLite Performance
SQLITE_MMAP_SIZE = 256 * 1024 * 1024  # 256MB for faster memory-mapped reads

# Memory and Resource Limits
DEFAULT_PROCESS_LIMIT_MB = 256.0
DEFAULT_AGGREGATE_LIMIT_MB = 2048.0
MEMORY_FLUSH_THRESHOLD_RATIO = 0.8  # Flush caches when usage exceeds 80% of limit
