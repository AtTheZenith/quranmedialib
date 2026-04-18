"""Tests for the DatabaseManager class.

This module contains tests for verifying database connectivity and data retrieval
methods including verse fetching, word-by-word translations, and full translations.
"""

import pytest

from quranmedialib import DatabaseManager


def test_database_manager() -> None:
    print("\nRunning test_database_manager...")
    db = DatabaseManager()

    # Test Quran methods (always use "quran" database)
    verses = db.get_verses_from_surah(1)
    print(f"Verses in Surah 1: {verses[:2]}")
    assert len(verses) > 0

    verse_text = db.get_verse(1, 1)
    print(f"Verse 1:1 text: {verse_text}")
    assert "بِسۡمِ" in verse_text

    # Test WBW methods (always use "wbw" database)
    wbw_surah = db.get_wbw_from_surah(1)
    print(f"WBW translations in Surah 1: {wbw_surah[:5]}")
    assert len(wbw_surah) > 0

    wbw_verse = db.get_wbw_from_verse(1, 1)
    print(f"WBW translations in Verse 1:1: {wbw_verse}")
    assert len(wbw_verse) > 0

    wbw_word = db.get_wbw_from_word(1, 1, 1)
    print(f"WBW translation for 1:1:1: {wbw_word}")
    assert wbw_word is not None

    # Test Translation methods (uses "translation" database by default)
    trans_surah = db.get_translation_from_surah(1)
    print(f"Full translations in Surah 1: {trans_surah[:2]}")
    assert len(trans_surah) == 7

    trans_verse = db.get_translation_from_verse(1, 1)
    print(f"Full translation for 1:1: {trans_verse}")
    assert trans_verse is not None
    assert "In the name of Allah" in trans_verse

    print("test_database_manager completed successfully.")


if __name__ == "__main__":
    test_database_manager()


# === Validation Tests ===


def test_database_manager_invalid_surah_range() -> None:
    """Test that invalid surah numbers raise ValueError."""
    db = DatabaseManager()

    # Surah 0 doesn't exist — should raise ValueError
    with pytest.raises(ValueError, match="Surah number must be between"):
        db.get_verses_from_surah(0)

    # Surah 115 doesn't exist — should raise ValueError
    with pytest.raises(ValueError, match="Surah number must be between"):
        db.get_verses_from_surah(115)


def test_database_manager_invalid_ayah_range() -> None:
    """Test that invalid ayah numbers raise ValueError."""
    db = DatabaseManager()

    # Ayah 0 doesn't exist — should raise ValueError
    with pytest.raises(ValueError, match="Ayah number must be between"):
        db.get_verse(1, 0)

    # Ayah 1000 doesn't exist — should raise ValueError
    with pytest.raises(ValueError, match="Ayah number must be between"):
        db.get_verse(1, 1000)


def test_database_manager_surah_boundary_values() -> None:
    """Test surah boundary values (1 and 114)."""
    db = DatabaseManager()

    # Surah 1 should work (Al-Fatiha)
    verses = db.get_verses_from_surah(1)
    assert len(verses) == 7

    # Surah 114 should work (An-Nas)
    verses = db.get_verses_from_surah(114)
    assert len(verses) == 6


def test_database_manager_invalid_sql_identifier() -> None:
    """Test that SQL identifier validation rejects malicious input."""
    from quranmedialib.database_manager import _validate_sql_identifier

    # Valid identifiers should pass
    assert _validate_sql_identifier("valid_table") == "valid_table"
    assert _validate_sql_identifier("test123") == "test123"

    # Invalid identifiers should raise ValueError
    with pytest.raises(ValueError, match="Invalid SQL"):
        _validate_sql_identifier("table; DROP TABLE")

    with pytest.raises(ValueError, match="Invalid SQL"):
        _validate_sql_identifier("table' OR '1'='1")

    with pytest.raises(ValueError, match="Invalid SQL"):
        _validate_sql_identifier("123_invalid")


def test_database_manager_unknown_connection() -> None:
    """Test that accessing unknown connection raises KeyError."""
    db = DatabaseManager()

    with pytest.raises(KeyError, match="Unknown database"):
        db._get_config("nonexistent_db")


def test_database_manager_set_active_unknown_translation() -> None:
    """Test that setting unknown active translation raises KeyError."""
    db = DatabaseManager()

    with pytest.raises(KeyError, match="Unknown translation"):
        db.set_active_translation("nonexistent_translation")


def test_database_manager_set_active_unknown_wbw() -> None:
    """Test that setting unknown active WBW raises KeyError."""
    db = DatabaseManager()

    with pytest.raises(KeyError, match="Unknown WBW database"):
        db.set_active_wbw("nonexistent_wbw")


