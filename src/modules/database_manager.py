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

    def __new__(cls, quran_path: str = "./assets/quran.db", wbw_path: str = "./assets/wbw_en.db") -> Self:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, quran_path: str = "./assets/quran.db", wbw_path: str = "./assets/wbw_en.db"):
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

            self._initialized = True
            logger.info("DatabaseManager initialized with %s and %s", quran_path, wbw_path)
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

    def fetch_all_verses_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all verses from a specific surah.

        Returns:
            A list of strings, where each string is the text of a verse.
        """
        rows = self._fetch_quran("SELECT ayah, text FROM verses WHERE sura = ? ORDER BY ayah", (surah_number,))
        verses_dict = {}
        for row in rows:
            verses_dict.setdefault(row["ayah"], []).append(row["text"])

        return [" ".join(verses_dict[ayah_num]) for ayah_num in sorted(verses_dict)]

    def fetch_all_words_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all words from a specific surah."""
        rows = self._fetch_quran("SELECT text FROM verses WHERE sura = ? ORDER BY ayah", (surah_number,))
        return [word for row in rows for word in row["text"].split() if word]

    def fetch_all_words_from_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> list[str]:
        """Fetches all words from a specific verse."""
        rows = self._fetch_quran("SELECT text FROM verses WHERE sura = ? AND ayah = ?", (surah_number, ayah_number))
        return [word for row in rows for word in row["text"].split() if word]

    def fetch_all_translations_from_surah(self, surah_number: SurahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific surah."""
        rows = self._fetch_wbw("SELECT translation FROM wbw WHERE surah = ? ORDER BY ayah, word", (surah_number,))
        return [row["translation"] for row in rows]

    def fetch_all_translations_from_verse(self, surah_number: SurahNumber, ayah_number: AyahNumber) -> list[str]:
        """Fetches all word-by-word translations for a specific verse."""
        rows = self._fetch_wbw("SELECT translation FROM wbw WHERE surah = ? AND ayah = ? ORDER BY word", (surah_number, ayah_number))
        return [row["translation"] for row in rows]

    def fetch_translation_for_word(self, surah_number: SurahNumber, ayah_number: AyahNumber, word_index: WordIndex) -> Optional[str]:
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

    def close(self):
        """Closes all database connections and invalidates the instance state."""
        if not getattr(self, "_initialized", False):
            return

        if self.conn_quran:
            self.conn_quran.close()
        if self.conn_wbw:
            self.conn_wbw.close()

        self.conn_quran = None
        self.cursor_quran = None
        self.conn_wbw = None
        self.cursor_wbw = None
        self._initialized = False
        logger.info("DatabaseManager connections closed.")
