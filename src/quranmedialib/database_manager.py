"""Stateful registry singleton for managing multiple database connections.

This module provides a DatabaseManager that:
- Maintains a registry of named database connections
- Supports dynamic switching between active translation databases
- Auto-registers packaged databases on initialization
- Handles both standard verse-by-verse and word-by-word databases
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from typing import Any, Optional, Self, Union

from quranmedialib.types import (
    AyahNumber,
    DatabaseConfig,
    SurahNumber,
    WbwDatabaseConfig,
    WordIndex,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton manager for multiple database connections with active state switching.

    The DatabaseManager maintains a registry of named connections and allows
    switching between them using set_active_translation(). All fetch methods
    operate on the currently active connection.

    Example:
        db = DatabaseManager()

        # Use default English translation
        verses = db.get_verses_from_surah(1)

        # Switch to a custom translation
        db.set_active_translation("my_custom_db")
        verses = db.get_verses_from_surah(1)

        # Access word-by-word data
        db.set_active_translation("wbw")
        wbw = db.get_wbw_from_verse(1, 1)
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

        The active translation is set to "translation" by default.
        """
        if getattr(self, "_initialized", False):
            return

        self._registry: dict[str, dict[str, Any]] = {}
        self._cursors: dict[str, sqlite3.Cursor] = {}
        self._connections: dict[str, sqlite3.Connection] = {}
        self._configs: dict[str, Union[DatabaseConfig, WbwDatabaseConfig]] = {}
        self._active_translation: Optional[str] = None
        self._lock = threading.Lock()

        try:
            # Import presets lazily to avoid circular import issues
            from quranmedialib.presets import DATABASE_EN_SAHIH, DATABASE_QURAN, DATABASE_WBW_EN

            # Register packaged databases with default names
            # (skip validation during initialization)
            self._add_connection_internal(self.DEFAULT_QURAN_NAME, DATABASE_QURAN)
            self._add_connection_internal(self.DEFAULT_WBW_NAME, DATABASE_WBW_EN)
            self._add_connection_internal(self.DEFAULT_TRANSLATION_NAME, DATABASE_EN_SAHIH)

            # Set default active translation
            self._active_translation = self.DEFAULT_TRANSLATION_NAME
            self._initialized = True

            logger.info("DatabaseManager initialized with connections: %s", list(self._registry.keys()))
        except sqlite3.Error as e:
            logger.error("Failed to initialize DatabaseManager: %s", e)
            raise

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _validate_state(self) -> None:
        """Ensures the manager is initialized before performing operations."""
        if not getattr(self, "_initialized", False):
            raise RuntimeError("DatabaseManager is not initialized.")

    def _get_active_config(self) -> Union[DatabaseConfig, WbwDatabaseConfig]:
        """Get the config for the currently active translation."""
        if self._active_translation is None:
            raise RuntimeError("No active translation set. Call set_active_translation() first.")
        if self._active_translation not in self._configs:
            raise KeyError(f"Unknown translation: {self._active_translation}")
        return self._configs[self._active_translation]

    def _get_active_cursor(self) -> sqlite3.Cursor:
        """Get the cursor for the currently active translation."""
        if self._active_translation is None:
            raise RuntimeError("No active translation set. Call set_active_translation() first.")
        if self._active_translation not in self._cursors:
            raise KeyError(f"Unknown translation: {self._active_translation}")
        return self._cursors[self._active_translation]

    def _add_connection_internal(self, name: str, config: Union[DatabaseConfig, WbwDatabaseConfig]) -> None:
        """Internal method to add a connection without validation (used during initialization)."""
        try:
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

            logger.debug("Added internal database connection '%s' -> %s", name, config.filepath)
        except sqlite3.Error as e:
            logger.error("Failed to add internal connection '%s': %s", name, e)
            raise

    def add_connection(self, name: str, config: Union[DatabaseConfig, WbwDatabaseConfig]) -> None:
        """Add a database connection to the registry.

        Args:
            name: Unique name for this connection (used with set_active_translation).
            config: DatabaseConfig or WbwDatabaseConfig with connection details.
        """
        self._validate_state()

        try:
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

            logger.info("Added database connection '%s' -> %s", name, config.filepath)
        except sqlite3.Error as e:
            logger.error("Failed to add connection '%s': %s", name, e)
            raise

    def set_active_translation(self, name: str) -> None:
        """Set the active translation database for subsequent fetch operations.

        Args:
            name: Name of a registered connection (e.g., "translation", "wbw").

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

    def list_connections(self) -> list[str]:
        """List all registered connection names."""
        return list(self._registry.keys())

    def _fetch(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Execute a query on the active translation database."""
        cursor = self._get_active_cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error("Query failed on '%s': %s | Query: %s", self._active_translation, e, query)
            return []

    def _aggregate_verses(self, rows: list[sqlite3.Row], config: DatabaseConfig | WbwDatabaseConfig, order_by_word: bool = False) -> list[str]:
        """Helper to aggregate verses by ayah number.

        Args:
            rows: Query results containing ayah and text columns.
            config: Database configuration for column name mapping.
            order_by_word: If True, rows are ordered by word_id within each ayah
                and words are concatenated. If False, rows are concatenated
                as complete verses.

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

    def get_verses_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all verses from a specific surah.

        Uses the active translation database. For WBW databases, returns
        concatenated word translations per verse. For standard databases,
        returns verse text.

        Returns:
            A list of strings, where each string is the text of a verse.
        """
        config = self._get_active_config()

        # Handle WBW database differently - group by ayah and concatenate words
        if isinstance(config, WbwDatabaseConfig):
            query = f"""
                SELECT {config.ayah_col}, {config.text_col}
                FROM {config.tablename}
                WHERE {config.surah_col} = ?
                ORDER BY {config.ayah_col}, {config.word_id_col}
            """
            rows = self._fetch(query, (surah_number,))
            return self._aggregate_verses(rows, config, order_by_word=True)
        else:
            # Standard verse-by-verse database
            query = f"""
                SELECT {config.ayah_col}, {config.text_col}
                FROM {config.tablename}
                WHERE {config.surah_col} = ?
                ORDER BY {config.ayah_col}
            """
            rows = self._fetch(query, (surah_number,))
            return self._aggregate_verses(rows, config)

    def get_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> str:
        """Fetches a specific verse text from the active database.

        For WBW databases, returns concatenated word translations.
        For standard databases, returns the verse text.

        Returns:
            The verse text as a string.
        """
        config = self._get_active_config()

        if isinstance(config, WbwDatabaseConfig):
            query = f"""
                SELECT {config.text_col}
                FROM {config.tablename}
                WHERE {config.surah_col} = ? AND {config.ayah_col} = ?
                ORDER BY {config.word_id_col}
            """
            rows = self._fetch(query, (surah_number, ayah_number))
            return " ".join(row[config.text_col] for row in rows)
        else:
            query = f"""
                SELECT {config.text_col}
                FROM {config.tablename}
                WHERE {config.surah_col} = ? AND {config.ayah_col} = ?
            """
            rows = self._fetch(query, (surah_number, ayah_number))
            return " ".join(row[config.text_col] for row in rows)

    def get_wbw_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific surah.

        Always uses the "wbw" connection regardless of active translation.

        Returns:
            List of word translations in order.
        """
        # Always use the WBW connection
        if self.DEFAULT_WBW_NAME not in self._configs:
            raise RuntimeError("WBW database not initialized.")
        config = self._configs[self.DEFAULT_WBW_NAME]
        cursor = self._cursors[self.DEFAULT_WBW_NAME]

        query = f"""
            SELECT {config.text_col}
            FROM {config.tablename}
            WHERE {config.surah_col} = ?
            ORDER BY {config.ayah_col}, {config.word_id_col}
        """
        try:
            cursor.execute(query, (surah_number,))
            rows = cursor.fetchall()
            return [row[config.text_col] for row in rows]
        except sqlite3.Error as e:
            logger.error("Failed to fetch WBW from surah: %s", e)
            return []

    def get_wbw_from_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific verse.

        Always uses the "wbw" connection regardless of active translation.

        Returns:
            List of word translations in order.
        """
        # Always use the WBW connection
        if self.DEFAULT_WBW_NAME not in self._configs:
            raise RuntimeError("WBW database not initialized.")
        config = self._configs[self.DEFAULT_WBW_NAME]
        cursor = self._cursors[self.DEFAULT_WBW_NAME]

        query = f"""
            SELECT {config.text_col}
            FROM {config.tablename}
            WHERE {config.surah_col} = ? AND {config.ayah_col} = ?
            ORDER BY {config.word_id_col}
        """
        try:
            cursor.execute(query, (surah_number, ayah_number))
            rows = cursor.fetchall()
            return [row[config.text_col] for row in rows]
        except sqlite3.Error as e:
            logger.error("Failed to fetch WBW from verse: %s", e)
            return []

    def get_wbw_from_word(self, surah_number: SurahNumber, ayah_number: AyahNumber, word_index: WordIndex) -> Optional[str]:
        """Fetches the translation for a specific word in a specific verse.

        Always uses the "wbw" connection regardless of active translation.

        Args:
            surah_number: The surah number.
            ayah_number: The ayah (verse) number.
            word_index: The 1-indexed word position within the verse.

        Returns:
            The translation string or None if not found.
        """
        # Always use the WBW connection
        if self.DEFAULT_WBW_NAME not in self._configs:
            raise RuntimeError("WBW database not initialized.")
        config = self._configs[self.DEFAULT_WBW_NAME]
        cursor = self._cursors[self.DEFAULT_WBW_NAME]

        query = f"""
            SELECT {config.text_col}
            FROM {config.tablename}
            WHERE {config.surah_col} = ? AND {config.ayah_col} = ? AND {config.word_id_col} = ?
        """
        try:
            cursor.execute(query, (surah_number, ayah_number, word_index))
            result = cursor.fetchone()
            return result[config.text_col] if result else None
        except sqlite3.Error as e:
            logger.error("Failed to fetch word translation: %s", e)
            return None

    def get_translation_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all verse translations for a specific surah.

        Returns:
            List of verse translations (one per verse).
        """
        config = self._get_active_config()

        query = f"""
            SELECT {config.text_col}
            FROM {config.tablename}
            WHERE {config.surah_col} = ?
            ORDER BY {config.ayah_col}
        """
        rows = self._fetch(query, (surah_number,))

        # For WBW, we need to group by ayah
        if isinstance(config, WbwDatabaseConfig):
            # Re-use get_verses_from_surah logic
            return self.get_verses_from_surah(surah_number)

        return [row[config.text_col] for row in rows]

    def get_translation_from_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> Optional[str]:
        """Fetches the translation for a specific verse.

        Returns:
            The verse translation string or None if not found.
        """
        config = self._get_active_config()

        query = f"""
            SELECT {config.text_col}
            FROM {config.tablename}
            WHERE {config.surah_col} = ? AND {config.ayah_col} = ?
        """
        rows = self._fetch(query, (surah_number, ayah_number))
        return rows[0][config.text_col] if rows else None

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
        self._active_translation = None
        self._initialized = False

        logger.info("DatabaseManager closed. All connections closed.")
