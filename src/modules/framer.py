"""
Framer module for laying out word images into pages with translation support.
"""

from __future__ import annotations

import itertools
import logging
from PIL import Image, ImageDraw, ImageFont

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


def _group_items_into_rows(
    all_items: list[tuple[Image.Image, str | None]],
    max_width: int,
    image_height: int,
    padding: int,
    word_spacing: int,
    row_spacing: int,
    max_rows_per_page: int,
    bottom_offset: int = 0,
) -> tuple[list[list[tuple[Image.Image, str | None]]], int]:
    """Groups items into rows for a single page with a reserved bottom area."""
    current_image_rows = []
    current_y = padding
    items_consumed = 0

    while items_consumed < len(all_items) and len(current_image_rows) < max_rows_per_page:
        row_items = []
        current_row_width = 0
        row_consumed = 0

        for item_index in range(items_consumed, len(all_items)):
            word_image, _ = all_items[item_index]
            word_width, _ = word_image.size

            if current_row_width + word_width + (word_spacing if row_items else 0) > max_width - 2 * padding:
                if not row_items:
                    row_items.append(all_items[item_index])
                    row_consumed += 1
                break

            current_row_width += word_width + (word_spacing if row_items else 0)
            row_items.append(all_items[item_index])
            row_consumed += 1

        if not row_items:
            break

        max_row_height = max(item[0].size[1] for item in row_items)
        if current_y + max_row_height + padding + bottom_offset > image_height:
            if not current_image_rows:
                current_image_rows.append(row_items)
                items_consumed += row_consumed
            break

        current_image_rows.append(row_items)
        items_consumed += row_consumed
        current_y += max_row_height + row_spacing

    return current_image_rows, items_consumed


def _apply_stop_sign_adjustment(
    current_image_rows: list[list[tuple[Image.Image, str | None]]],
    items_consumed: int,
) -> tuple[list[list[tuple[Image.Image, str | None]]], int]:
    """Adjusts page breaks to align with Quranic stop signs."""
    row_lengths = [len(row) for row in current_image_rows]
    prefix_sums = [0] + list(itertools.accumulate(row_lengths))

    for row_index in range(len(current_image_rows) - 1, -1, -1):
        row = current_image_rows[row_index]
        for word_index in range(len(row) - 1, -1, -1):
            _, text = row[word_index]
            if text and any(sign in text for sign in QURANIC_STOP_SIGNS):
                keep_count = prefix_sums[row_index] + word_index + 1
                if keep_count < items_consumed:
                    adjusted_rows = current_image_rows[: row_index + 1]
                    adjusted_rows[-1] = adjusted_rows[-1][: word_index + 1]
                    return adjusted_rows, keep_count
    return current_image_rows, items_consumed


