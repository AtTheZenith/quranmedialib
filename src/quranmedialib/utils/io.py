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

type SaveFunction = Callable[..., None]


@contextmanager
def async_image_saver(max_queue: int = 4) -> Iterator[SaveFunction]:
    """Manages background image/data saving to overlap CPU rendering and I/O.

    Uses multiple background threads and a bounded semaphore to prevent memory
    exhaustion if rendering outpaces the disk.

    Args:
        max_queue: Maximum number of items to queue before blocking.

    Yields:
        Callable: A save function that accepts (image, path, **kwargs). The
            context also exposes a ``save_data(path, payload, **kwargs)`` attribute
            on the yielded callable for background writes of serialized data.

    Example:
        with async_image_saver(max_queue=4) as save:
            for i, img in enumerate(images):
                save(img, f"image_{i}.png", compress_level=1)
            save.save_data("sidecar.json", '{"schema": "spatial-1"}')
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

    def _write_task(path: str, payload: str | bytes, **kwargs: Any) -> None:
        """Internal task to write data and release the semaphore."""
        try:
            if isinstance(payload, str):
                with open(path, "w", encoding=kwargs.get("encoding", "utf-8")) as fh:
                    fh.write(payload)
            else:
                with open(path, "wb") as fh:
                    fh.write(payload)
        except Exception as e:
            logger.error("Failed to save data to %s: %s", path, e)
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

    def save_data(path: str, payload: str | bytes, **kwargs: Any) -> None:
        """Queues a data payload for background writing, sharing the image saver.

        Shares the same bounded semaphore and executor as :func:`save`, so a burst
        of data writes cannot bypass the backpressure applied to image saves.

        Args:
            path: Destination file path.
            payload: The serialized string (or raw bytes) to write.
            **kwargs: ``encoding`` for str payloads (default "utf-8").
        """
        semaphore.acquire()
        future = executor.submit(_write_task, path, payload, **kwargs)
        futures.append(future)

    # Expose save_data as an attribute of save so a single handle can write both.
    save.save_data = save_data  # type: ignore[attr-defined]

    try:
        yield save
    finally:
        # Wait for all pending tasks
        if futures:
            wait(futures)
        executor.shutdown(wait=True)
