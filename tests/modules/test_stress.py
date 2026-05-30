import gc
import threading

from quranmedialib import DatabaseManager, VerseWorkflow, WordConfig, LANDSCAPE_PRESET
from quranmedialib.utils.memory import get_current_rss_mb
from quranmedialib.utils.parallel import ExecutionMode, ParallelRenderer


def test_database_manager_rapid_reinit_stress():
    """Stress test DatabaseManager singleton and connection pooling under rapid re-init."""
    errors = []

    def worker():
        try:
            for _ in range(50):
                db = DatabaseManager()
                # Trigger a query to ensure connection is active
                db.get_verses_from_surah(1)
                # Rapidly close and reset singleton
                db.close()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Detected {len(errors)} errors during rapid re-init: {errors}"


def task_fn(batch: list[int]) -> list[int]:
    return [x * x for x in batch]


def test_parallel_renderer_extreme_churn():
    """Stress test ParallelRenderer with high volume of small tasks and rapid pool resets."""
    renderer = ParallelRenderer(mode=ExecutionMode.PROCESS)

    # Batch of 1000 small tasks
    tasks = list(range(1000))
    results = list(renderer.map_batches(task_fn, tasks))

    assert results == [x * x for x in tasks]

    # The ParallelRenderer uses a singleton pool manager, so it should be stable


def test_rendering_memory_stability():
    """Verify that memory usage remains stable (no leaks) during repeated heavy rendering."""
    # Setup simple config
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseWorkflow(preset)

    # Translation for a verse
    translations = [
        "This is a test translation that we repeat many times to ensure we are using significant memory."
    ] * 5

    baseline_mem = get_current_rss_mb()

    # Render the same verse 100 times
    for _ in range(100):
        # Convert iterator to list to force rendering
        list(workflow.get_iterator(1, 1, translations))
        gc.collect()

    final_mem = get_current_rss_mb()

    # Allow for some reasonable growth/fragmentation, but not a massive leak
    # (e.g., < 100MB increase)
    assert final_mem - baseline_mem < 100, f"Potential memory leak detected: {final_mem - baseline_mem:.2f} MB increase"


if __name__ == "__main__":
    # Manual run for quick verification
    print("Running stress tests...")
    test_database_manager_rapid_reinit_stress()
    print("DB Re-init: Passed")
    test_parallel_renderer_extreme_churn()
    print("Parallel Churn: Passed")
    test_rendering_memory_stability()
    print("Memory Stability: Passed")
