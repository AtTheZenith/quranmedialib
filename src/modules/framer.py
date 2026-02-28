"""Module for framing words and verses into a 2D grid image.

This module manages the layout of multiple word images into rows and pages,
handling overflow based on width and row constraints, and optimizing
overflow points using Quranic stop signs.
"""

from __future__ import annotations
import itertools
from PIL import Image


QURANIC_STOP_SIGNS = ["ۖ", "ۗ", "ۘ", "ۙ", "ۚ", "ۛ", "ۜ"]


def _normalize_items(words: list[Image.Image], words_text: list[str] | None = None) -> list[tuple[Image.Image, str | None]]:
    """Normalizes and zips words and their corresponding text.

    Args:
        words: List of PIL Image objects.
        words_text: Optional list of strings.

    Returns:
        A list of tuples containing (image, text).
    """
    if words_text is not None:
        if len(words_text) < len(words):
            # Create a new list instead of in-place extension
            words_text = list(words_text) + [None] * (len(words) - len(words_text))
        return list(zip(words, words_text))

    return list(zip(words, [None] * len(words)))


def _group_items_into_rows(
    all_items: list[tuple[Image.Image, str | None]],
    max_width: int,
    image_height: int,
    padding: int,
    word_spacing: int,
    row_spacing: int,
    max_rows_per_page: int,
) -> tuple[list[list[tuple[Image.Image, str | None]]], int]:
    """Groups items into rows for a single page.

    Args:
        all_items: List of all remaining items to process.
        max_width: Maximum image width.
        image_height: Maximum image height.
        padding: Padding around the image.
        word_spacing: Spacing between words.
        row_spacing: Spacing between rows.
        row_num: Maximum rows per page.

    Returns:
        A tuple of (grouped rows, items consumed).
    """
    current_image_rows = []
    current_y = padding
    items_consumed = 0

    while items_consumed < len(all_items) and len(current_image_rows) < max_rows_per_page:
        row_items = []
        current_row_width = 0
        row_consumed = 0

        # Group items into a single row
        for item_index in range(items_consumed, len(all_items)):
            word_image, _ = all_items[item_index]
            word_width, _ = word_image.size

            if current_row_width + word_width + (word_spacing if row_items else 0) > max_width - 2 * padding:
                # If the first item of the row doesn't fit, force it to avoid infinite loops
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
        if current_y + max_row_height + padding > image_height:
            # If the very first row doesn't fit, force it to avoid infinite loops
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
    """Adjusts page breaks to align with Quranic stop signs.

    Args:
        current_image_rows: The rows grouped for the current page.
        items_consumed: The total number of items originally intended for this page.

    Returns:
        Adjusted (rows, items_consumed) based on stop signs.
    """
    row_lengths = [len(row) for row in current_image_rows]
    prefix_sums = [0] + list(itertools.accumulate(row_lengths))

    for row_index in range(len(current_image_rows) - 1, -1, -1):
        row = current_image_rows[row_index]
        for word_index in range(len(row) - 1, -1, -1):
            _, text = row[word_index]
            if text and any(sign in text for sign in QURANIC_STOP_SIGNS):
                # Calculate how many items we keep up to this stop sign
                keep_count = prefix_sums[row_index] + word_index + 1

                if keep_count < items_consumed:
                    adjusted_rows = current_image_rows[: row_index + 1]
                    adjusted_rows[-1] = adjusted_rows[-1][: word_index + 1]
                    return adjusted_rows, keep_count
    return current_image_rows, items_consumed


def _render_page(
    rows: list[list[tuple[Image.Image, str | None]]],
    max_width: int,
    image_height: int,
    padding: int,
    word_spacing: int,
    row_spacing: int,
) -> Image.Image:
    """Renders a single page of rows into an RGBA image.

    Args:
        rows: Rows of items to render.
        max_width: Image width.
        image_height: Image height.
        padding: Padding around the image.
        word_spacing: Spacing between words.
        row_spacing: Spacing between rows.

    Returns:
        A PIL Image object.
    """
    page_image = Image.new("RGBA", (max_width, image_height), color=(0, 0, 0, 0))
    draw_y = padding

    for row in rows:
        max_row_height = max(item[0].size[1] for item in row)
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


def frame(
    words: list[Image.Image],
    words_text: list[str] = None,
    max_rows_per_page: int = 5,
    max_width: int = 1920,
    image_height: int = 1080,
    padding: int = 50,
    word_spacing: int = 20,
    row_spacing: int = 30,
) -> list[Image.Image]:
    """Manages the 2D grid layout of word images with overflow handling.

    Takes a list of words in image form and arranges them into rows and pages
    based on the specified width and height constraints.

    Args:
        words: A list of PIL Image objects for each word.
        words_text: Optional list of strings corresponding to the words for stop-sign logic.
        row_num: Maximum number of rows per image.
        max_width: Maximum width of the generated images.
        image_height: Height of the generated images.
        padding: Padding around the image.
        word_spacing: Spacing between words.
        row_spacing: Spacing between rows.

    Returns:
        A list of PIL Image objects representing the pages of framed words.
    """
    if not words:
        return []

    all_items = _normalize_items(words, words_text)
    images: list[Image.Image] = []

    while all_items:
        # Step 1: Initial grouping (group)
        current_rows, items_consumed = _group_items_into_rows(
            all_items,
            max_width,
            image_height,
            padding,
            word_spacing,
            row_spacing,
            max_rows_per_page,
        )

        # Step 2: Stop-sign based overflow adjustment (adjust)
        if words_text and items_consumed < len(all_items):
            current_rows, items_consumed = _apply_stop_sign_adjustment(current_rows, items_consumed)

        # Step 3: Render the current page (render)
        images.append(
            _render_page(
                current_rows,
                max_width,
                image_height,
                padding,
                word_spacing,
                row_spacing,
            )
        )

        # Advance
        all_items = all_items[items_consumed:]

    return images


def main():
    import os

    from src.modules.database_manager import DatabaseManager
    from src.modules.wimage import get_wimage
    from src.modules.annotate_word import annotate_word
    from src.modules.verse_number import verse_number

    database_manager = DatabaseManager()
    # Ayatul Kursi (2:255)
    words_text = database_manager.fetch_all_words_from_verse(2, 255)
    print(f"Converting {len(words_text)} words to images...")
    word_images = [get_wimage(word_text) for word_text in words_text]

    print("Annotating words with translations...")
    word_wbw_images = []
    word_wbw_images.extend(annotate_word(word_images[index], 2, 255, index + 1) for index in range(len(word_images)))
    print("Arranging words into verses with stop-sign overflow...")
    word_wbw_images.append(verse_number(255, padding=(0, 42, 0, 0)))
    images = frame(word_wbw_images, words_text=words_text)

    output_dir = "./output/test/"
    os.makedirs(output_dir, exist_ok=True)

    for i, image in enumerate(images):
        save_path = f"{output_dir}/framer_{i + 1}.png"
        image.save(save_path)
        print(f"Saved: {save_path}")

    database_manager.close()


if __name__ == "__main__":
    main()