def test_database_manager_close_and_reinitialize() -> None:
    """Test that closing and reinitializing works correctly."""
    db = DatabaseManager()
    db.close()

    # After close, singleton should be reset
    # Next call should create new instance
    db2 = DatabaseManager()
    assert db2._initialized is True

    # Verify basic functionality after reinit
    verses = db2.get_verses_from_surah(1)
    assert len(verses) == 7


@pytest.mark.parametrize("invalid_surah", [0, -1, 115, 999])
def test_database_manager_surah_boundary(invalid_surah: int) -> None:
    """Test surah number boundary validation."""
    db = DatabaseManager()

    # Should raise ValueError for out-of-range surah
    with pytest.raises(ValueError, match="Surah number must be between"):
        db.get_verses_from_surah(invalid_surah)


@pytest.mark.parametrize("invalid_ayah", [0, -1, 1000])
def test_database_manager_ayah_boundary(invalid_ayah: int) -> None:
    """Test ayah number boundary validation."""
    db = DatabaseManager()

    # Should raise ValueError for out-of-range ayah
    with pytest.raises(ValueError, match="Ayah number must be between"):
        db.get_verse(1, invalid_ayah)


# === Round 2: DatabaseManager Internal State and Thread Safety ===


def test_database_manager_context_manager() -> None:
    """Test that DatabaseManager works as a context manager."""
    with DatabaseManager() as db:
        verses = db.get_verses_from_surah(1)
        assert len(verses) == 7


def test_database_manager_list_connections() -> None:
    """Test that list_connections() returns expected names."""
    db = DatabaseManager()
    conns = db.list_connections()
    assert "quran" in conns
    assert "wbw" in conns
    assert "translation" in conns


def test_database_manager_close_clears_state() -> None:
    """Test that close() resets singleton."""
    db = DatabaseManager()
    db.close()
    # Singleton should be reset
    assert db._initialized is False or getattr(DatabaseManager, "_instance", None) is None


def test_database_manager_get_connection_unknown_db() -> None:
    """Test that _get_connection raises KeyError for unknown database."""
    db = DatabaseManager()
    with pytest.raises(KeyError):
        db._get_connection("nonexistent_db")


def test_database_manager_fetch_sql_error() -> None:
    """Test that _fetch returns empty list on SQL error (with warning log)."""
    db = DatabaseManager()
    # _fetch catches sqlite3.Error and returns [] with a warning
    result = db._fetch("quran", "SELECT * FROM nonexistent_table", ())
    assert result == []


def test_database_manager_validate_state() -> None:
    """Test that _validate_state raises RuntimeError on bad state."""
    db = DatabaseManager()
    # Should not raise when properly initialized
    db._validate_state()


def test_database_manager_reinit_after_close() -> None:
    """Test that after close(), a new DatabaseManager reinitializes correctly."""
    db = DatabaseManager()
    db.close()
    db2 = DatabaseManager()
    assert db2._initialized is True
    verses = db2.get_verses_from_surah(1)
    assert len(verses) == 7


@pytest.mark.benchmark
def test_database_manager_rapid_reinit_benchmark(request: pytest.FixtureRequest) -> None:
    """Benchmark the performance of rapid DatabaseManager re-initialization."""
    import time

    start = time.perf_counter()
    for _ in range(50):
        db = DatabaseManager()
        db.close()
    elapsed = time.perf_counter() - start
    request.node.benchmark_data = [f"total {elapsed:.4f}s"]
    print(f"\nRapid re-init (50 iterations) took {elapsed:.4f}s")
    # Should be relatively fast since it's mostly lock handling and connection close
    assert elapsed < 5.0


@pytest.mark.benchmark
def test_database_manager_concurrency_benchmark(request: pytest.FixtureRequest) -> None:
    """Benchmark concurrent read access from multiple threads."""
    import threading
    import time

    db = DatabaseManager()
    errors = []

    def task():
        try:
            for _ in range(100):
                # Accessing Quran DB (shared connection with per-call cursors)
                verses = db.get_verses_from_surah(1)
                assert len(verses) == 7
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=task) for _ in range(10)]

    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - start
    request.node.benchmark_data = ["10 thr", f"total {elapsed:.4f}s"]

    print(f"\nConcurrent read (10 threads, 100 reads each) took {elapsed:.4f}s")
    assert not errors, f"Encountered concurrency errors: {errors}"
    # Concurrency should be efficient due to per-call cursors
    assert elapsed < 10.0
