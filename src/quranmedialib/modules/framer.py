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
    LayoutConfig,
    VerticalAlignment,
    WordConfig,
    WordItem,
)

logger = logging.getLogger(__name__)

__all__ = [
    "frame",
    "QURANIC_STOP_SIGNS",
]

# Quranic stop signs for wrapping logic. These signs indicate natural pausing
# points in the text and are used to avoid awkward line breaks.
QURANIC_STOP_SIGNS = ["ۖ", "ۗ", "ۚ", "ۛ", "ۜ", "ۙ", "ۘ"]


def _build_row(
    all_items: list[WordItem],
    start_index: int,
    config: LayoutConfig,
    word_config: WordConfig,
) -> tuple[list[WordItem], int, int, int]:
    """Builds a single row of items until the max width is reached.

    Args:
        all_items: The full list of WordItems.
        start_index: Index of the first word to place in this row.
        config: Layout geometry.
        word_config: Spacing rules.

    Returns:
        (row_items, items_consumed, row_width, max_row_height)
    """
    row_items = []
    current_row_width = 0
    max_row_height = 0

    for item in all_items[start_index:]:
        word_width, word_height = item.width, item.height
        spacing = word_config.word_spacing if row_items else 0

        if current_row_width + word_width + spacing > config.content_width:
            if not row_items:
                # Force at least one item to avoid infinite loop
                return [item], 1, word_width, word_height
            break

        current_row_width += word_width + spacing
        max_row_height = max(max_row_height, word_height)
        row_items.append(item)

    return row_items, len(row_items), current_row_width, max_row_height


def _fits_on_page(current_y: int, row_height: int, config: LayoutConfig) -> bool:
    """Checks if a row with the given height fits in the remaining vertical space."""
    limit = config.available_height + config.padding.top
    return current_y + row_height <= limit


def _group_items_into_rows(
    all_items: list[WordItem],
    start_index: int,
    config: LayoutConfig,
    word_config: WordConfig,
) -> tuple[list[list[WordItem]], int]:
    """Groups items into rows for a single page based on line count and height.

    Args:
        all_items: List of all items to be processed.
        start_index: Index of the first item to process.
        config: Layout geometry.
        word_config: Page limits (max_rows_per_page).

    Returns:
        A tuple of (list of rows, total items consumed from start_index).
    """
    page_rows = []
    current_y = config.padding.top
    total_items_consumed = 0
    current_pos = start_index

    while current_pos < len(all_items) and len(page_rows) < word_config.max_rows_per_page:
        row_items, row_consumed, _, max_row_height = _build_row(all_items, current_pos, config, word_config)

        if not row_items:
            break

        # Check vertical fit for this row
        if not _fits_on_page(current_y, max_row_height, config):
            # If the page is empty, we force the row to avoid stuck iterations.
            if not page_rows:
                page_rows.append(row_items)
                total_items_consumed += row_consumed
            break

        page_rows.append(row_items)
        total_items_consumed += row_consumed
        current_pos += row_consumed
        current_y += max_row_height + word_config.row_spacing

    return page_rows, total_items_consumed


def _get_global_index(row_index: int, word_index: int, prefix_sums: list[int]) -> int:
    """Calculates the 1-based global index of a word given its location in rows."""
    return prefix_sums[row_index] + word_index + 1


def _apply_stop_sign_adjustment(
    current_image_rows: list[list[WordItem]],
    items_consumed: int,
) -> tuple[list[list[WordItem]], int]:
    """Adjusts page breaks backwards to end on a Quranic stop sign.

    This ensures that lines don't break mid-phrase if a natural pause
    point is available nearby on the same page.
    """
    row_lengths = [len(row) for row in current_image_rows]
    prefix_sums = [0] + list(itertools.accumulate(row_lengths))

    for row_index in range(len(current_image_rows) - 1, -1, -1):
        row = current_image_rows[row_index]
        for word_index in range(len(row) - 1, -1, -1):
            item = row[word_index]
            # Check if this word contains a stop sign marker.
            if item.text and any(sign in item.text for sign in QURANIC_STOP_SIGNS):
                keep_count = _get_global_index(row_index, word_index, prefix_sums)

                # Only adjust if it actually reduces the item count (moves break backwards).
                if keep_count < items_consumed:
                    adjusted_rows = current_image_rows[: row_index + 1]
                    adjusted_rows[-1] = adjusted_rows[-1][: word_index + 1]
                    return adjusted_rows, keep_count

    return current_image_rows, items_consumed


