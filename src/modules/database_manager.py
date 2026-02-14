# ./assets/quran.db
# table (is named 'verses') structure:
# "surah","ayah","text"

# ./assets/wbw_en.db
# table structure:
# "surah","ayah","word","translation"
# fetch by word only, it is used in parallel with fetch by word from corpus.db (to annotate words with translations)

"""
This is a class that will be used to manage the database.
This is to centralize the database operations and to prevent opening it in multiple places thereby causing memory leaks.
It will allow running custom operations and will have methods to fetch all verses from a surah, fetch all words from a surah, fetch all words from a verse, etc. to avoid repetition.
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

    def fetch_all_verses_from_surah(self, surah_number):
        self.cursor_quran.execute("SELECT ayah, text FROM verses WHERE sura = ? ORDER BY ayah", (surah_number,))
        verses_dict = {}
        for ayah, text in self.cursor_quran.fetchall():
            verses_dict.setdefault(ayah, []).append(text)
        return [" ".join(verses_dict[ayah_num]) for ayah_num in sorted(verses_dict)]

    def fetch_all_words_from_surah(self, surah_number):
        self.cursor_quran.execute("SELECT text FROM verses WHERE sura = ? ORDER BY ayah", (surah_number,))
        words = [word for row in self.cursor_quran.fetchall() for word in row[0].split(" ") if word != ""]
        return words

    def fetch_all_words_from_verse(self, surah_number, ayah_number):
        self.cursor_quran.execute("SELECT text FROM verses WHERE sura = ? AND ayah = ?", (surah_number, ayah_number))
        words = [word for row in self.cursor_quran.fetchall() for word in row[0].split(" ") if word != ""]
        return words

    def fetch_all_tr_words_from_surah(self, surah_number):
        """Fetches all translations for a given surah, ordered by ayah and word."""
        self.cursor_wbw.execute("SELECT translation FROM wbw WHERE surah = ? ORDER BY ayah, word", (surah_number,))
        return [row[0] for row in self.cursor_wbw.fetchall()]

    def fetch_all_tr_words_from_verse(self, surah_number, ayah_number):
        """Fetches all translations for a specific verse, ordered by word."""
        self.cursor_wbw.execute("SELECT translation FROM wbw WHERE surah = ? AND ayah = ? ORDER BY word", (surah_number, ayah_number))
        return [row[0] for row in self.cursor_wbw.fetchall()]

    def fetch_translation_for_word(self, surah_number, ayah_number, word_index):
        """Fetches the translation for a specific word in a specific verse."""
        self.cursor_wbw.execute("SELECT translation FROM wbw WHERE surah = ? AND ayah = ? AND word = ?", (surah_number, ayah_number, word_index))
        return self.cursor_wbw.fetchone()[0]

    def close(self):
        self.conn_quran.close()
        self.conn_wbw.close()


if __name__ == "__main__":
    db = DatabaseManager()
    print("Words in Surah 1:", db.fetch_all_words_from_surah(1)[:10])
    print("Translations in Surah 1:", db.fetch_all_tr_words_from_surah(1)[:10])
