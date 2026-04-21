"""I/O utilities for high-performance image and data persistence.

This module provides utilities for non-blocking image saving
using background threads to overlap I/O and rendering.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Iterator

from quranmedialib.config import DEFAULT_IO_THREADS

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)

type SaveFunction = Callable[[Image.Image, str, Any], None]


@contextmanager
def async_image_saver(max_queue: int = 4) -> Iterator[SaveFunction]:
    """Manages background image saving to overlap CPU rendering and I/O.

    Uses multiple background threads and a bounded semaphore to prevent memory
    exhaustion if rendering outpaces the disk.

    Args:
        max_queue: Maximum number of images to queue before blocking.

    Yields:
        Callable: A save function that accepts (image, path, **kwargs).

    Example:
        with async_image_saver(max_queue=4) as save:
            for i, img in enumerate(images):
                save(img, f"image_{i}.png", compress_level=1)
    """
    executor = ThreadPoolExecutor(max_workers=DEFAULT_IO_THREADS)
    semaphore = threading.BoundedSemaphore(max_queue)
    futures = []

    def _save_task(image: Image.Image, path: str, **kwargs: Any) -> None:
        """Internal task to save and release the semaphore."""
        try:
            image.save(path, **kwargs)
        except Exception as e:
            logger.error("Failed to save image to %s: %s", path, e)
        finally:
            semaphore.release()

    def save(image: Image.Image, path: str, **kwargs: Any) -> None:
        """Queues an image for background saving.

        Blocks if the internal queue (max_queue) is full.

        Args:
            image: The PIL Image to save.
            path: Destination file path.
            **kwargs: Arguments passed to Image.save (e.g., format, compress_level).
        """
        semaphore.acquire()
        future = executor.submit(_save_task, image, path, **kwargs)
        futures.append(future)

    try:
        yield save
    finally:
        # Wait for all pending tasks
        if futures:
            wait(futures)
        executor.shutdown(wait=True)
