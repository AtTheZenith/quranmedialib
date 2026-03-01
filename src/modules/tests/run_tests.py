from src.modules.database_manager import DatabaseManager
from src.modules.tests.test_database_manager import test_database_manager
from src.modules.tests.test_wimage import test_wimage
from src.modules.tests.test_annotate_word import test_annotate_word
from src.modules.tests.test_verse_number import test_verse_number
from src.modules.tests.test_image import test_color, test_pad, test_glow
from src.modules.tests.test_framer import test_framer


def run_all_tests():
    print("Starting all tests...")

    # Order matters if there are dependencies, but here they are mostly independent
    # except for DatabaseManager singleton.

    test_database_manager()
    test_wimage()
    test_annotate_word()
    test_verse_number()
    test_color()
    test_pad()
    test_glow()
    test_framer()

    # Close database at the very end
    DatabaseManager().close()
    print("\nAll tests completed.")


if __name__ == "__main__":
    run_all_tests()
