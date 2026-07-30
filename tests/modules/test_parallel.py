"""Tests for parallel processing and memory enforcement utilities."""

from unittest.mock import patch

import pytest

from quranmedialib.config import DEFAULT_PROCESS_LIMIT_MB
from quranmedialib.utils.memory import MemoryLimitExceededError, check_process_memory
from quranmedialib.utils.parallel import worker_heartbeat


class TestCheckProcessMemory:
    """Tests for check_process_memory() — the underlying RSS enforcement."""

    def test_below_limit_passes(self) -> None:
        """Should not raise when RSS is under limit."""
        with patch("quranmedialib.utils.memory.get_current_rss_mb", return_value=100.0):
            check_process_memory(DEFAULT_PROCESS_LIMIT_MB)

    def test_above_limit_raises(self) -> None:
        """Should raise MemoryLimitExceededError when RSS exceeds limit."""
        with patch("quranmedialib.utils.memory.get_current_rss_mb", return_value=300.0):
            with pytest.raises(MemoryLimitExceededError) as exc:
                check_process_memory(DEFAULT_PROCESS_LIMIT_MB)  # 256
        assert "300.00MB" in str(exc.value)
        assert f"{DEFAULT_PROCESS_LIMIT_MB:.2f}MB" in str(exc.value)

    def test_exact_limit_under(self) -> None:
        """RSS exactly at limit should not raise (limit is exclusive)."""
        with patch("quranmedialib.utils.memory.get_current_rss_mb", return_value=DEFAULT_PROCESS_LIMIT_MB):
            check_process_memory(DEFAULT_PROCESS_LIMIT_MB)

    def test_custom_limit(self) -> None:
        """Should respect custom limit_mb argument."""
        with patch("quranmedialib.utils.memory.get_current_rss_mb", return_value=512.0):
            with pytest.raises(MemoryLimitExceededError):
                check_process_memory(256.0)
            check_process_memory(600.0)


class TestWorkerHeartbeat:
    """Tests for worker_heartbeat() — the worker-facing RSS check."""

    def test_below_limit_passes(self) -> None:
        """Should not raise when RSS is under default limit."""
        with patch("quranmedialib.utils.memory.get_current_rss_mb", return_value=100.0):
            worker_heartbeat()

    def test_above_limit_raises(self) -> None:
        """Should raise MemoryLimitExceededError (crash the worker)."""
        with patch("quranmedialib.utils.memory.get_current_rss_mb", return_value=300.0):
            with pytest.raises(MemoryLimitExceededError):
                worker_heartbeat()

    def test_custom_limit_raises_at_lower_threshold(self) -> None:
        """Custom limit should trigger breach earlier than default."""
        with patch("quranmedialib.utils.memory.get_current_rss_mb", return_value=100.0):
            with pytest.raises(MemoryLimitExceededError):
                worker_heartbeat(50.0)

    def test_custom_limit_allows_at_higher_threshold(self) -> None:
        """Custom limit above RSS should pass."""
        with patch("quranmedialib.utils.memory.get_current_rss_mb", return_value=100.0):
            worker_heartbeat(200.0)

    def test_zero_limit_always_fails(self) -> None:
        """With limit=0, any positive RSS triggers breach."""
        with patch("quranmedialib.utils.memory.get_current_rss_mb", return_value=1.0):
            with pytest.raises(MemoryLimitExceededError):
                worker_heartbeat(0.0)

    def test_default_limit_matches_config(self) -> None:
        """Default limit should equal config.DEFAULT_PROCESS_LIMIT_MB."""
        with patch("quranmedialib.utils.memory.get_current_rss_mb", return_value=DEFAULT_PROCESS_LIMIT_MB + 1):
            with pytest.raises(MemoryLimitExceededError):
                worker_heartbeat()
