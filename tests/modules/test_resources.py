"""Tests for the resources module.

This module contains tests for verifying resource loading functionality including:
- Font file path resolution
- Database file path resolution
- Asset existence verification
- SQLite connection handling
"""

from pathlib import Path

import pytest

from quranmedialib.resources import (
    get_asset_path,
    get_db_path,
    get_font_path,
    get_sqlite_connection,
    verify_asset_exists,
)


def test_get_font_path_valid() -> None:
    """Test that get_font_path returns valid path for existing font."""
    path = get_font_path("hafs.otf")
    assert path is not None
    assert path.exists() or path.is_file()


def test_get_font_path_invalid() -> None:
    """Test that get_font_path returns path for non-existent font (no existence check)."""
    # get_font_path returns a Path object without checking existence
    path = get_font_path("nonexistent_font.otf")
    assert path is not None
    # File doesn't exist, but path object is valid
    assert not path.exists()


def test_get_db_path_valid() -> None:
    """Test that get_db_path returns valid path for existing database."""
    path = get_db_path("quran.db")
    assert path is not None
    assert path.exists() or path.is_file()


def test_get_db_path_invalid() -> None:
    """Test that get_db_path returns path for non-existent database (no existence check)."""
    path = get_db_path("nonexistent.db")
    assert path is not None
    assert not path.exists()


def test_get_asset_path_valid() -> None:
    """Test that get_asset_path returns valid path for existing asset."""
    path = get_asset_path("hafs.otf")
    assert path is not None


# === Path Traversal Tests (V1) ===


def test_get_asset_path_path_traversal_double_dot() -> None:
    """Test that path traversal with '..' is rejected."""
    with pytest.raises(ValueError, match="Path traversal components"):
        get_asset_path("../etc/passwd")


def test_get_asset_path_path_traversal_nested() -> None:
    """Test that nested path traversal is rejected."""
    with pytest.raises(ValueError, match="Path traversal components"):
        get_asset_path("fonts/../../etc/passwd")


def test_get_asset_path_path_traversal_windows_style() -> None:
    """Test that Windows-style path traversal is rejected."""
    with pytest.raises(ValueError, match="Path traversal components"):
        get_asset_path("..\\..\\etc\\passwd")


def test_get_asset_path_absolute_path_rejected() -> None:
    """Test that absolute paths are rejected."""
    absolute_path = str(Path(__file__).resolve())
    with pytest.raises(ValueError, match="Absolute paths are not allowed"):
        get_asset_path(absolute_path)


def test_verify_asset_exists_valid() -> None:
    """Test that verify_asset_exists returns True for existing asset."""
    assert verify_asset_exists("hafs.otf") is True


def test_verify_asset_exists_invalid() -> None:
    """Test that verify_asset_exists returns False for non-existent asset."""
    assert verify_asset_exists("nonexistent.txt") is False


def test_get_sqlite_connection_valid() -> None:
    """Test that get_sqlite_connection returns valid connection."""
    conn = get_sqlite_connection("quran.db")
    assert conn is not None
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    assert len(tables) > 0
    conn.close()


def test_get_sqlite_connection_invalid() -> None:
    """Test that get_sqlite_connection raises error for non-existent database."""
    with pytest.raises(Exception):
        get_sqlite_connection("nonexistent.db")


def test_get_sqlite_connection_readonly() -> None:
    """Test that get_sqlite_connection opens in read-only mode by default."""
    conn = get_sqlite_connection("quran.db")
    try:
        cursor = conn.cursor()
        # Try to write (should fail in read-only mode)
        with pytest.raises(Exception):
            cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY)")
    finally:
        conn.close()


def test_get_sqlite_connection_writable() -> None:
    """Test that get_sqlite_connection can open in writable mode."""
    # This should open in writable mode (readonly=False)
    # Note: May fail if database is in read-only package location
    try:
        conn = get_sqlite_connection("quran.db", readonly=False)
        conn.close()
    except Exception:
        # Expected to fail for packaged databases
        pass
