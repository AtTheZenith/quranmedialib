from tests.workflows.test_isolate_words import test_isolate_words
from tests.workflows.test_verse_range import test_verse_range
from tests.workflows.test_surah import test_surah_stress


def run_tests():
    print("=== Starting Workflow Tests ===")
    test_isolate_words()
    test_verse_range()
    test_surah_stress()
    print("=== Workflow Tests Completed ===")


if __name__ == "__main__":
    run_tests()