def _get_image_rows(
    items: list[WordItem],
    word_config: WordConfig,
    target_width: int,
    max_rows: int | None = None,
) -> list[list[WordItem]]:
    """Internal greedy divider for a specific width constraint.

    Used primarily as a core primitive for the binary-search balancing algorithm.

    Args:
        items: List of word items to arrange.
        word_config: Configuration with spacing settings.
        target_width: Target row width in pixels.
        max_rows: Optional maximum number of rows before early termination.

    Returns:
        List of rows (each row is a list of WordItems).
    """
    rows = []
    current_row = []
    current_width = 0

    for item in items:
        word_width = item.width
        spacing = word_config.word_spacing if current_row else 0

        if current_width + word_width + spacing <= target_width:
            current_row.append(item)
            current_width += word_width + spacing
        elif current_row:
            rows.append(current_row)
            # Early termination if we exceed max_rows
            if max_rows is not None and len(rows) > max_rows:
                return rows
            current_row = [item]
            current_width = word_width
        else:
            # Word is wider than target_width, force it into its own row.
            rows.append([item])
            # Early termination check
            if max_rows is not None and len(rows) > max_rows:
                return rows
            current_row = []
            current_width = 0

    if current_row:
        rows.append(current_row)
    return rows


def _balance_image_rows(
    items: list[WordItem],
    target_num_rows: int,
    config: LayoutConfig,
    word_config: WordConfig,
) -> list[list[WordItem]]:
    """Binary searches for the minimum first-line width that produces target_num_rows.

    Strictly enforces an inverted pyramid shape (W_i >= W_{i+1}).
    Delegates to the centralized balance_lines_pyramid utility.
    """
    if not items:
        return []

    from quranmedialib.modules.text_layout import balance_lines_pyramid

    widths = [it.width for it in items]
    best_breaks = balance_lines_pyramid(
        widths=widths,
        spacing=word_config.word_spacing,
        target_k=target_num_rows,
        max_width=config.content_width,
    )

    if best_breaks is None:
        return _get_image_rows(items, word_config, config.content_width)

    final_rows = []
    current_row = []
    break_set = set(best_breaks)
    for i, item in enumerate(items):
        if i in break_set:
            final_rows.append(current_row)
            current_row = []
        current_row.append(item)
    if current_row:
        final_rows.append(current_row)

    return final_rows


def _get_verse_start_y(content_height: int, config: LayoutConfig, word_config: WordConfig) -> int:
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


def _get_row_start_x(row_width: int, config: LayoutConfig) -> int:
    """Calculates the starting X coordinate for a row (Right-to-Left anchoring)."""
    # RTL default: anchor to the right margin.
    x_start = config.max_width - config.padding.right

    if config.wimage_horizontal_align == HorizontalAlignment.CENTER:
        if row_width < config.content_width:
            x_start = config.padding.left + (config.content_width - row_width) // 2 + row_width
    elif config.wimage_horizontal_align == HorizontalAlignment.LEFT:
        if row_width < config.content_width:
            x_start = config.padding.left + row_width

    return x_start + config.wimage_x_offset


def _render_page(
    rows: list[list[WordItem]],
    config: LayoutConfig,
    word_config: WordConfig,
) -> Image.Image:
    """Renders a single page of rows into an RGBA image."""
    page_image = Image.new("RGBA", (config.max_width, config.image_height), color=(0, 0, 0, 0))

    row_heights = [max((item.height for item in row), default=0) for row in rows]
    total_verse_height = sum(row_heights) + (len(rows) - 1) * word_config.row_spacing if rows else 0

    draw_y = _get_verse_start_y(total_verse_height, config, word_config)

    # Local references for performance
    word_spacing = word_config.word_spacing
    row_spacing = word_config.row_spacing
    global_word_color = word_config.word_color
    alpha_composite = page_image.alpha_composite

    for i, row in enumerate(rows):
        max_row_height = row_heights[i]
        row_width = sum(item.width for item in row) + (len(row) - 1) * word_spacing
        current_x = _get_row_start_x(row_width, config)

        # OPTIM: Merge row into a single mask if colors are uniform and all use L mode
        first_color = row[0].color if row else None
        can_merge = len(row) > 1 and all(item.image.mode == "L" and item.color == first_color for item in row)

        if can_merge:
            row_mask = Image.new("L", (row_width, max_row_height), 0)
            rx = row_width
            for item in row:
                w_img = item.image
                ry = (max_row_height - w_img.height) // 2
                rx -= w_img.width
                row_mask.paste(w_img, (rx, ry))
                rx -= word_spacing

            color_to_use = first_color if first_color is not None else global_word_color
            page_image.paste(color_to_use, (current_x - row_width, draw_y), mask=row_mask)
        else:
            # Fallback word-by-word
            for item in row:
                w_img = item.image
                ry = draw_y + (max_row_height - w_img.height) // 2
                color_to_use = item.color if item.color is not None else global_word_color

                if w_img.mode == "L":
                    page_image.paste(color_to_use, (current_x - w_img.width, ry), mask=w_img)
                else:
                    alpha_composite(w_img, dest=(current_x - w_img.width, ry))

                current_x -= w_img.width + word_spacing

        draw_y += max_row_height + row_spacing

    return page_image


