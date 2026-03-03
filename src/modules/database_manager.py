"""Singleton manager for Quranic and translation databases."""

import logging
import sqlite3
import threading
from typing import Optional, Any, Self

# Type Aliases
SurahNumber = int
AyahNumber = int
WordIndex = int

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton manager for Quranic and translation databases."""

    _instance: Optional[Self] = None
    _lock = threading.Lock()

    def __new__(cls, quran_path: str = "./assets/quran.db", wbw_path: str = "./assets/wbw_en.db", translation_path: str = "./assets/en_sahih.db") -> Self:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, quran_path: str = "./assets/quran.db", wbw_path: str = "./assets/wbw_en.db", translation_path: str = "./assets/en_sahih.db"):
        """Initializes database connections. Re-initializes if previously closed.

        Args:
            quran_path: Path to the Quran text database.
            wbw_path: Path to the word-by-word translation database.
        """
        if getattr(self, "_initialized", False):
            return

        try:
            self.conn_quran = sqlite3.connect(quran_path, check_same_thread=False)
            self.conn_quran.row_factory = sqlite3.Row
            self.cursor_quran = self.conn_quran.cursor()

            self.conn_wbw = sqlite3.connect(wbw_path, check_same_thread=False)
            self.conn_wbw.row_factory = sqlite3.Row
            self.cursor_wbw = self.conn_wbw.cursor()

            self.conn_translation = sqlite3.connect(translation_path, check_same_thread=False)
            self.conn_translation.row_factory = sqlite3.Row
            self.cursor_translation = self.conn_translation.cursor()

            self._initialized = True
            logger.info("DatabaseManager initialized with %s, %s, and %s", quran_path, wbw_path, translation_path)
        except sqlite3.Error as e:
            logger.error("Failed to connect to databases: %s", e)
            raise

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _validate_state(self):
        """Ensures the connections are open before performing operations."""
        if not getattr(self, "_initialized", False) or self.conn_quran is None:
            raise RuntimeError("DatabaseManager is closed or uninitialized.")

    def _fetch_quran(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        self._validate_state()
        try:
            self.cursor_quran.execute(query, params)
            return self.cursor_quran.fetchall()
        except sqlite3.Error as e:
            logger.error("Quran DB query failed: %s | Query: %s", e, query)
            return []

    def _fetch_wbw(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        self._validate_state()
        try:
            self.cursor_wbw.execute(query, params)
            return self.cursor_wbw.fetchall()
        except sqlite3.Error as e:
            logger.error("WBW DB query failed: %s | Query: %s", e, query)
            return []

    def _fetch_translation(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        self._validate_state()
        try:
            self.cursor_translation.execute(query, params)
            return self.cursor_translation.fetchall()
        except sqlite3.Error as e:
            logger.error("Translation DB query failed: %s | Query: %s", e, query)
            return []

    def get_verses_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all verses from a specific surah.

        Returns:
            A list of strings, where each string is the text of a verse.
        """
        rows = self._fetch_quran("SELECT ayah, text FROM verses WHERE sura = ? ORDER BY ayah", (surah_number,))
        verses_dict = {}
        for row in rows:
            verses_dict.setdefault(row["ayah"], []).append(row["text"])

        return [" ".join(verses_dict[ayah_num]) for ayah_num in sorted(verses_dict)]

    def get_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> str:
        """Fetches a specific verse text."""
        rows = self._fetch_quran("SELECT text FROM verses WHERE sura = ? AND ayah = ?", (surah_number, ayah_number))
        return " ".join([row["text"] for row in rows])

    def get_wbw_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific surah."""
        rows = self._fetch_wbw("SELECT translation FROM wbw WHERE surah = ? ORDER BY ayah, word", (surah_number,))
        return [row["translation"] for row in rows]

    def get_wbw_from_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific verse."""
        rows = self._fetch_wbw("SELECT translation FROM wbw WHERE surah = ? AND ayah = ? ORDER BY word", (surah_number, ayah_number))
        return [row["translation"] for row in rows]

    def get_wbw_from_word(self, surah_number: SurahNumber, ayah_number: AyahNumber, word_index: WordIndex) -> Optional[str]:
        """Fetches the translation for a specific word in a specific verse (1-indexed).

        Returns:
            The translation string or None if not found.
        """
        self._validate_state()
        try:
            self.cursor_wbw.execute("SELECT translation FROM wbw WHERE surah = ? AND ayah = ? AND word = ?", (surah_number, ayah_number, word_index))
            result = self.cursor_wbw.fetchone()
            return result["translation"] if result else None
        except sqlite3.Error as e:
            logger.error("Failed to fetch translation: %s", e)
            return None

    def get_translation_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all verse translations for a specific surah."""
        rows = self._fetch_translation("SELECT text FROM verses WHERE sura = ? ORDER BY ayah", (surah_number,))
        return [row["text"] for row in rows]

    def get_translation_from_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> Optional[str]:
        """Fetches the translation for a specific verse."""
        rows = self._fetch_translation("SELECT text FROM verses WHERE sura = ? AND ayah = ?", (surah_number, ayah_number))
        return rows[0]["text"] if rows else None

    def close(self):
        """Closes all database connections and invalidates the instance state."""
        if not getattr(self, "_initialized", False):
            return

        self.conn_quran.close() if self.conn_quran else None
        self.conn_wbw.close() if self.conn_wbw else None
        self.conn_translation.close() if self.conn_translation else None

        self.conn_quran = None
        self.cursor_quran = None
        self.conn_wbw = None
        self.cursor_wbw = None
        self.conn_translation = None
        self.cursor_translation = None
        self._initialized = False
        logger.info("DatabaseManager connections closed.")
