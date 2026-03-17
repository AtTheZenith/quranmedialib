"""
Framer module for laying out word images into pages with translation support.
"""

from __future__ import annotations

import itertools
from PIL import Image

from src.modules.configs import LayoutConfig, WordConfig

# Quranic stop signs for wrapping logic
QURANIC_STOP_SIGNS = ["ۖ", "ۗ", "ۚ", "ۛ", "ۜ", "ۙ", "ۘ", "ۗ"]


def _normalize_items(
    words: list[Image.Image],
    words_text: list[str] | None = None,
) -> list[tuple[Image.Image, str | None]]:
    """Zips words with their optional text content."""
    if words_text is None:
        return [(word, None) for word in words]
    return list(itertools.zip_longest(words, words_text))


def _build_row(
    all_items: list[tuple[Image.Image, str | None]],
    start_index: int,
    config: LayoutConfig,
    word_config: WordConfig,
) -> tuple[list[tuple[Image.Image, str | None]], int, int, int]:
    """
    Builds a single row of items from the given start index.
    Returns (row_items, items_consumed, row_width, max_row_height).
    """
    row_items = []
    current_row_width = 0
    max_row_height = 0
    items_consumed = 0

    for i in range(start_index, len(all_items)):
        word_image, _ = all_items[i]
        word_width, word_height = word_image.size

        # Check if the word fits in the current row
        spacing = word_config.word_spacing if row_items else 0
        if current_row_width + word_width + spacing > config.content_width:
            # If the row is empty, we MUST take at least one word to avoid infinite loops
            if not row_items:
                row_items.append(all_items[i])
                items_consumed += 1
                current_row_width = word_width
                max_row_height = word_height
            break

        current_row_width += word_width + spacing
        if word_height > max_row_height:
            max_row_height = word_height
        row_items.append(all_items[i])
        items_consumed += 1

    return row_items, items_consumed, current_row_width, max_row_height


def _fits_on_page(current_y: int, row_height: int, config: LayoutConfig) -> bool:
    """Checks if a row with the given height fits in the remaining vertical space."""
    return current_y + row_height + config.padding <= config.available_height + config.padding


def _group_items_into_rows(
    all_items: list[tuple[Image.Image, str | None]],
    config: LayoutConfig,
    word_config: WordConfig,
) -> tuple[list[list[tuple[Image.Image, str | None]]], int]:
    """Groups items into rows for a single page based on configuration."""
    page_rows = []
    current_y = config.padding
    total_items_consumed = 0

    while total_items_consumed < len(all_items) and len(page_rows) < word_config.max_rows_per_page:
        row_items, row_consumed, _, max_row_height = _build_row(all_items, total_items_consumed, config, word_config)

        if not row_items:
            break

        if not _fits_on_page(current_y, max_row_height, config):
            # If it's the first row and doesn't fit, we take it anyway to ensure progress
            if not page_rows:
                page_rows.append(row_items)
                total_items_consumed += row_consumed
            break

        page_rows.append(row_items)
        total_items_consumed += row_consumed
        current_y += max_row_height + word_config.row_spacing

    return page_rows, total_items_consumed


def _get_global_index(row_index: int, word_index: int, prefix_sums: list[int]) -> int:
    """Calculates the global index of a word given its row and word index."""
    return prefix_sums[row_index] + word_index + 1


def _apply_stop_sign_adjustment(
    current_image_rows: list[list[tuple[Image.Image, str | None]]],
    items_consumed: int,
) -> tuple[list[list[tuple[Image.Image, str | None]]], int]:
    """
    Adjusts page breaks to align with Quranic stop signs.
    Iterates backwards from the last word to find the nearest stop sign that
    would require keeping fewer items than originally planned.
    """
    row_lengths = [len(row) for row in current_image_rows]
    prefix_sums = [0] + list(itertools.accumulate(row_lengths))

    # Iterate backwards through rows and words to find a suitable stop sign
    for row_index in range(len(current_image_rows) - 1, -1, -1):
        row = current_image_rows[row_index]
        for word_index in range(len(row) - 1, -1, -1):
            _, text = row[word_index]
            if text and any(sign in text for sign in QURANIC_STOP_SIGNS):
                keep_count = _get_global_index(row_index, word_index, prefix_sums)

                # Only adjust if we are actually reducing the count (avoiding infinite loops)
                if keep_count < items_consumed:
                    adjusted_rows = current_image_rows[: row_index + 1]
                    adjusted_rows[-1] = adjusted_rows[-1][: word_index + 1]
                    return adjusted_rows, keep_count

    return current_image_rows, items_consumed


def _get_image_rows(
    items: list[tuple[Image.Image, str | None]],
    word_config: WordConfig,
    target_width: int,
) -> list[list[tuple[Image.Image, str | None]]]:
    """Internal greedy divider that respects a custom width for balancing calculations."""
    rows = []
    current_row = []
    current_width = 0

    for item in items:
        word_image, _ = item
        word_width = word_image.size[0]
        spacing = word_config.word_spacing if current_row else 0

        if current_width + word_width + spacing <= target_width:
            current_row.append(item)
            current_width += word_width + spacing
        elif current_row:
            rows.append(current_row)
            current_row = [item]
            current_width = word_width
        else:
            # Word is wider than target_width, give it its own row
            rows.append([item])
            current_row = []
            current_width = 0

    if current_row:
        rows.append(current_row)
    return rows


