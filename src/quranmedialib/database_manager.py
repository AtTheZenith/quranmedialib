"""Stateful registry singleton for managing multiple database connections.

This module provides a DatabaseManager that:
- Maintains a registry of named database connections
- Provides dedicated methods for each data source (Quran, WBW, Translation)
- Supports dynamic switching between WBW and translation databases
- Auto-registers packaged databases on initialization
- Handles both standard verse-by-verse and word-by-word databases

Quran methods always use the "quran" database (unchangeable).
WBW and Translation methods use their respective active databases (configurable).
"""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
from types import TracebackType
from typing import Any, Optional, Self

from quranmedialib.types import (
    AyahNumber,
    DatabaseConfig,
    SurahNumber,
    WbwDatabaseConfig,
    WordIndex,
)

logger = logging.getLogger(__name__)

# SQL identifier validation (alphanumeric + underscore only)
_SQL_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_sql_identifier(name: str, context: str = "identifier") -> str:
    """Validate that a string is a safe SQL identifier.

    Args:
        name: The identifier to validate (table name, column name, etc.).
        context: Description of what the identifier represents (for error messages).

    Returns:
        The validated identifier.

    Raises:
        ValueError: If the identifier contains invalid characters.
    """
    if not _SQL_IDENTIFIER.match(name):
        raise ValueError(f"Invalid SQL {context}: {name!r}. Must be alphanumeric with underscores only.")
    return name


