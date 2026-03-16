from src.workflows.tests.test_isolate_words import test_isolate_words
from src.workflows.tests.test_verse_range import test_verse_range
from src.workflows.tests.test_surah import test_surah


def run_tests():
    print("=== Starting Workflow Tests ===")
    test_isolate_words()
    test_verse_range()
    test_surah()
    print("=== Workflow Tests Completed ===")


if __name__ == "__main__":
    run_tests()