def _paste_translation_image(
    page_image: Image.Image,
    trans_img: Image.Image,
    config: LayoutConfig,
    text_color: Color = (255, 255, 255, 255),
) -> None:
    """Pastes a translation image onto a page based on configured alignment."""
    # Vertical placement
    trans_y = config.padding.top + config.timage_y_offset
    if config.timage_vertical_align == VerticalAlignment.CENTER:
        trans_y = config.padding.top + (config.available_height - trans_img.height) // 2 + config.timage_y_offset
    elif config.timage_vertical_align == VerticalAlignment.BOTTOM:
        trans_y = config.padding.top + config.available_height - trans_img.height + config.timage_y_offset

    # Prevent clipping when aligned to TOP: ensure we don't go above the top padding.
    if config.timage_vertical_align == VerticalAlignment.TOP:
        trans_y = max(config.padding.top, trans_y)

    # Horizontal placement
    trans_x = config.padding.left + config.timage_x_offset
    if config.timage_horizontal_align == HorizontalAlignment.CENTER:
        trans_x = config.padding.left + (config.content_width - trans_img.width) // 2 + config.timage_x_offset
    elif config.timage_horizontal_align == HorizontalAlignment.RIGHT:
        trans_x = config.padding.left + config.content_width - trans_img.width + config.timage_x_offset

    # Warn if translation image would be clipped off-canvas
    if (
        trans_x < 0
        or trans_y < 0
        or trans_x + trans_img.width > config.max_width
        or trans_y + trans_img.height > config.image_height
    ):
        logger.warning(
            "Translation image (%dx%d at x=%d, y=%d) will be clipped off canvas "
            "(%dx%d). Consider adjusting timage offsets or canvas dimensions.",
            trans_img.width,
            trans_img.height,
            trans_x,
            trans_y,
            config.max_width,
            config.image_height,
        )

    # PERF: Use masked paste for grayscale masks (L), alpha_composite for RGBA
    if trans_img.mode == "L":
        page_image.paste(text_color, (trans_x, trans_y), mask=trans_img)
    elif trans_img.mode == "RGBA":
        page_image.alpha_composite(trans_img, dest=(trans_x, trans_y))
    else:
        page_image.paste(trans_img, (trans_x, trans_y))


def frame(
    words: list[WordItem],
    translation_images: Sequence[Image.Image | None] | None = None,
    config: LayoutConfig | None = None,
    word_config: WordConfig | None = None,
    text_color: Color | None = None,
) -> list[Image.Image]:
    """Manages the 2D grid layout of word images into one or more pages.

    This function handles right-to-left layout and supports automatic page-break
    adjustment based on Quranic stop signs using WordItem metadata.

    Args:
        words: List of WordItem objects (containing image and optional text).
        translation_images: Optional pre-rendered translation images to paste at bottom.
        config: LayoutConfig for canvas sizing and offsets.
        word_config: WordConfig for spacing and wrapping behavior.

    Returns:
        A list of rendered PIL Images (one per page).

    Raises:
        ValueError: If one or more WordItems are missing their image content.
    """
    if not words:
        return []

    # Apply defaults if configs are missing.
    if config is None:
        config = LayoutConfig(max_width=1920, image_height=1080, padding=(50, 350, 50, 50), timage_y_offset=880)
    if word_config is None:
        word_config = WordConfig(word_spacing=20, row_spacing=30, max_rows_per_page=5, font_size=80)

    # Configs are validated at creation (__post_init__) — no redundant checks needed

    all_items = list(words)
    if any(item.image is None for item in all_items):
        raise ValueError("One or more WordItems are missing their image content.")

    pages: list[Image.Image] = []
    page_index = 0
    current_index = 0
    total_items = len(all_items)

    while current_index < total_items:
        # 1. Greedy grouping into rows for the current page.
        current_rows, items_consumed = _group_items_into_rows(all_items, current_index, config, word_config)

        # 2. Adjust break backwards to end on a stop sign if possible.
        remaining_items = total_items - current_index
        if any(it.text for it in all_items[current_index:]) and items_consumed < remaining_items:
            current_rows, items_consumed = _apply_stop_sign_adjustment(current_rows, items_consumed)

        # 3. Optional balancing: redistribute words to make lines more even/top-heavy.
        if word_config.balanced_wrapping and len(current_rows) > 1:
            current_rows = _balance_image_rows(
                list(itertools.chain.from_iterable(current_rows)),
                len(current_rows),
                config,
                word_config,
            )

        # 4. Render the page canvas.
        page_image = _render_page(current_rows, config, word_config)

        # 5. Overlays: Translation images.
        if translation_images and page_index < len(translation_images):
            if trans_img := translation_images[page_index]:
                _paste_translation_image(
                    page_image,
                    trans_img,
                    config,
                    text_color=text_color or (255, 255, 255, 255),
                )

        pages.append(page_image)
        current_index += items_consumed
        page_index += 1

    return pages