class DatabaseManager:
    """Manager for multiple database connections with dedicated methods for each data source.

    The DatabaseManager maintains separate connections for:
    - Quran text (always uses the "quran" database - unchangeable)
    - Word-by-word translations (uses active WBW database, default "wbw")
    - Verse translations (uses active translation database, default "translation")

    Quran methods always use the "quran" database.
    WBW methods use the active WBW database (configurable via set_active_wbw).
    Translation methods use the active translation database (configurable via set_active_translation).
    """

    _instance: Optional[Self] = None
    _lock = threading.Lock()

    # Default connection names
    DEFAULT_QURAN_NAME = "quran"
    DEFAULT_WBW_NAME = "wbw"
    DEFAULT_TRANSLATION_NAME = "translation"

    def __new__(cls) -> Self:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        """Initializes database connections and registers packaged databases.

        Automatically registers:
        - "quran": Default Quran text database
        - "wbw": Default word-by-word translation database
        - "translation": Default English translation (Sahih International)

        Raises:
            sqlite3.Error: If database initialization fails.
        """
        if getattr(self, "_initialized", False):
            return

        # Auto-close orphaned connections before re-initialization
        if hasattr(self, "_connections") and self._connections:
            logger.warning(
                "DatabaseManager re-initialized without calling .close() first. "
                "Automatically closing orphaned connections."
            )
            self.close()

        self._registry: dict[str, dict[str, Any]] = {}
        self._cursors: dict[str, sqlite3.Cursor] = {}
        self._connections: dict[str, sqlite3.Connection] = {}
        self._configs: dict[str, DatabaseConfig | WbwDatabaseConfig] = {}
        self._active_wbw: Optional[str] = None
        self._active_translation: Optional[str] = None
        self._lock = threading.Lock()

        try:
            # Import presets lazily to avoid circular import issues
            from quranmedialib.presets import DATABASE_EN_SAHIH, DATABASE_QURAN, DATABASE_WBW_EN

            # Register packaged databases with default names
            self._add_connection_internal(self.DEFAULT_QURAN_NAME, DATABASE_QURAN)
            self._add_connection_internal(self.DEFAULT_WBW_NAME, DATABASE_WBW_EN)
            self._add_connection_internal(self.DEFAULT_TRANSLATION_NAME, DATABASE_EN_SAHIH)

            # Set default active databases
            self._active_wbw = self.DEFAULT_WBW_NAME
            self._active_translation = self.DEFAULT_TRANSLATION_NAME
            self._initialized = True

            logger.info("DatabaseManager initialized with connections: %s", list(self._registry.keys()))
        except Exception:
            # Cleanup any partially-opened connections before re-raising
            self.close()
            raise

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def _validate_state(self) -> None:
        """Ensures the manager is initialized before performing operations."""
        if not getattr(self, "_initialized", False):
            raise RuntimeError("DatabaseManager is not initialized.")

    def _get_config(self, name: str) -> DatabaseConfig | WbwDatabaseConfig:
        """Get the config for a named database."""
        if name not in self._configs:
            raise KeyError(f"Unknown database: {name}")
        return self._configs[name]

    def _get_cursor(self, name: str) -> sqlite3.Cursor:
        """Get the cursor for a named database."""
        if name not in self._cursors:
            raise KeyError(f"Unknown database: {name}")
        return self._cursors[name]

    def _register_connection(self, name: str, config: DatabaseConfig | WbwDatabaseConfig) -> None:
        """Registers a connection and its cursor into the internal registry.

        Args:
            name: Unique name for the connection.
            config: Configuration object.
        """
        conn = sqlite3.connect(str(config.filepath), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        self._connections[name] = conn
        self._cursors[name] = cursor
        self._configs[name] = config
        self._registry[name] = {
            "config": config,
            "connection": conn,
            "cursor": cursor,
        }

    def _add_connection_internal(self, name: str, config: DatabaseConfig | WbwDatabaseConfig) -> None:
        """Internal method to add a connection without validation (used during initialization)."""
        try:
            self._register_connection(name, config)
            logger.debug("Added internal database connection '%s' -> %s", name, config.filepath)
        except sqlite3.Error as e:
            logger.error("Failed to add internal connection '%s': %s", name, e)
            raise

    def add_connection(self, name: str, config: DatabaseConfig | WbwDatabaseConfig) -> None:
        """Add a database connection to the registry.

        Args:
            name: Unique name for this connection.
            config: DatabaseConfig or WbwDatabaseConfig with connection details.
        """
        self._validate_state()

        try:
            self._register_connection(name, config)
            logger.info("Added database connection '%s' -> %s", name, config.filepath)
        except sqlite3.Error as e:
            logger.error("Failed to add connection '%s': %s", name, e)
            raise

    def set_active_translation(self, name: str) -> None:
        """Set the active translation database for subsequent translation fetch operations.

        Does not affect Quran or WBW methods.

        Args:
            name: Name of a registered translation database (e.g., "translation", "ur_jalandhry").

        Raises:
            KeyError: If the name is not a registered connection.
        """
        self._validate_state()
        if name not in self._registry:
            raise KeyError(f"Unknown translation: {name}. Available: {list(self._registry.keys())}")
        self._active_translation = name
        logger.debug("Active translation set to: %s", name)

    def get_active_translation_name(self) -> Optional[str]:
        """Get the name of the currently active translation."""
        return self._active_translation

    def set_active_wbw(self, name: str) -> None:
        """Set the active WBW database for subsequent WBW fetch operations.

        Does not affect Quran or Translation methods.

        Args:
            name: Name of a registered WBW database (e.g., "wbw", "wbw_urdu").

        Raises:
            KeyError: If the name is not a registered connection.
        """
        self._validate_state()
        if name not in self._registry:
            raise KeyError(f"Unknown WBW database: {name}. Available: {list(self._registry.keys())}")
        self._active_wbw = name
        logger.debug("Active WBW set to: %s", name)

    def get_active_wbw_name(self) -> Optional[str]:
        """Get the name of the currently active WBW database."""
        return self._active_wbw

    def _fetch(self, name: str, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Execute a query on a named database and return all rows.

        Args:
            name: Registered connection name.
            query: SQL query string.
            params: Parameters to bind to the query.

        Returns:
            List of result rows. Returns empty list on sqlite3 errors after logging.
        """
        cursor = self._get_cursor(name)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error("Query failed on DB '%s': %s | Query: %s", name, e, query)
            return []

    def _aggregate_verses(
        self,
        rows: list[sqlite3.Row],
        config: DatabaseConfig | WbwDatabaseConfig,
    ) -> list[str]:
        """Helper to aggregate verses by ayah number.

        Args:
            rows: Query results containing ayah and text columns.
            config: Database configuration for column name mapping.

        Returns:
            A list of verse strings, ordered by ayah number.
        """
        verses_dict: dict[int, list[str]] = {}
        for row in rows:
            ayah = row[config.ayah_col]
            if ayah not in verses_dict:
                verses_dict[ayah] = []
            verses_dict[ayah].append(row[config.text_col])

        return [" ".join(verses_dict[ayah]) for ayah in sorted(verses_dict.keys())]

    # === Quran Database Methods (always use "quran" database) ===

    def get_verses_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all Arabic verses from a specific surah.

        Always uses the "quran" database.

        Returns:
            A list of Arabic verse strings, ordered by ayah number.
        """
        config = self._get_config(self.DEFAULT_QURAN_NAME)

        # Validate identifiers to prevent SQL injection from untrusted configs
        tablename = _validate_sql_identifier(config.tablename, "table name")
        ayah_col = _validate_sql_identifier(config.ayah_col, "column name")
        text_col = _validate_sql_identifier(config.text_col, "column name")
        surah_col = _validate_sql_identifier(config.surah_col, "column name")

        query = f"""
            SELECT {ayah_col}, {text_col}
            FROM {tablename}
            WHERE {surah_col} = ?
            ORDER BY {ayah_col}
        """
        rows = self._fetch(self.DEFAULT_QURAN_NAME, query, (surah_number,))
        return self._aggregate_verses(rows, config)

    def get_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> str:
        """Fetches a specific Arabic verse text.

        Always uses the "quran" database.

        Returns:
            The Arabic verse text as a string.
        """
        config = self._get_config(self.DEFAULT_QURAN_NAME)

        tablename = _validate_sql_identifier(config.tablename, "table name")
        text_col = _validate_sql_identifier(config.text_col, "column name")
        surah_col = _validate_sql_identifier(config.surah_col, "column name")
        ayah_col = _validate_sql_identifier(config.ayah_col, "column name")

        query = f"""
            SELECT {text_col}
            FROM {tablename}
            WHERE {surah_col} = ? AND {ayah_col} = ?
        """
        rows = self._fetch(self.DEFAULT_QURAN_NAME, query, (surah_number, ayah_number))
        return " ".join(row[config.text_col] for row in rows)

    # === WBW Database Methods (use active WBW database) ===

    def get_wbw_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific surah.

        Uses the active WBW database (set via set_active_wbw, default "wbw").

        Returns:
            List of word translations in order.
        """
        name = self._active_wbw or self.DEFAULT_WBW_NAME
        config = self._get_config(name)

        tablename = _validate_sql_identifier(config.tablename, "table name")
        text_col = _validate_sql_identifier(config.text_col, "column name")
        surah_col = _validate_sql_identifier(config.surah_col, "column name")
        ayah_col = _validate_sql_identifier(config.ayah_col, "column name")
        word_id_col = _validate_sql_identifier(config.word_id_col, "column name")

        query = f"""
            SELECT {text_col}
            FROM {tablename}
            WHERE {surah_col} = ?
            ORDER BY {ayah_col}, {word_id_col}
        """
        rows = self._fetch(name, query, (surah_number,))
        return [row[config.text_col] for row in rows]

    def get_wbw_from_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific verse.

        Uses the active WBW database (set via set_active_wbw, default "wbw").

        Returns:
            List of word translations in order.
        """
        name = self._active_wbw or self.DEFAULT_WBW_NAME
        config = self._get_config(name)

        tablename = _validate_sql_identifier(config.tablename, "table name")
        text_col = _validate_sql_identifier(config.text_col, "column name")
        surah_col = _validate_sql_identifier(config.surah_col, "column name")
        ayah_col = _validate_sql_identifier(config.ayah_col, "column name")
        word_id_col = _validate_sql_identifier(config.word_id_col, "column name")

        query = f"""
            SELECT {text_col}
            FROM {tablename}
            WHERE {surah_col} = ? AND {ayah_col} = ?
            ORDER BY {word_id_col}
        """
        rows = self._fetch(name, query, (surah_number, ayah_number))
        return [row[config.text_col] for row in rows]

    def get_wbw_from_word(
        self,
        surah_number: SurahNumber,
        ayah_number: AyahNumber,
        word_index: WordIndex,
    ) -> Optional[str]:
        """Fetches the translation for a specific word in a specific verse.

        Uses the active WBW database (set via set_active_wbw, default "wbw").

        Args:
            surah_number: The surah number.
            ayah_number: The ayah (verse) number.
            word_index: The 1-indexed word position within the verse.

        Returns:
            The translation string or None if not found.
        """
        name = self._active_wbw or self.DEFAULT_WBW_NAME
        config = self._get_config(name)

        tablename = _validate_sql_identifier(config.tablename, "table name")
        text_col = _validate_sql_identifier(config.text_col, "column name")
        surah_col = _validate_sql_identifier(config.surah_col, "column name")
        ayah_col = _validate_sql_identifier(config.ayah_col, "column name")
        word_id_col = _validate_sql_identifier(config.word_id_col, "column name")

        query = f"""
            SELECT {text_col}
            FROM {tablename}
            WHERE {surah_col} = ? AND {ayah_col} = ? AND {word_id_col} = ?
        """
        rows = self._fetch(name, query, (surah_number, ayah_number, word_index))
        return rows[0][config.text_col] if rows else None

    def get_wbw_grouped_by_verse(
        self,
        surah_number: SurahNumber,
    ) -> dict[int, list[str]]:
        """Fetches all word-by-word translations for a surah, grouped by ayah.

        Uses the active WBW database (set via set_active_wbw, default "wbw").
        This method fetches all WBW data for a surah in a single query,
        eliminating the N+1 query pattern when processing multiple verses.

        Args:
            surah_number: The surah number (1-114).

        Returns:
            Dictionary mapping ayah numbers to their lists of word translations.
            Example: {1: ["word1", "word2", ...], 2: ["word1", ...], ...}
        """
        name = self._active_wbw or self.DEFAULT_WBW_NAME
        config = self._get_config(name)

        tablename = _validate_sql_identifier(config.tablename, "table name")
        ayah_col = _validate_sql_identifier(config.ayah_col, "column name")
        text_col = _validate_sql_identifier(config.text_col, "column name")
        surah_col = _validate_sql_identifier(config.surah_col, "column name")
        word_id_col = _validate_sql_identifier(config.word_id_col, "column name")

        query = f"""
            SELECT {ayah_col}, {word_id_col}, {text_col}
            FROM {tablename}
            WHERE {surah_col} = ?
            ORDER BY {ayah_col}, {word_id_col}
        """
        rows = self._fetch(name, query, (surah_number,))

        result: dict[int, list[str]] = {}
        for row in rows:
            ayah = row[config.ayah_col]
            if ayah not in result:
                result[ayah] = []
            result[ayah].append(row[config.text_col])

        return result

    # === Translation Database Methods (use active translation database) ===

    def get_translation_from_surah(
        self,
        surah_number: SurahNumber,
        translation_name: str | None = None,
    ) -> list[str]:
        """Fetches all verse translations for a specific surah.

        Args:
            surah_number: The surah number.
            translation_name: Optional name of the translation database to use.
                If None, uses the active translation (set via set_active_translation).

        Returns:
            List of verse translations (one per verse).
        """
        name = translation_name or (self._active_translation or self.DEFAULT_TRANSLATION_NAME)
        config = self._get_config(name)

        tablename = _validate_sql_identifier(config.tablename, "table name")
        text_col = _validate_sql_identifier(config.text_col, "column name")
        surah_col = _validate_sql_identifier(config.surah_col, "column name")
        ayah_col = _validate_sql_identifier(config.ayah_col, "column name")

        query = f"""
            SELECT {text_col}
            FROM {tablename}
            WHERE {surah_col} = ?
            ORDER BY {ayah_col}
        """
        rows = self._fetch(name, query, (surah_number,))
        return [row[config.text_col] for row in rows]

    def get_translation_from_verse(
        self,
        surah_number: SurahNumber,
        ayah_number: AyahNumber,
        translation_name: str | None = None,
    ) -> str | None:
        """Fetches the translation for a specific verse.

        Args:
            surah_number: The surah number.
            ayah_number: The ayah (verse) number.
            translation_name: Optional name of the translation database to use.
                If None, uses the active translation (set via set_active_translation).

        Returns:
            The verse translation string or None if not found.
        """
        name = translation_name or (self._active_translation or self.DEFAULT_TRANSLATION_NAME)
        config = self._get_config(name)

        tablename = _validate_sql_identifier(config.tablename, "table name")
        text_col = _validate_sql_identifier(config.text_col, "column name")
        surah_col = _validate_sql_identifier(config.surah_col, "column name")
        ayah_col = _validate_sql_identifier(config.ayah_col, "column name")

        query = f"""
            SELECT {text_col}
            FROM {tablename}
            WHERE {surah_col} = ? AND {ayah_col} = ?
        """
        rows = self._fetch(name, query, (surah_number, ayah_number))
        return rows[0][config.text_col] if rows else None

    def get_translations_from_verse_range(
        self,
        surah_number: SurahNumber,
        start_ayah: AyahNumber,
        end_ayah: AyahNumber,
        translation_name: str | None = None,
    ) -> list[str]:
        """Fetches translations for a range of verses in a single query.

        Args:
            surah_number: The surah number.
            start_ayah: Starting ayah number (1-indexed, inclusive).
            end_ayah: Ending ayah number (inclusive).
            translation_name: Optional name of the translation database to use.
                If None, uses the active translation (set via set_active_translation).

        Returns:
            List of verse translations in order by ayah number.

        Raises:
            ValueError: If any ayah in the requested range is missing from the database.
        """
        name = translation_name or (self._active_translation or self.DEFAULT_TRANSLATION_NAME)
        config = self._get_config(name)

        tablename = _validate_sql_identifier(config.tablename, "table name")
        ayah_col = _validate_sql_identifier(config.ayah_col, "column name")
        text_col = _validate_sql_identifier(config.text_col, "column name")
        surah_col = _validate_sql_identifier(config.surah_col, "column name")

        query = f"""
            SELECT {ayah_col}, {text_col}
            FROM {tablename}
            WHERE {surah_col} = ? AND {ayah_col} BETWEEN ? AND ?
            ORDER BY {ayah_col}
        """
        rows = self._fetch(name, query, (surah_number, start_ayah, end_ayah))

        # Group by ayah and return in order
        verses_dict: dict[int, str] = {}
        for row in rows:
            ayah = row[config.ayah_col]
            verses_dict[ayah] = row[config.text_col]

        # Check for missing ayahs and raise error if any are missing
        missing_ayah = [ayah for ayah in range(start_ayah, end_ayah + 1) if ayah not in verses_dict]
        if missing_ayah:
            raise ValueError(
                f"Missing translations for ayah(s) {missing_ayah} in surah {surah_number}. "
                f"Database may be corrupted or incomplete."
            )

        return [verses_dict[ayah] for ayah in range(start_ayah, end_ayah + 1)]

    def list_connections(self) -> list[str]:
        """List all registered connection names."""
        return list(self._registry.keys())

    def close(self) -> None:
        """Closes all database connections and invalidates the instance state."""
        if not getattr(self, "_initialized", False):
            return

        for name, conn in self._connections.items():
            if conn:
                conn.close()
                logger.debug("Closed connection: %s", name)

        self._connections.clear()
        self._cursors.clear()
        self._configs.clear()
        self._registry.clear()
        self._active_wbw = None
        self._active_translation = None
        self._initialized = False

        # Reset singleton instance so next DatabaseManager() creates a fresh instance
        type(self)._instance = None

        logger.info("DatabaseManager closed. All connections closed.")
