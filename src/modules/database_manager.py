# ./assets/quran.db
# table (is named 'verses') structure:
# "surah","ayah","text"

# ./assets/wbw_en.db
# table structure:
# "surah","ayah","word","translation"
# fetch by word only, it is used in parallel with fetch by word from corpus.db (to annotate words with translations)

"""Module for managing database operations for Quranic text and translations.

This module provides a singleton DatabaseManager class to handle connections
to multiple SQLite databases and perform common fetch operations for verses,
words, and translations.
"""

import sqlite3


# A Singleton
class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.conn_quran = sqlite3.connect("./assets/quran.db")
            cls._instance.cursor_quran = cls._instance.conn_quran.cursor()
            cls._instance.conn_wbw = sqlite3.connect("./assets/wbw_en.db")
            cls._instance.cursor_wbw = cls._instance.conn_wbw.cursor()
        return cls._instance

    def fetch_all_verses_from_surah(self, surah_number: int) -> list[str]:
        """Fetches all verses from a specific surah.

        Args:
            surah_number: The surah number to fetch verses from.

        Returns:
            A list of strings, where each string is the text of a verse.
        """
        self.cursor_quran.execute("SELECT ayah, text FROM verses WHERE sura = ? ORDER BY ayah", (surah_number,))
        verses_dict = {}
        for ayah, text in self.cursor_quran.fetchall():
            verses_dict.setdefault(ayah, []).append(text)
        return [" ".join(verses_dict[ayah_num]) for ayah_num in sorted(verses_dict)]

    def fetch_all_words_from_surah(self, surah_number: int) -> list[str]:
        """Fetches all words from a specific surah.

        Args:
            surah_number: The surah number to fetch words from.

        Returns:
            A list of words (strings) from the surah.
        """
        self.cursor_quran.execute("SELECT text FROM verses WHERE sura = ? ORDER BY ayah", (surah_number,))
        words = [word for row in self.cursor_quran.fetchall() for word in row[0].split(" ") if word != ""]
        return words

    def fetch_all_words_from_verse(self, surah_number: int, ayah_number: int) -> list[str]:
        """Fetches all words from a specific verse.

        Args:
            surah_number: The surah number.
            ayah_number: The ayah number.

        Returns:
            A list of words (strings) from the verse.
        """
        self.cursor_quran.execute("SELECT text FROM verses WHERE sura = ? AND ayah = ?", (surah_number, ayah_number))
        words = [word for row in self.cursor_quran.fetchall() for word in row[0].split(" ") if word != ""]
        return words

    def fetch_all_tr_words_from_surah(self, surah_number: int) -> list[str]:
        """Fetches all word-by-word translations for a specific surah.

        Args:
            surah_number: The surah number.

        Returns:
            A list of translation strings.
        """
        self.cursor_wbw.execute("SELECT translation FROM wbw WHERE surah = ? ORDER BY ayah, word", (surah_number,))
        return [row[0] for row in self.cursor_wbw.fetchall()]

    def fetch_all_tr_words_from_verse(self, surah_number: int, ayah_number: int) -> list[str]:
        """Fetches all word-by-word translations for a specific verse.

        Args:
            surah_number: The surah number.
            ayah_number: The ayah number.

        Returns:
            A list of translation strings.
        """
        self.cursor_wbw.execute("SELECT translation FROM wbw WHERE surah = ? AND ayah = ? ORDER BY word", (surah_number, ayah_number))
        return [row[0] for row in self.cursor_wbw.fetchall()]

    def fetch_translation_for_word(self, surah_number: int, ayah_number: int, word_index: int) -> str:
        """Fetches the translation for a specific word in a specific verse.

        Args:
            surah_number: The surah number.
            ayah_number: The ayah number.
            word_index: The index of the word (1-indexed).

        Returns:
            The translation string for the specified word.
        """
        self.cursor_wbw.execute("SELECT translation FROM wbw WHERE surah = ? AND ayah = ? AND word = ?", (surah_number, ayah_number, word_index))
        result = self.cursor_wbw.fetchone()
        return result[0] if result else ""

    def close(self):
        self.conn_quran.close()
        self.conn_wbw.close()


if __name__ == "__main__":
    db = DatabaseManager()
    print("Words in Surah 1:", db.fetch_all_words_from_surah(1)[:10])
    print("Translations in Surah 1:", db.fetch_all_tr_words_from_surah(1)[:10])