def _wrap_text_balanced(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Wraps text into lines such that the line widths are as balanced as possible."""
    words = text.split()
    if not words:
        return []

    def get_lines(target_width: int) -> list[str]:
        res_lines = []
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= target_width:
                current_line.append(word)
            else:
                if current_line:
                    res_lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    res_lines.append(word)
                    current_line = []
        if current_line:
            res_lines.append(" ".join(current_line))
        return res_lines

    greedy_lines = get_lines(max_width)
    target_num_lines = len(greedy_lines)

    if target_num_lines <= 1:
        return greedy_lines

    low = max(draw.textbbox((0, 0), w, font=font)[2] - draw.textbbox((0, 0), w, font=font)[0] for w in words)
    high = max_width
    best_lines = greedy_lines

    while low <= high:
        mid = (low + high) // 2
        lines = get_lines(mid)
        if len(lines) <= target_num_lines:
            best_lines = lines
            high = mid - 1
        else:
            low = mid + 1

    return best_lines


def _render_page(
    rows: list[list[tuple[Image.Image, str | None]]],
    max_width: int,
    image_height: int,
    padding: int,
    word_spacing: int,
    row_spacing: int,
    verse_vertical_align: str = "center",
    verse_horizontal_align: str = "center",
    verse_v_offset: int = 0,
    bottom_offset: int = 0,
) -> Image.Image:
    """Renders a single page of rows into an RGBA image."""
    page_image = Image.new("RGBA", (max_width, image_height), color=(0, 0, 0, 0))

    row_heights = [max(item[0].size[1] for item in row) for row in rows]
    total_verse_height = sum(row_heights) + (len(rows) - 1) * row_spacing if rows else 0
    available_height = image_height - 2 * padding - bottom_offset

    if verse_vertical_align == "center" and total_verse_height < available_height:
        draw_y = padding + (available_height - total_verse_height) // 2 + verse_v_offset
    else:
        draw_y = padding + verse_v_offset

    for i, row in enumerate(rows):
        max_row_height = row_heights[i]

        row_width = sum(item[0].size[0] for item in row) + (len(row) - 1) * word_spacing
        available_width = max_width - 2 * padding

        if verse_horizontal_align == "center" and row_width < available_width:
            current_x = padding + (available_width - row_width) // 2 + row_width
        else:
            current_x = max_width - padding

        for word_image, _ in row:
            word_width, word_height = word_image.size
            word_y = draw_y + (max_row_height - word_height) // 2
            page_image.paste(
                word_image,
                (current_x - word_width, word_y),
                mask=word_image if word_image.mode == "RGBA" else None,
            )
            current_x -= word_width + word_spacing
        draw_y += max_row_height + row_spacing

    return page_image


def _get_translation_layout(
    translation: str,
    max_width: int,
    padding: int,
) -> tuple[list[str], int, ImageFont.ImageFont]:
    """Calculates the layout for a translation string and returns lines and metrics."""
    try:
        translation_font = ImageFont.truetype("./assets/inter.ttf", 36)
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)

        lines = _wrap_text_balanced(draw, translation, translation_font, max_width - 2 * padding)
        return lines, 0, translation_font
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to calculate translation layout: {e}")
        return [], 0, None


def _draw_translation(
    image: Image.Image,
    lines: list[str],
    font: ImageFont.ImageFont,
    max_width: int,
    image_height: int,
    padding: int,
    translation_height: int,
):
    """Draws translation lines onto the bottom of an image with a fixed starting Y."""
    if not lines or not font:
        return

    try:
        draw = ImageDraw.Draw(image)
        metrics = font.getmetrics()
        ascent, descent = metrics
        spacing = 10

        # Fixed starting Y position for the first line based on translation_height
        current_y = image_height - padding - translation_height

        for line in lines:
            draw.text(
                (max_width // 2, current_y),
                line,
                font=font,
                fill=(255, 255, 255, 255),
                anchor="mt",
            )
            current_y += ascent + descent + spacing
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to render translation: {e}")


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
    """Manages the 2D grid layout of word images with fixed-start translations."""
    if not words:
        return []

    all_items = _normalize_items(words, words_text)
    images: list[Image.Image] = []
    flat_translations = verse_translations or []

    page_index = 0
    while all_items:
        current_translation = flat_translations[page_index] if page_index < len(flat_translations) else None
        trans_lines, _, trans_font = [], 0, None
        if current_translation:
            trans_lines, _, trans_font = _get_translation_layout(current_translation, max_width, padding)

        # Reserve fixed space for all pages to ensure consistent starting Y.
        current_rows, items_consumed = _group_items_into_rows(
            all_items,
            max_width,
            image_height,
            padding,
            word_spacing,
            row_spacing,
            max_rows_per_page,
            bottom_offset=translation_height,
        )

        if words_text and items_consumed < len(all_items):
            current_rows, items_consumed = _apply_stop_sign_adjustment(current_rows, items_consumed)

        page_image = _render_page(
            current_rows,
            max_width,
            image_height,
            padding,
            word_spacing,
            row_spacing,
            verse_vertical_align=verse_vertical_align,
            verse_horizontal_align=verse_horizontal_align,
            verse_v_offset=verse_v_offset,
            bottom_offset=translation_height,
        )

        if trans_lines:
            _draw_translation(page_image, trans_lines, trans_font, max_width, image_height, padding, translation_height)

        images.append(page_image)
        all_items = all_items[items_consumed:]
        page_index += 1

    return images
