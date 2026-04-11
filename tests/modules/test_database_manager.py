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
    """Test that database returns empty list for non-existent surah numbers."""
    db = DatabaseManager()

    # Surah 0 doesn't exist, should return empty list
    verses = db.get_verses_from_surah(0)
    assert verses == []

    # Surah 115 doesn't exist, should return empty list
    verses = db.get_verses_from_surah(115)
    assert verses == []


def test_database_manager_invalid_ayah_range() -> None:
    """Test that database returns empty string for non-existent ayah numbers."""
    db = DatabaseManager()

    # Ayah 0 doesn't exist, should return empty string
    verse = db.get_verse(1, 0)
    assert verse == ""

    # Ayah 1000 doesn't exist, should return empty string
    verse = db.get_verse(1, 1000)
    assert verse == ""


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

    # Should return empty list for non-existent surah
    verses = db.get_verses_from_surah(invalid_surah)
    assert verses == []


@pytest.mark.parametrize("invalid_ayah", [0, -1, 1000])
def test_database_manager_ayah_boundary(invalid_ayah: int) -> None:
    """Test ayah number boundary validation."""
    db = DatabaseManager()

    # Should return empty string for non-existent ayah
    verse = db.get_verse(1, invalid_ayah)
    assert verse == ""
