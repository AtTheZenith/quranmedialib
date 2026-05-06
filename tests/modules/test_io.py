"""Tests for I/O utilities."""

import os
import shutil
import tempfile
import time
from unittest.mock import MagicMock

from PIL import Image

from quranmedialib.utils.io import async_image_saver


def test_async_image_saver_basic_save() -> None:
    """Verifies that images are saved correctly to disk."""
    temp_dir = tempfile.mkdtemp()
    try:
        with async_image_saver(max_queue=2) as save:
            img = Image.new("RGB", (100, 100), color="red")
            path = os.path.join(temp_dir, "test.png")
            save(img, path)

        # After context exit, file must exist
        assert os.path.exists(path)
        saved_img = Image.open(path)
        assert saved_img.size == (100, 100)
        saved_img.close()
    finally:
        shutil.rmtree(temp_dir)


def test_async_image_saver_max_queue_blocking() -> None:
    """Verifies that save() blocks when the queue is full."""
    max_queue = 1

    # Track save duration
    save_times = []

    def slow_save(*args, **kwargs):
        time.sleep(0.1)
        save_times.append(time.time())

    mock_img = MagicMock(spec=Image.Image)
    mock_img.save.side_effect = slow_save

    with async_image_saver(max_queue=max_queue) as save:
        start_time = time.time()

        # First save: should start immediately, but task takes 0.1s
        save(mock_img, "p1.png")

        # Second save: should block because max_queue=1 and first task still running
        save(mock_img, "p2.png")

        end_time = time.time()

        # Blocking should have happened
        assert end_time - start_time >= 0.05


def test_async_image_saver_lifecycle_wait() -> None:
    """Verifies that context exit waits for all tasks."""
    temp_dir = tempfile.mkdtemp()
    try:
        img = Image.new("RGB", (10, 10))
        paths = [os.path.join(temp_dir, f"test_{i}.png") for i in range(5)]

        with async_image_saver(max_queue=10) as save:
            for p in paths:
                save(img, p)
            # Context exit should trigger wait

        for p in paths:
            assert os.path.exists(p)
    finally:
        shutil.rmtree(temp_dir)


def test_async_image_saver_exception_handling(caplog) -> None:
    """Verifies that exceptions during save are logged and don't crash the worker."""
    # Mock image.save to raise an error
    mock_img = MagicMock(spec=Image.Image)
    mock_img.save.side_effect = Exception("Disk full")

    with async_image_saver(max_queue=1) as save:
        save(mock_img, "wont_save.png")

    assert "Failed to save image" in caplog.text
    assert "Disk full" in caplog.text
