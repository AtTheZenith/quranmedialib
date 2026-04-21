"""Resource loader for packaged assets using importlib.resources.

This module provides a unified interface for accessing font and database files
that are shipped with the package. It uses importlib.resources.files() to get
absolute paths directly from the installed package location, with no temp file
extraction.
"""

from __future__ import annotations

import sqlite3
from importlib.resources import files
from pathlib import Path

# Package reference for importlib.resources
_PACKAGE = "quranmedialib"
_ASSETS = "assets"


def get_asset_path(relative_path: str) -> Path:
    """Get the absolute path to a packaged asset file.

    Uses importlib.resources.files() to resolve the path directly from the
    installed package location. No temp file extraction is performed.

    Args:
        relative_path: Path relative to the assets directory (e.g., "hafs.otf").

    Returns:
        Absolute Path to the asset file.

    Raises:
        ValueError: If the path contains traversal components ("..") or is absolute.
        FileNotFoundError: If the asset does not exist in the package.
    """
    # Security: prevent path traversal attacks
    if ".." in relative_path.split("/") or ".." in relative_path.split("\\"):
        raise ValueError(f"Invalid asset path: {relative_path!r}. Path traversal components ('..') are not allowed.")
    if Path(relative_path).is_absolute():
        raise ValueError(f"Invalid asset path: {relative_path!r}. Absolute paths are not allowed.")

    asset_path = files(_PACKAGE) / _ASSETS / relative_path
    # Convert to filesystem path (works for both installed and editable installs)
    return Path(str(asset_path))


def get_font_path(font_name: str) -> Path:
    """Get the absolute path to a packaged font file.

    Args:
        font_name: Name of the font file (e.g., "hafs.otf", "inter.ttf").

    Returns:
        Absolute Path to the font file.

    Raises:
        FileNotFoundError: If the font does not exist in the package.
    """
    return get_asset_path(font_name)


def get_db_path(db_name: str) -> Path:
    """Get the absolute path to a packaged database file.

    Args:
        db_name: Name of the database file (e.g., "quran.db", "en_sahih.db").

    Returns:
        Absolute Path to the database file.

    Raises:
        FileNotFoundError: If the database does not exist in the package.
    """
    return get_asset_path(db_name)


def verify_asset_exists(relative_path: str) -> bool:
    """Check if an asset exists in the package without raising an exception.

    Args:
        relative_path: Path relative to the assets directory.

    Returns:
        True if the asset exists, False otherwise.
    """
    try:
        path = get_asset_path(relative_path)
        return path.is_file()
    except (FileNotFoundError, OSError):
        return False


def get_sqlite_connection(db_name: str, **kwargs) -> sqlite3.Connection:
    """Open a SQLite connection to a packaged database.

    The database is accessed in-place from the package location. For read-only
    access (recommended for packaged databases), use:

        conn = get_sqlite_connection("quran.db", readonly=True)

    Args:
        db_name: Name of the database file.
        **kwargs: Additional arguments passed to sqlite3.connect().

    Returns:
        SQLite connection object.
    """
    db_path = get_db_path(db_name)
    # For packaged databases, default to read-only mode
    if "readonly" not in kwargs:
        kwargs["readonly"] = True

    readonly = kwargs.pop("readonly")
    if readonly:
        # Open in read-only mode using URI
        uri = f"file:{db_path}?mode=ro"
        return sqlite3.connect(uri, uri=True, **kwargs)
    else:
        return sqlite3.connect(str(db_path), **kwargs)
