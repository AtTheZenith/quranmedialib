from src.modules.database_manager import DatabaseManager, logger


def test_database_manager():
    print("\nRunning test_database_manager...")
    try:
        db = DatabaseManager()

        # Test Renamed methods
        verses = db.get_verses_from_surah(1)
        print(f"Verses in Surah 1: {verses[:2]}")
        assert len(verses) > 0

        verse_text = db.get_verse(1, 1)
        print(f"Verse 1:1 text: {verse_text}")
        assert "بِسْمِ" in verse_text

        wbw_surah = db.get_wbw_from_surah(1)
        print(f"WBW translations in Surah 1: {wbw_surah[:5]}")
        assert len(wbw_surah) > 0

        wbw_verse = db.get_wbw_from_verse(1, 1)
        print(f"WBW translations in Verse 1:1: {wbw_verse}")
        assert len(wbw_verse) > 0

        wbw_word = db.get_wbw_from_word(1, 1, 1)
        print(f"WBW translation for 1:1:1: {wbw_word}")
        assert wbw_word is not None

        # Test New Translation methods (en_sahih.db)
        trans_surah = db.get_translation_from_surah(1)
        print(f"Full translations in Surah 1: {trans_surah[:2]}")
        assert len(trans_surah) == 7

        trans_verse = db.get_translation_from_verse(1, 1)
        print(f"Full translation for 1:1: {trans_verse}")
        assert trans_verse is not None
        assert "In the name of Allah" in trans_verse

    except Exception as e:
        logger.error("Tests failed: %s", e)
        raise
    print("test_database_manager completed successfully.")


if __name__ == "__main__":
    test_database_manager()
    DatabaseManager().close()
