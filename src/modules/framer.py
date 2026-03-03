"""
Framer module for laying out word images into pages with translation support.
"""

from __future__ import annotations

import itertools
import logging
from PIL import Image, ImageDraw, ImageFont

# Quranic stop signs for wrapping logic
QURANIC_STOP_SIGNS = ["ۖ", "ۗ", "ۚ", "ۛ", "ۜ", "ۙ", "ۘ", "ۗ"]


class LayoutConfig:
    """Helper class to store layout-related configuration."""

    def __init__(
        self,
        max_width: int,
        image_height: int,
        padding: int,
        word_spacing: int,
        row_spacing: int,
        max_rows_per_page: int,
        bottom_offset: int = 0,
        verse_vertical_align: str = "center",
        verse_horizontal_align: str = "center",
        verse_v_offset: int = 0,
    ):
        self.max_width = max_width
        self.image_height = image_height
        self.padding = padding
        self.word_spacing = word_spacing
        self.row_spacing = row_spacing
        self.max_rows_per_page = max_rows_per_page
        self.bottom_offset = bottom_offset
        self.verse_vertical_align = verse_vertical_align
        self.verse_horizontal_align = verse_horizontal_align
        self.verse_v_offset = verse_v_offset

    @property
    def content_width(self) -> int:
        """The available width for horizontal layout."""
        return self.max_width - 2 * self.padding

    @property
    def available_height(self) -> int:
        """The available height for vertical layout, excluding bottom reserved area."""
        return self.image_height - 2 * self.padding - self.bottom_offset


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
) -> tuple[list[tuple[Image.Image, str | None]], int, int, int]:
    """
    Builds a single row of items from the given start index.
    Returns (row_items, items_consumed, row_width, max_row_height).
    """
    row_items = []
    current_row_width = 0
    items_consumed = 0

    for i in range(start_index, len(all_items)):
        word_image, _ = all_items[i]
        word_width, word_height = word_image.size

        # Check if the word fits in the current row
        spacing = config.word_spacing if row_items else 0
        if current_row_width + word_width + spacing > config.content_width:
            # If the row is empty, we MUST take at least one word to avoid infinite loops
            if not row_items:
                row_items.append(all_items[i])
                items_consumed += 1
                current_row_width = word_width
            break

        current_row_width += word_width + spacing
        row_items.append(all_items[i])
        items_consumed += 1

    max_row_height = max((item[0].size[1] for item in row_items), default=0)
    return row_items, items_consumed, current_row_width, max_row_height


def _fits_on_page(current_y: int, row_height: int, config: LayoutConfig) -> bool:
    """Checks if a row with the given height fits in the remaining vertical space."""
    return current_y + row_height + config.padding <= config.available_height + config.padding


