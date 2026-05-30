"""Framer module for laying out word images into pages with translation support.

This module handles the complex 2D spatial arrangement of Arabic word images,
supporting Right-to-Left (RTL) flow, multi-page splitting, Quranic stop-sign
aware wrapping, and balanced line distribution.
"""

from __future__ import annotations

import itertools
import logging
from typing import Sequence

from PIL import Image

from quranmedialib.types import (
    Color,
    HorizontalAlignment,
    FrameConfig,
    VerticalAlignment,
    VerseConfig,
    WordConfig,
    WordItem,
)
from quranmedialib.modules.vimage import VImage
from quranmedialib.modules.frame import Frame

logger = logging.getLogger(__name__)

__all__ = [
    "frame",
]


def _get_verse_start_y(content_height: int, config: FrameConfig, word_config: WordConfig) -> int:
    """Calculates the starting Y coordinate for the entire verse block."""
    y_start = config.padding.top + word_config.verse_v_offset

    if config.wimage_vertical_align == VerticalAlignment.CENTER:
        if content_height < config.available_height:
            y_start += (config.available_height - content_height) // 2
    elif config.wimage_vertical_align == VerticalAlignment.BOTTOM:
        if content_height < config.available_height:
            y_start += config.available_height - content_height

    final_y = y_start + config.wimage_y_offset

    # Prevent clipping when aligned to TOP: ensure we don't go above the top padding.
    if config.wimage_vertical_align == VerticalAlignment.TOP:
        return max(config.padding.top, final_y)

    return final_y


def frame(
    words: list[WordItem],
    translation_images: Sequence[Image.Image | None] | None = None,
    frame_cfg: FrameConfig | None = None,
    verse_cfg: VerseConfig | None = None,
    word_cfg: WordConfig | None = None,
    text_color: Color | None = None,
) -> list[Image.Image]:
    """Manages the 2D grid layout of word images into one or more pages.
    
    This function handles right-to-left layout and supports automatic page-break
    adjustment based on Quranic stop signs using WordItem metadata.
    
    Args:
        words: List of WordItem objects (containing image and optional text).
        translation_images: Optional pre-rendered translation images to paste at bottom.
        frame_cfg: FrameConfig for canvas sizing and offsets.
        verse_cfg: VerseConfig for spacing and wrapping behavior.
        word_cfg: WordConfig for rendering colors and fonts.


    Returns:
        A list of rendered PIL Images (one per page).

    Raises:
        ValueError: If one or more WordItems are missing their image content.
    """
    if not words:
        return []

    # Apply defaults if configs are missing.
    if frame_cfg is None:
        frame_cfg = FrameConfig(max_width=1920, image_height=1080, padding=(50, 350, 50, 50), timage_y_offset=880)
    if verse_cfg is None:
        verse_cfg = VerseConfig(word_spacing=20, row_spacing=30, max_rows_per_page=5)
    if word_cfg is None:
        word_cfg = WordConfig(word_spacing=20, row_spacing=30, max_rows_per_page=5, font_size=80)

    all_items = list(words)
    if any(item.image is None for item in all_items):
        raise ValueError("One or more WordItems are missing their image content.")

    # 0. Initialize VImage for the entire verse.
    vimage = VImage(all_items, verse_cfg, frame_cfg)

    pages: list[Image.Image] = []
    page_index = 0
    current_index = 0
    total_items = len(all_items)

    while current_index < total_items:
        # 1. Get rows for the current page (incorporates grouping and stop-sign adjustment).
        current_rows, items_consumed = vimage.get_page_chunk(current_index, verse_cfg.max_rows_per_page)

        # 2. Compose the page.
        frame_obj = Frame(frame_cfg)
        v_image = vimage.render(word_cfg, rows_to_render=current_rows)
        frame_obj.layer(
            v_image,
            alignment=(frame_cfg.wimage_horizontal_align, frame_cfg.wimage_vertical_align),
            offset=(frame_cfg.wimage_x_offset, frame_cfg.wimage_y_offset),
        )

        # 3. Overlays: Translation images.
        if translation_images and page_index < len(translation_images):
            if t_image := translation_images[page_index]:
                frame_obj.layer(
                    t_image,
                    alignment=(frame_cfg.timage_horizontal_align, frame_cfg.timage_vertical_align),
                    offset=(frame_cfg.timage_x_offset, frame_cfg.timage_y_offset),
                    text_color=text_color or (255, 255, 255, 255),
                )

        pages.append(frame_obj.render())
        current_index += items_consumed
        page_index += 1

    return pages
