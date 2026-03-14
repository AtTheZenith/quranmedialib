from src.workflows.tests.test_isolate_words import test_isolate_words


def run_tests():
    print("=== Starting Workflow Tests ===")
    test_isolate_words()
    print("=== Workflow Tests Completed ===")


if __name__ == "__main__":
    run_tests()
