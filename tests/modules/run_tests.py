from quranmedialib import DatabaseManager
from .test_annotation import test_annotate_word, test_annotate_words
from .test_database_manager import test_database_manager
from .test_framer import test_framer, test_framer_alignment, test_framer_offsets
from .test_image import test_color, test_glow, test_pad
from .test_timage import test_timage_formatting
from .test_verse_number import test_verse_number
from .test_wimage import test_wimage


def run_all_tests():
    print("=== Starting module tests ===")

    # Order matters if there are dependencies, but here they are mostly independent
    # except for DatabaseManager singleton.

    test_database_manager()
    test_timage_formatting()
    test_wimage()
    test_annotate_word()
    test_annotate_words()
    test_verse_number()
    test_color()
    test_pad()
    test_glow()
    test_framer()
    test_framer_alignment()
    test_framer_offsets()

    # Close database at the very end
    DatabaseManager().close()
    print("\n=== Modules tests completed ===")


if __name__ == "__main__":
    run_all_tests()