def _balance_image_rows(
    items: list[tuple[Image.Image, str | None]],
    target_num_rows: int,
    config: LayoutConfig,
    word_config: WordConfig,
) -> list[list[tuple[Image.Image, str | None]]]:
    """
    Finds the smallest target_width that maintains the target number of rows
    while ensuring the layout is 'top-heavy' (Line N >= Line N+1).
    """
    if not items:
        return []

    low = max((it[0].size[0] for it in items), default=0)
    high = config.content_width
    best_rows = _get_image_rows(items, word_config, high)

    while low <= high:
        mid = (low + high) // 2
        rows = _get_image_rows(items, word_config, mid)

        # Calculate widths to check for top-heavy constraint
        row_widths = []
        for row in rows:
            w = sum(it[0].size[0] for it in row) + (len(row) - 1) * word_config.word_spacing
            row_widths.append(w)

        # Check if widths are non-increasing (Line N >= Line N+1)
        is_top_heavy = all(row_widths[i] >= row_widths[i + 1] for i in range(len(row_widths) - 1))

        if len(rows) <= target_num_rows and is_top_heavy:
            best_rows = rows
            high = mid - 1
        else:
            low = mid + 1

    return best_rows


def _get_verse_start_y(content_height: int, config: LayoutConfig, word_config: WordConfig) -> int:
    """Calculates the starting Y coordinate for the verse content based on alignment."""
    if word_config.verse_vertical_align == "center" and content_height < config.available_height:
        return config.padding + (config.available_height - content_height) // 2 + word_config.verse_v_offset
    return config.padding + word_config.verse_v_offset


def _get_row_start_x(row_width: int, config: LayoutConfig, word_config: WordConfig) -> int:
    """Calculates the starting X coordinate for a row (Right-to-Left)."""
    if word_config.verse_horizontal_align == "center" and row_width < config.content_width:
        # Centered RTL: start from padding + offset + row_width (since we paste moving left)
        return config.padding + (config.content_width - row_width) // 2 + row_width
    # Right-aligned: start from far right
    return config.max_width - config.padding


def _render_page(
    rows: list[list[tuple[Image.Image, str | None]]],
    config: LayoutConfig,
    word_config: WordConfig,
) -> Image.Image:
    """Renders a single page of rows into an RGBA image."""
    page_image = Image.new("RGBA", (config.max_width, config.image_height), color=(0, 0, 0, 0))

    row_heights = [max((item[0].size[1] for item in row), default=0) for row in rows]
    total_verse_height = sum(row_heights) + (len(rows) - 1) * word_config.row_spacing if rows else 0

    draw_y = _get_verse_start_y(total_verse_height, config, word_config)

    for i, row in enumerate(rows):
        max_row_height = row_heights[i]
        row_width = sum(item[0].size[0] for item in row) + (len(row) - 1) * word_config.word_spacing

        # current_x represents the right edge of the next word to be pasted
        current_x = _get_row_start_x(row_width, config, word_config)

        for word_image, _ in row:
            word_width, word_height = word_image.size
            # Center word vertically within the row height
            word_y = draw_y + (max_row_height - word_height) // 2

            # Paste word moving from right to left
            page_image.paste(
                word_image,
                (current_x - word_width, word_y),
                mask=word_image if word_image.mode == "RGBA" else None,
            )
            current_x -= word_width + word_config.word_spacing

        draw_y += max_row_height + word_config.row_spacing

    return page_image


def frame(
    words: list[Image.Image],
    words_text: list[str] | None = None,
    translation_images: list[Image.Image | None] | None = None,
    config: LayoutConfig | None = None,
    word_config: WordConfig | None = None,
) -> list[Image.Image]:
    """
    Manages the 2D grid layout of word images into one or more pages.
    Supports right-to-left layout and bottom-aligned translations.
    """
    if not words:
        return []

    # Use provided configs or create default ones
    if config is None:
        config = LayoutConfig(
            max_width=1920,
            image_height=1080,
            padding=50,
            bottom_offset=300,
        )
    if word_config is None:
        word_config = WordConfig(
            word_spacing=20,
            row_spacing=30,
            max_rows_per_page=5,
        )

    all_items = _normalize_items(words, words_text)
    images: list[Image.Image] = []

    page_index = 0
    while all_items:
        # Plan the rows for this page
        current_rows, items_consumed = _group_items_into_rows(all_items, config, word_config)

        # Adjust page break to end at a stop sign if possible
        if words_text and items_consumed < len(all_items):
            current_rows, items_consumed = _apply_stop_sign_adjustment(current_rows, items_consumed)

        # If balancing is enabled and we have multiple rows, redistribute words symmetrically (top-heavy)
        if word_config.balanced_wrapping and len(current_rows) > 1:
            current_rows = _balance_image_rows(
                list(itertools.chain.from_iterable(current_rows)),
                len(current_rows),
                config,
                word_config,
            )

        # Render the verse content
        page_image = _render_page(current_rows, config, word_config)

        # Paste the pre-rendered translation image at the bottom if present
        if translation_images and page_index < len(translation_images):
            if trans_img := translation_images[page_index]:
                # Vertical position: centered within the reserved bottom area
                reserved_top_y = config.image_height - config.padding - config.bottom_offset
                trans_y = reserved_top_y + (config.bottom_offset - trans_img.height) // 2
                # Horizontal centering
                trans_x = (config.max_width - trans_img.width) // 2
                page_image.paste(
                    trans_img,
                    (trans_x, trans_y),
                    mask=trans_img if trans_img.mode == "RGBA" else None,
                )

        images.append(page_image)
        all_items = all_items[items_consumed:]
        page_index += 1

    return images
