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
import json
import logging
import re
import sqlite3
import threading
import time
from contextlib import closing
from types import TracebackType
from typing import Any, Callable, Self
import threading as threading_mod

from quranmedialib.config import SQLITE_MMAP_SIZE
from quranmedialib.exceptions import ValidationError
from quranmedialib.types import (
    MAX_AYAH,
    MAX_SURAH,
    MIN_AYAH,
    MIN_SURAH,
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
    f"PRAGMA mmap_size={SQLITE_MMAP_SIZE}",
]

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
        ValidationError: If the identifier contains invalid characters.
    """
    if not _SQL_IDENTIFIER.match(name):
        raise ValidationError(f"Invalid SQL {context}: {name!r}. Must be alphanumeric with underscores only.")
    return name


def _validate_surah(surah: int) -> int:
    """Validate surah number is within valid range."""
    if not MIN_SURAH <= surah <= MAX_SURAH:
        raise ValidationError(f"Surah number must be between {MIN_SURAH} and {MAX_SURAH}, got {surah}")
    return surah


def _validate_ayah(ayah: int) -> int:
    """Validate ayah number is within valid range."""
    if not MIN_AYAH <= ayah <= MAX_AYAH:
        raise ValidationError(f"Ayah number must be between {MIN_AYAH} and {MAX_AYAH}, got {ayah}")
    return ayah


def _truncate_for_log(value: Any, max_len: int = 100) -> str:
    """Truncate a value for safe logging."""
    s = str(value)
    return f"{s[:max_len]}..." if len(s) > max_len else s


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

    _instance: DatabaseManager | None = None
    _lock = threading.RLock()

    # Default connection names
    DEFAULT_QURAN_NAME = "quran"
    DEFAULT_WBW_NAME = "wbw"
    DEFAULT_TRANSLATION_NAME = "translation"

    def __new__(cls) -> DatabaseManager:
        """Standard thread-safe singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initializes database connections and registers packaged databases.
        
        Automatically registers packaged databases on first initialization.
        """
        if getattr(self, "_initialized", False):
            return

        with self._lock:
            if getattr(self, "_initialized", False):
                return

            self._registry: dict[str, dict[str, DatabaseConfig | WbwDatabaseConfig | sqlite3.Connection]] = {}
            self._local = threading_mod.local()
            self._configs: dict[str, DatabaseConfig | WbwDatabaseConfig] = {}
            self._active_wbw: str | None = None
            self._active_translation: str | None = None

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
        """Get the connection for a named database, creating it for the current thread if needed.
        
        Implements thread-local connection pooling to ensure thread safety and performance.
        """
        config = self._get_config(name)
        
        # Thread-local storage for connections
        if not hasattr(self._local, "connections"):
            self._local.connections = {}
            
        if name not in self._local.connections:
            conn = sqlite3.connect(str(config.filepath), check_same_thread=False)
            for pragma in _SQLITE_PRAGMAS:
                conn.execute(pragma)
            conn.row_factory = None
            self._local.connections[name] = conn
            
        return self._local.connections[name]

    def _register_connection(self, name: str, config: DatabaseConfig | WbwDatabaseConfig) -> None:
        """Registers a connection into the internal registry.
        
        Args:
            name: Unique name for the connection.
            config: Configuration object.
        """
        with self._lock:
            self._configs[name] = config
            self._registry[name] = {
                "config": config,
            }


    def _add_connection_internal(self, name: str, config: DatabaseConfig | WbwDatabaseConfig) -> None:
        """Internal method to add a connection without validation."""
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

        Args:
            name: Name of a registered translation database.

        Raises:
            KeyError: If the name is not a registered connection.
        """
        self._validate_state()
        with self._lock:
            if name not in self._registry:
                raise KeyError(f"Unknown translation: {name}. Available: {list(self._registry.keys())}")
            self._active_translation = name
            logger.debug("Active translation set to: %s", name)

    def get_active_translation_name(self) -> str | None:
        """Get the name of the currently active translation."""
        self._validate_state()
        return self._active_translation

    def set_active_wbw(self, name: str) -> None:
        """Set the active WBW database for subsequent WBW fetch operations.

        Args:
            name: Name of a registered WBW database.

        Raises:
            KeyError: If the name is not a registered connection.
        """
        self._validate_state()
        with self._lock:
            if name not in self._registry:
                raise KeyError(f"Unknown WBW database: {name}. Available: {list(self._registry.keys())}")
            self._active_wbw = name
            logger.debug("Active WBW set to: %s", name)

    def get_active_wbw_name(self) -> str | None:
        """Get the name of the currently active WBW database."""
        self._validate_state()
        return self._active_wbw

    def _fetch(
        self,
        name: str,
        query: str,
        params: tuple[str | int | float | bytes | None, ...] = (),
        row_factory: Callable[[sqlite3.Cursor], Any] | None = None,
    ) -> list[sqlite3.Row | tuple[Any, ...]]:
        """Execute a query on a named database and return all rows.

        Args:
            name: Registered connection name.
            query: SQL query string.
            params: Parameters to bind to the query.
            row_factory: Row factory to use for this fetch (rarely used).

        Returns:
            List of result rows.
        """
        conn = self._get_connection(name)

        # The lock is only needed if we are actually changing the connection-wide row_factory.
        # Since we now default to None, we only lock if a specific row_factory is requested.
        if row_factory is not None:
            with self._lock:
                old_factory = conn.row_factory
                conn.row_factory = row_factory
                try:
                    with closing(conn.cursor()) as cursor:
                        cursor.execute(query, params)
                        return cursor.fetchall()
                except sqlite3.Error as e:
                    logger.error(
                        "Database query failed on '%s': %s | Query: %s | Params: %s",
                        name,
                        e,
                        _truncate_for_log(query, 200),
                        _truncate_for_log(params),
                        exc_info=True,
                    )
                    raise
                finally:
                    conn.row_factory = old_factory

        # Hot path: row_factory is None, no locking needed for concurrent reads.
        try:
            with closing(conn.cursor()) as cursor:
                return self._execute_and_profile(cursor, query, params, name)
        except sqlite3.Error as e:
            logger.error(
                "Database query failed on '%s': %s | Query: %s | Params: %s",
                name,
                e,
                _truncate_for_log(query, 200),
                _truncate_for_log(params),
                exc_info=True,
            )
            raise

    # TODO Rename this here and in `_fetch`
    def _execute_and_profile(
        self,
        cursor: sqlite3.Cursor,
        query: str,
        params: tuple[Any, ...],
        name: str,
    ) -> list[sqlite3.Row | tuple[Any, ...]]:
        start_time = time.perf_counter()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        end_time = time.perf_counter()

        duration = end_time - start_time
        logger.debug("SQL EXECUTE: %.4fs | DB: %s | Query: %s", duration, name, _truncate_for_log(query))
        return rows

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
            "word_id_col": _validate_sql_identifier(config.word_id_col, "column name") if isinstance(config, WbwDatabaseConfig) else "word",
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
        self._validate_state()
        surah_number = _validate_surah(surah_number)
        config = self._get_config(self.DEFAULT_QURAN_NAME)
        _, schema = self._resolve_schema(config)

        # Build query once and cache it
        query_key = f"quran_surah_verses_json_{config.filepath.name}"
        if query_key not in self._query_cache:
            # Use JSON_GROUP_ARRAY for native SQL aggregation (faster + no truncation)
            self._query_cache[query_key] = f"""
                SELECT json_group_array({schema["text_col"]})
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ?
                GROUP BY {schema["ayah_col"]}
                ORDER BY {schema["ayah_col"]}
            """

        # Use None row_factory for fastest raw tuple access
        rows = self._fetch(self.DEFAULT_QURAN_NAME, self._query_cache[query_key], (surah_number,), row_factory=None)
        return [" ".join(json.loads(row[0])) for row in rows]

    def get_verses_from_range(self, surah_number: SurahNumber, start_ayah: AyahNumber, end_ayah: AyahNumber) -> list[str]:
        """Fetches Arabic verses for a specific range within a surah.

        Always uses the "quran" database.

        Args:
            surah_number: Surah number (1-114).
            start_ayah: Starting ayah number (inclusive).
            end_ayah: Ending ayah number (inclusive).

        Returns:
            A list of Arabic verse strings, ordered by ayah number.
        """
        self._validate_state()
        surah_number = _validate_surah(surah_number)
        start_ayah = _validate_ayah(start_ayah)
        end_ayah = _validate_ayah(end_ayah)
        config = self._get_config(self.DEFAULT_QURAN_NAME)
        _, schema = self._resolve_schema(config)

        # Build query for range
        query_key = f"quran_range_verses_json_{config.filepath.name}"
        if query_key not in self._query_cache:
            self._query_cache[query_key] = f"""
                SELECT json_group_array({schema["text_col"]})
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ? AND {schema["ayah_col"]} BETWEEN ? AND ?
                GROUP BY {schema["ayah_col"]}
                ORDER BY {schema["ayah_col"]}
            """

        rows = self._fetch(
            self.DEFAULT_QURAN_NAME,
            self._query_cache[query_key],
            (surah_number, start_ayah, end_ayah),
            row_factory=None,
        )
        return [" ".join(json.loads(row[0])) for row in rows]

    @functools.lru_cache(maxsize=1024)
    def get_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> str:
        """Fetches a specific Arabic verse text.

        Always uses the "quran" database. Caches frequently accessed verses.

        Returns:
            The Arabic verse text as a string.
        """
        self._validate_state()
        surah_number = _validate_surah(surah_number)
        ayah_number = _validate_ayah(ayah_number)
        config = self._get_config(self.DEFAULT_QURAN_NAME)
        _, schema = self._resolve_schema(config)

        # Use native JSON_GROUP_ARRAY for 2x faster fetching (safer than GROUP_CONCAT)
        query_key = f"quran_verse_json_{config.filepath.name}"
        if query_key not in self._query_cache:
            self._query_cache[query_key] = f"""
                SELECT json_group_array({schema["text_col"]})
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ? AND {schema["ayah_col"]} = ?
            """

        rows = self._fetch(self.DEFAULT_QURAN_NAME, self._query_cache[query_key], (surah_number, ayah_number), row_factory=None)
        return " ".join(json.loads(rows[0][0])) if rows and rows[0][0] else ""

    # === WBW Database Methods (use active WBW database) ===

    def get_wbw_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific surah.

        Returns:
            List of word translations in order.
        """
        self._validate_state()
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
        rows = self._fetch(name, query, (surah_number,), row_factory=None)
        return [row[0] for row in rows]

    def get_wbw_from_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific verse.

        Returns:
            List of word translations in order.
        """
        self._validate_state()
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
        rows = self._fetch(name, query, (surah_number, ayah_number), row_factory=None)
        return [row[0] for row in rows]

    def get_wbw_from_word(
        self,
        surah_number: SurahNumber,
        ayah_number: AyahNumber,
        word_index: WordIndex,
    ) -> str | None:
        """Fetches the translation for a specific word in a specific verse.

        Args:
            surah_number: The surah number.
            ayah_number: The ayah (verse) number.
            word_index: The 1-indexed word position within the verse.

        Returns:
            The translation string or None if not found.
        """
        self._validate_state()
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
        rows = self._fetch(name, query, (surah_number, ayah_number, word_index), row_factory=None)
        return rows[0][0] if rows else None

    @functools.lru_cache(maxsize=114)
    def get_wbw_grouped_by_verse(
        self,
        surah_number: SurahNumber,
    ) -> dict[int, list[str]]:
        """Fetches all word-by-word translations for a surah, grouped by ayah.

        Caches full surah WBW results.

        Args:
            surah_number: The surah number (1-114).

        Returns:
            Dictionary mapping ayah numbers to their lists of word translations.
        """
        self._validate_state()
        surah_number = _validate_surah(surah_number)
        name = self._active_wbw or self.DEFAULT_WBW_NAME
        config = self._get_config(name)
        _, schema = self._resolve_schema(config)

        # OPTIM: Try native SQL grouping (JSON_GROUP_ARRAY)
        query_key = f"wbw_grouped_json_{config.filepath.name}"
        if query_key not in self._query_cache:
            self._query_cache[query_key] = f"""
                SELECT {schema["ayah_col"]}, json_group_array({schema["text_col"]})
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ?
                GROUP BY {schema["ayah_col"]}
                ORDER BY {schema["ayah_col"]}
            """

        try:
            rows = self._fetch(name, self._query_cache[query_key], (surah_number,), row_factory=None)
            return {row[0]: json.loads(row[1]) for row in rows} if rows else {}
        except (sqlite3.OperationalError, json.JSONDecodeError):
            logger.debug("json_group_array not supported or failed, falling back to manual grouping.")
            query = f"""
                SELECT {schema["ayah_col"]}, {schema["text_col"]}
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ?
                ORDER BY {schema["ayah_col"]}, {schema["word_id_col"]}
            """
            rows = self._fetch(name, query, (surah_number,), row_factory=None)
            result: dict[int, list[str]] = {}
            for row in rows:
                ayah = row[0]
                if ayah not in result:
                    result[ayah] = []
                result[ayah].append(row[1])
            return result

    def get_wbw_grouped_by_verse_range(
        self,
        surah_number: SurahNumber,
        start_ayah: AyahNumber,
        end_ayah: AyahNumber,
    ) -> dict[int, list[str]]:
        """Fetches word-by-word translations for a range of verses, grouped by ayah.

        Args:
            surah_number: The surah number (1-114).
            start_ayah: Starting ayah number (inclusive).
            end_ayah: Ending ayah number (inclusive).

        Returns:
            Dictionary mapping ayah numbers to their lists of word translations.
        """
        self._validate_state()
        surah_number = _validate_surah(surah_number)
        start_ayah = _validate_ayah(start_ayah)
        end_ayah = _validate_ayah(end_ayah)
        name = self._active_wbw or self.DEFAULT_WBW_NAME
        config = self._get_config(name)
        _, schema = self._resolve_schema(config)

        # OPTIM: Try native SQL grouping (JSON_GROUP_ARRAY) for 10x faster aggregation
        query_key = f"wbw_range_grouped_json_{config.filepath.name}"
        if query_key not in self._query_cache:
            self._query_cache[query_key] = f"""
                SELECT {schema["ayah_col"]}, json_group_array({schema["text_col"]})
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ? AND {schema["ayah_col"]} BETWEEN ? AND ?
                GROUP BY {schema["ayah_col"]}
                ORDER BY {schema["ayah_col"]}
            """

        try:
            rows = self._fetch(name, self._query_cache[query_key], (surah_number, start_ayah, end_ayah), row_factory=None)
            return {row[0]: json.loads(row[1]) for row in rows} if rows else {}
        except (sqlite3.OperationalError, json.JSONDecodeError):
            # Fallback to slower row-by-row fetching for older SQLite versions
            logger.debug("json_group_array not supported or failed, falling back to manual grouping.")
            query = f"""
                SELECT {schema["ayah_col"]}, {schema["text_col"]}
                FROM {schema["tablename"]}
                WHERE {schema["surah_col"]} = ? AND {schema["ayah_col"]} BETWEEN ? AND ?
                ORDER BY {schema["ayah_col"]}, {schema["word_id_col"]}
            """
            rows = self._fetch(name, query, (surah_number, start_ayah, end_ayah), row_factory=None)
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
        self._validate_state()
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

        Returns:
            The verse translation string or None if not found.
        """
        self._validate_state()
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
        rows = self._fetch(name, query, (surah_number, ayah_number), row_factory=None)
        return rows[0][0] if rows else None

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

        Returns:
            List of verse translations in order by ayah number.

        Raises:
            ValueError: If any ayah in the requested range is missing from the database.
        """
        self._validate_state()
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
        rows = self._fetch(name, query, (surah_number, start_ayah, end_ayah), row_factory=None)

        verses_dict: dict[int, str] = {}
        for row in rows:
            ayah = row[0]
            verses_dict[ayah] = row[1]

        if missing_ayah := [ayah for ayah in range(start_ayah, end_ayah + 1) if ayah not in verses_dict]:
            raise ValidationError(f"Missing translations for ayah(s) {missing_ayah} in surah {surah_number}. Database may be corrupted or incomplete.")

        return [verses_dict[ayah] for ayah in range(start_ayah, end_ayah + 1)]

    def list_connections(self) -> list[str]:
        """List all registered connection names."""
        self._validate_state()
        return list(self._registry.keys())

    def close(self) -> None:
        """Closes all database connections and invalidates the instance state."""
        if not getattr(self, "_initialized", False):
            return

        with self._lock:
            # Note: We cannot easily close thread-local connections for other threads.
            # The current thread's connections are closed here.
            if hasattr(self._local, "connections"):
                for conn in self._local.connections.values():
                    if conn:
                        conn.close()
                self._local.connections.clear()

            self._configs.clear()
            self._registry.clear()
            self._schema_cache.clear()
            self._query_cache.clear()
            self._active_wbw = None
            self._active_translation = None
            self._initialized = False

            # Reset singleton instance under init lock for complete cleanup
            DatabaseManager._instance = None

    def minimize_caches(self) -> None:
        """Clears performance caches to minimize memory footprint."""
        with self._lock:
            self._schema_cache.clear()
            self._query_cache.clear()

        # Clear functools.lru_cache methods
        self.get_verses_from_surah.cache_clear()
        self.get_verse.cache_clear()
        self.get_wbw_grouped_by_verse.cache_clear()
        self.get_translation_from_surah.cache_clear()

        logger.debug("DatabaseManager caches minimized.")