def _group_items_into_rows(
    all_items: list[tuple[Image.Image, str | None]],
    config: LayoutConfig,
) -> tuple[list[list[tuple[Image.Image, str | None]]], int]:
    """Groups items into rows for a single page based on configuration."""
    page_rows = []
    current_y = config.padding
    total_items_consumed = 0

    while total_items_consumed < len(all_items) and len(page_rows) < config.max_rows_per_page:
        row_items, row_consumed, _, max_row_height = _build_row(all_items, total_items_consumed, config)

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
        current_y += max_row_height + config.row_spacing

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


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    """Measures the width of a given text string."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _get_lines(words: list[str], word_widths: dict[str, int], space_width: int, target_width: int) -> list[str]:
    res_lines = []
    current_line = []
    current_width = 0

    for word in words:
        word_width = word_widths[word]
        # Width if we add this word to the current line (including space)
        added_width = word_width + (space_width if current_line else 0)

        if current_width + added_width <= target_width:
            current_line.append(word)
            current_width += added_width
        elif current_line:
            res_lines.append(" ".join(current_line))
            current_line = [word]
            current_width = word_width
        else:
            res_lines.append(word)
            current_line = []
            current_width = 0

    if current_line:
        res_lines.append(" ".join(current_line))
    return res_lines


def _wrap_text_balanced(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """
    Wraps text into lines such that the line widths are as balanced as possible.
    Uses a greedy approach combined with binary search on target width.
    """
    words = text.split()
    if not words:
        return []

    # Cache word widths to avoid redundant text measurement
    word_widths = {word: _measure_text(draw, word, font) for word in set(words)}
    space_width = _measure_text(draw, " ", font)

    # First, get a baseline using greedy wrapping at max_width
    greedy_lines = _get_lines(words, word_widths, space_width, max_width)
    target_num_lines = len(greedy_lines)

    if target_num_lines <= 1:
        return greedy_lines

    # Binary search for the smallest width that maintains the same number of lines
    low = max(word_widths.values())
    high = max_width
    best_lines = greedy_lines

    while low <= high:
        mid = (low + high) // 2
        lines = _get_lines(words, word_widths, space_width, mid)
        if len(lines) <= target_num_lines:
            best_lines = lines
            high = mid - 1
        else:
            low = mid + 1

    return best_lines


def _get_verse_start_y(content_height: int, config: LayoutConfig) -> int:
    """Calculates the starting Y coordinate for the verse content based on alignment."""
    if config.verse_vertical_align == "center" and content_height < config.available_height:
        return config.padding + (config.available_height - content_height) // 2 + config.verse_v_offset
    return config.padding + config.verse_v_offset


def _get_row_start_x(row_width: int, config: LayoutConfig) -> int:
    """Calculates the starting X coordinate for a row (Right-to-Left)."""
    if config.verse_horizontal_align == "center" and row_width < config.content_width:
        # Centered RTL: start from padding + offset + row_width (since we paste moving left)
        return config.padding + (config.content_width - row_width) // 2 + row_width
    # Right-aligned: start from far right
    return config.max_width - config.padding


def _render_page(
    rows: list[list[tuple[Image.Image, str | None]]],
    config: LayoutConfig,
) -> Image.Image:
    """Renders a single page of rows into an RGBA image."""
    page_image = Image.new("RGBA", (config.max_width, config.image_height), color=(0, 0, 0, 0))

    row_heights = [max((item[0].size[1] for item in row), default=0) for row in rows]
    total_verse_height = sum(row_heights) + (len(rows) - 1) * config.row_spacing if rows else 0

    draw_y = _get_verse_start_y(total_verse_height, config)

    for i, row in enumerate(rows):
        max_row_height = row_heights[i]
        row_width = sum(item[0].size[0] for item in row) + (len(row) - 1) * config.word_spacing

        # current_x represents the right edge of the next word to be pasted
        current_x = _get_row_start_x(row_width, config)

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
            current_x -= word_width + config.word_spacing

        draw_y += max_row_height + config.row_spacing

    return page_image


def _get_translation_layout(
    translation: str,
    max_width: int,
    padding: int,
) -> tuple[list[str], ImageFont.ImageFont | None]:
    """Calculates the layout for a translation string and returns lines and font."""
    try:
        # Load a modern sans-serif font for translations
        translation_font = ImageFont.truetype("./assets/inter.ttf", 36)
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)

        # Use balanced wrapping for better aesthetic
        lines = _wrap_text_balanced(draw, translation, translation_font, max_width - 2 * padding)
        return lines, translation_font
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to calculate translation layout: {e}")
        return [], None


def _draw_translation(
    image: Image.Image,
    lines: list[str],
    font: ImageFont.ImageFont,
    config: LayoutConfig,
):
    """
    Draws translation lines onto the bottom of an image with a fixed starting Y.
    Uses 'mt' anchor to center each line horizontally.
    """
    if not lines or not font:
        return

    draw = ImageDraw.Draw(image)
    metrics = font.getmetrics()
    ascent, descent = metrics
    spacing = 10  # Vertical spacing between translation lines

    # Fixed starting Y position for the first line based on bottom reserved area
    current_y = config.image_height - config.padding - config.bottom_offset

    for line in lines:
        draw.text(
            (config.max_width // 2, current_y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            anchor="mt",
        )
        current_y += ascent + descent + spacing


def frame(
    words: list[Image.Image],
    words_text: list[str] | None = None,
    verse_translations: list[str] | list[list[str]] | None = None,
    max_rows_per_page: int = 5,
    max_width: int = 1920,
    image_height: int = 1080,
    padding: int = 50,
    word_spacing: int = 20,
    row_spacing: int = 30,
    translation_height: int = 300,
    verse_vertical_align: str = "center",
    verse_horizontal_align: str = "center",
    verse_v_offset: int = 0,
) -> list[Image.Image]:
    """
    Manages the 2D grid layout of word images into one or more pages.
    Supports right-to-left layout and bottom-aligned translations.
    """
    if not words:
        return []

    config = LayoutConfig(
        max_width=max_width,
        image_height=image_height,
        padding=padding,
        word_spacing=word_spacing,
        row_spacing=row_spacing,
        max_rows_per_page=max_rows_per_page,
        bottom_offset=translation_height,
        verse_vertical_align=verse_vertical_align,
        verse_horizontal_align=verse_horizontal_align,
        verse_v_offset=verse_v_offset,
    )

    all_items = _normalize_items(words, words_text)
    images: list[Image.Image] = []
    flat_translations = verse_translations or []

    page_index = 0
    while all_items:
        current_translation = flat_translations[page_index] if page_index < len(flat_translations) else None

        trans_lines, trans_font = [], None
        if current_translation:
            trans_lines, trans_font = _get_translation_layout(current_translation, config.max_width, config.padding)

        # Plan the rows for this page
        current_rows, items_consumed = _group_items_into_rows(all_items, config)

        # Adjust page break to end at a stop sign if possible
        if words_text and items_consumed < len(all_items):
            current_rows, items_consumed = _apply_stop_sign_adjustment(current_rows, items_consumed)

        # Render the verse content
        page_image = _render_page(current_rows, config)

        # Draw the translation if present
        if trans_lines:
            _draw_translation(page_image, trans_lines, trans_font, config)

        images.append(page_image)
        all_items = all_items[items_consumed:]
        page_index += 1

    return images
