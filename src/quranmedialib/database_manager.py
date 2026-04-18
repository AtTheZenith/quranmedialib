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

import functools
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

# SQLite performance settings
_SQLITE_PRAGMAS = [
    "PRAGMA journal_mode=DELETE",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA cache_size=10000",
    "PRAGMA temp_store=MEMORY",
    "PRAGMA locking_mode=NORMAL",
]

# Maximum glow radius to prevent resource exhaustion
MAX_GLOW_RADIUS = 200

# Surah and ayah range constants for runtime validation
MIN_SURAH = 1
MAX_SURAH = 114
MIN_AYAH = 1
MAX_AYAH = 286

# Trusted packaged database table/column names — hardcoded to prevent SQL injection
_PACKAGED_DB_SCHEMAS = {
    "quran.db": {"tablename": "ayat", "surah_col": "sura", "ayah_col": "ayah", "text_col": "text"},
    "english_sahih.db": {"tablename": "english_sahih", "surah_col": "sura", "ayah_col": "aya", "text_col": "text"},
    "english_wbw.db": {
        "tablename": "wbw",
        "surah_col": "surah",
        "ayah_col": "ayah",
        "text_col": "translation",
        "word_id_col": "word",
    },
}


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


def _validate_surah(surah: int) -> int:
    """Validate surah number is within valid range."""
    if not MIN_SURAH <= surah <= MAX_SURAH:
        raise ValueError(f"Surah number must be between {MIN_SURAH} and {MAX_SURAH}, got {surah}")
    return surah


def _validate_ayah(ayah: int) -> int:
    """Validate ayah number is within valid range."""
    if not MIN_AYAH <= ayah <= MAX_AYAH:
        raise ValueError(f"Ayah number must be between {MIN_AYAH} and {MAX_AYAH}, got {ayah}")
    return ayah


def _truncate_for_log(value: Any, max_len: int = 100) -> str:
    """Truncate a value for safe logging."""
    s = str(value)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def _is_packaged_db(config: DatabaseConfig | WbwDatabaseConfig) -> bool:
    """Check if a config references a packaged database by filename."""
    return config.filepath.name in _PACKAGED_DB_SCHEMAS


