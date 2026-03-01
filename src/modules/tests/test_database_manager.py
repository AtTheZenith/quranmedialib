from src.modules.database_manager import DatabaseManager, logger


def test_database_manager():
    print("\nRunning test_database_manager...")
    try:
        db = DatabaseManager()
        print(f"Words in Surah 1: {db.fetch_all_words_from_surah(1)[:10]}")
        print(f"Translations in Surah 1: {db.fetch_all_translations_from_surah(1)[:10]}")

        # Specific word translation demo
        trans = db.fetch_translation_for_word(1, 1, 1)
        print(f"Surah 1, Ayah 1, Word 1 translation: {trans}")
    except Exception as e:
        logger.error("Demo failed: %s", e)
        raise
    print("test_database_manager completed successfully.")


if __name__ == "__main__":
    test_database_manager()