def _get_packaged_schema(config: DatabaseConfig | WbwDatabaseConfig) -> dict[str, str]:
    """Return hardcoded schema for a packaged database."""
    schema = _PACKAGED_DB_SCHEMAS.get(config.filepath.name)
    if schema is None:
        raise ValueError(f"No hardcoded schema for packaged database: {config.filepath.name}")
    return schema


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
    _init_lock = threading.Lock()

    # Default connection names
    DEFAULT_QURAN_NAME = "quran"
    DEFAULT_WBW_NAME = "wbw"
    DEFAULT_TRANSLATION_NAME = "translation"

    def __new__(cls) -> Self:
        if cls._instance is not None:
            return cls._instance
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
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
        # Thread-safe check-and-init using dedicated init lock
        with type(self)._init_lock:
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
            self._connections: dict[str, sqlite3.Connection] = {}
            self._configs: dict[str, DatabaseConfig | WbwDatabaseConfig] = {}
            self._active_wbw: Optional[str] = None
            self._active_translation: Optional[str] = None

            # Performance caches
            self._schema_cache: dict[str, dict[str, str]] = {}
            self._query_cache: dict[str, str] = {}

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

    def _get_connection(self, name: str) -> sqlite3.Connection:
        """Get the connection for a named database."""
        if name not in self._connections:
            raise KeyError(f"Unknown database: {name}")
        return self._connections[name]

    def _register_connection(self, name: str, config: DatabaseConfig | WbwDatabaseConfig) -> None:
        """Registers a connection into the internal registry.

        Args:
            name: Unique name for the connection.
            config: Configuration object.
        """
        conn = sqlite3.connect(str(config.filepath), check_same_thread=False)

        # Apply optimization PRAGMAs
        for pragma in _SQLITE_PRAGMAS:
            conn.execute(pragma)

        conn.row_factory = sqlite3.Row

        self._connections[name] = conn
        self._configs[name] = config
        self._registry[name] = {
            "config": config,
            "connection": conn,
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

    def _fetch(
        self,
        name: str,
        query: str,
        params: tuple[Any, ...] = (),
        row_factory: Any = sqlite3.Row,
    ) -> list[Any]:
        """Execute a query on a named database and return all rows.

        Creates a fresh cursor per call to avoid thread-safety issues
        with shared cursor objects.

        Args:
            name: Registered connection name.
            query: SQL query string.
            params: Parameters to bind to the query.
            row_factory: Row factory to use for this fetch. Defaults to sqlite3.Row.
                Use None for fastest raw tuple access.

        Returns:
            List of result rows. Returns empty list on sqlite3 errors after logging
            at WARNING level with caller context for debugging.
        """
        conn = self._get_connection(name)
        old_factory = conn.row_factory
        conn.row_factory = row_factory
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            params_repr = _truncate_for_log(params)
            query_repr = _truncate_for_log(query, 200)
            logger.warning(
                "Database query failed on '%s': %s | Query: %s | Params: %s",
                name,
                e,
                query_repr,
                params_repr,
                exc_info=True,
            )
            return []
        finally:
            cursor.close()
            conn.row_factory = old_factory

    def _aggregate_verses(
        self,
        rows: list[sqlite3.Row],
        config: DatabaseConfig | WbwDatabaseConfig,
    ) -> list[str]:
        """Helper to aggregate verses by ayah number.

        Rows are already ORDER BY ayah_col from SQL, so this processes
        them in a single streaming pass without dict allocation or sorting.

        Args:
            rows: Query results containing ayah and text columns.
            config: Database configuration for column name mapping.

        Returns:
            A list of verse strings, ordered by ayah number.
        """
        result: list[str] = []
        current_ayah = None
        current_texts: list[str] = []

        for row in rows:
            ayah = row[config.ayah_col]
            if ayah != current_ayah:
                if current_texts:
                    result.append(" ".join(current_texts))
                current_ayah = ayah
                current_texts = []
            current_texts.append(row[config.text_col])

        if current_texts:
            result.append(" ".join(current_texts))

        return result

    def _resolve_schema(self, config: DatabaseConfig | WbwDatabaseConfig) -> tuple[str, dict[str, str]]:
        """Resolve database schema, using hardcoded values for packaged DBs.

        Caches results to avoid redundant string validation and dictionary lookups.

        Returns:
            Tuple of (table_name, schema_dict).
        """
        cache_key = config.filepath.name
        if cache_key in self._schema_cache:
            return cache_key, self._schema_cache[cache_key]

        if _is_packaged_db(config):
            schema = _get_packaged_schema(config)
            self._schema_cache[cache_key] = schema
            return cache_key, schema

        schema = {
            "tablename": _validate_sql_identifier(config.tablename, "table name"),
            "surah_col": _validate_sql_identifier(config.surah_col, "column name"),
            "ayah_col": _validate_sql_identifier(config.ayah_col, "column name"),
            "text_col": _validate_sql_identifier(config.text_col, "column name"),
            "word_id_col": _validate_sql_identifier(config.word_id_col, "column name")
            if isinstance(config, WbwDatabaseConfig)
            else "word",
        }
        self._schema_cache[cache_key] = schema
        return "user", schema

    # === Quran Database Methods (always use "quran" database) ===

    @functools.lru_cache(maxsize=114)
    def get_verses_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all Arabic verses from a specific surah.

        Always uses the "quran" database. Caches results for all 114 surahs.

        Returns:
            A list of Arabic verse strings, ordered by ayah number.
        """
        surah_number = _validate_surah(surah_number)
        config = self._get_config(self.DEFAULT_QURAN_NAME)
        _, schema = self._resolve_schema(config)

        # Build query once and cache it
        query_key = f"quran_surah_verses_{config.filepath.name}"
        if query_key not in self._query_cache:
            # Use GROUP_CONCAT with GROUP BY for native SQL aggregation
            self._query_cache[query_key] = f"""
                SELECT GROUP_CONCAT({schema["text_col"]}, ' ')
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ?
                GROUP BY {schema["ayah_col"]}
                ORDER BY {schema["ayah_col"]}
            """

        # Use None row_factory for fastest raw tuple access
        rows = self._fetch(self.DEFAULT_QURAN_NAME, self._query_cache[query_key], (surah_number,), row_factory=None)
        return [row[0] for row in rows]

    @functools.lru_cache(maxsize=1024)
    def get_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> str:
        """Fetches a specific Arabic verse text.

        Always uses the "quran" database. Caches frequently accessed verses.

        Returns:
            The Arabic verse text as a string.
        """
        surah_number = _validate_surah(surah_number)
        ayah_number = _validate_ayah(ayah_number)
        config = self._get_config(self.DEFAULT_QURAN_NAME)
        _, schema = self._resolve_schema(config)

        # Use native GROUP_CONCAT for 2x faster fetching
        query_key = f"quran_verse_{config.filepath.name}"
        if query_key not in self._query_cache:
            self._query_cache[query_key] = f"""
                SELECT GROUP_CONCAT({schema["text_col"]}, ' ')
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ? AND {schema["ayah_col"]} = ?
            """

        rows = self._fetch(
            self.DEFAULT_QURAN_NAME, self._query_cache[query_key], (surah_number, ayah_number), row_factory=None
        )
        return rows[0][0] if rows and rows[0][0] else ""

    # === WBW Database Methods (use active WBW database) ===

    def get_wbw_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific surah.

        Uses the active WBW database (set via set_active_wbw, default "wbw").

        Returns:
            List of word translations in order.
        """
        surah_number = _validate_surah(surah_number)
        name = self._active_wbw or self.DEFAULT_WBW_NAME
        config = self._get_config(name)
        _, schema = self._resolve_schema(config)

        query = f"""
            SELECT {schema["text_col"]}
            FROM {schema["tablename"]}
            WHERE {schema["surah_col"]} = ?
            ORDER BY {schema["ayah_col"]}, {schema["word_id_col"]}
        """
        rows = self._fetch(name, query, (surah_number,))
        return [row[config.text_col] for row in rows]

    def get_wbw_from_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific verse.

        Uses the active WBW database (set via set_active_wbw, default "wbw").

        Returns:
            List of word translations in order.
        """
        surah_number = _validate_surah(surah_number)
        ayah_number = _validate_ayah(ayah_number)
        name = self._active_wbw or self.DEFAULT_WBW_NAME
        config = self._get_config(name)
        _, schema = self._resolve_schema(config)

        query = f"""
            SELECT {schema["text_col"]}
            FROM {schema["tablename"]}
            WHERE {schema["surah_col"]} = ? AND {schema["ayah_col"]} = ?
            ORDER BY {schema["word_id_col"]}
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
        surah_number = _validate_surah(surah_number)
        ayah_number = _validate_ayah(ayah_number)
        name = self._active_wbw or self.DEFAULT_WBW_NAME
        config = self._get_config(name)
        _, schema = self._resolve_schema(config)

        query = f"""
            SELECT {schema["text_col"]}
            FROM {schema["tablename"]}
            WHERE {schema["surah_col"]} = ? AND {schema["ayah_col"]} = ? AND {schema["word_id_col"]} = ?
        """
        rows = self._fetch(name, query, (surah_number, ayah_number, word_index))
        return rows[0][config.text_col] if rows else None

    @functools.lru_cache(maxsize=114)
    def get_wbw_grouped_by_verse(
        self,
        surah_number: SurahNumber,
    ) -> dict[int, list[str]]:
        """Fetches all word-by-word translations for a surah, grouped by ayah.

        Uses the active WBW database (set via set_active_wbw, default "wbw").
        Caches full surah WBW results.

        Args:
            surah_number: The surah number (1-114).

        Returns:
            Dictionary mapping ayah numbers to their lists of word translations.
        """
        surah_number = _validate_surah(surah_number)
        name = self._active_wbw or self.DEFAULT_WBW_NAME
        config = self._get_config(name)
        _, schema = self._resolve_schema(config)

        query_key = f"wbw_grouped_{config.filepath.name}"
        if query_key not in self._query_cache:
            self._query_cache[query_key] = f"""
                SELECT {schema["ayah_col"]}, {schema["text_col"]}
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ?
                ORDER BY {schema["ayah_col"]}, {schema["word_id_col"]}
            """

        # Fetch as raw tuples for speed
        rows = self._fetch(name, self._query_cache[query_key], (surah_number,), row_factory=None)

        result: dict[int, list[str]] = {}
        for row in rows:
            ayah = row[0]
            if ayah not in result:
                result[ayah] = []
            result[ayah].append(row[1])

        return result

    # === Translation Database Methods (use active translation database) ===

    @functools.lru_cache(maxsize=114)
    def get_translation_from_surah(
        self,
        surah_number: SurahNumber,
        translation_name: str | None = None,
    ) -> list[str]:
        """Fetches all verse translations for a specific surah.

        Caches translation results for all surahs.

        Args:
            surah_number: The surah number.
            translation_name: Optional name of the translation database to use.

        Returns:
            List of verse translations (one per verse).
        """
        surah_number = _validate_surah(surah_number)
        name = translation_name or (self._active_translation or self.DEFAULT_TRANSLATION_NAME)
        config = self._get_config(name)
        _, schema = self._resolve_schema(config)

        query_key = f"trans_surah_{config.filepath.name}"
        if query_key not in self._query_cache:
            self._query_cache[query_key] = f"""
                SELECT {schema["text_col"]}
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ?
                ORDER BY {schema["ayah_col"]}
            """

        rows = self._fetch(name, self._query_cache[query_key], (surah_number,), row_factory=None)
        return [row[0] for row in rows]

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
        surah_number = _validate_surah(surah_number)
        ayah_number = _validate_ayah(ayah_number)
        name = translation_name or (self._active_translation or self.DEFAULT_TRANSLATION_NAME)
        config = self._get_config(name)
        _, schema = self._resolve_schema(config)

        query = f"""
            SELECT {schema["text_col"]}
            FROM {schema["tablename"]}
            WHERE {schema["surah_col"]} = ? AND {schema["ayah_col"]} = ?
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
        surah_number = _validate_surah(surah_number)
        start_ayah = _validate_ayah(start_ayah)
        end_ayah = _validate_ayah(end_ayah)
        name = translation_name or (self._active_translation or self.DEFAULT_TRANSLATION_NAME)
        config = self._get_config(name)
        _, schema = self._resolve_schema(config)

        query = f"""
            SELECT {schema["ayah_col"]}, {schema["text_col"]}
            FROM {schema["tablename"]}
            WHERE {schema["surah_col"]} = ? AND {schema["ayah_col"]} BETWEEN ? AND ?
            ORDER BY {schema["ayah_col"]}
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
                "Database may be corrupted or incomplete."
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
        self._configs.clear()
        self._registry.clear()
        self._schema_cache.clear()
        self._query_cache.clear()
        self._active_wbw = None
        self._active_translation = None
        self._initialized = False

        # Clear method caches
        self.get_verses_from_surah.cache_clear()
        self.get_verse.cache_clear()
        self.get_wbw_grouped_by_verse.cache_clear()
        self.get_translation_from_surah.cache_clear()

        # Reset singleton instance so next DatabaseManager() creates a fresh instance
        type(self)._instance = None

        logger.info("DatabaseManager closed. All connections closed.")
