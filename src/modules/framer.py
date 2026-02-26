"""Module for framing words and verses into a 2D grid image.

This module manages the layout of multiple word images into rows and pages,
handling overflow based on width and row constraints, and optimizing
overflow points using Quranic stop signs.
"""

from PIL import Image


QURANIC_STOP_SIGNS = ["ۖ", "ۗ", "ۘ", "ۙ", "ۚ", "ۛ", "ۜ"]


def frame(
    words: list[Image.Image],
    words_text: list[str] = None,
    row_num: int = 5,
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

    Returns:
        A list of PIL Image objects representing the pages of framed words.
    """
    if not words:
        return []

    images: list[Image.Image] = []

    # Process all words into images
    if words_text and len(words_text) < len(words):
        words_text.extend([None] * (len(words) - len(words_text)))

    all_items = list(zip(words, words_text if words_text else [None] * len(words)))
    images = []

    while all_items:
        current_image_rows = []
        current_y = padding
        current_row_count = 0
        items_consumed = 0

        # Tentatively group rows for ONE image
        while items_consumed < len(all_items) and current_row_count < row_num:
            row_items = []
            current_row_width = 0
            row_consumed = 0

            # Group items into a single row
            for i in range(items_consumed, len(all_items)):
                word_img, _ = all_items[i]
                ww, wh = word_img.size

                if current_row_width + ww + (word_spacing if row_items else 0) > max_width - 2 * padding:
                    break

                current_row_width += ww + (word_spacing if row_items else 0)
                row_items.append(all_items[i])
                row_consumed += 1

            if not row_items:
                break

            max_row_height = max(item[0].size[1] for item in row_items)
            if current_y + max_row_height + padding > image_height:
                break

            current_image_rows.append(row_items)
            items_consumed += row_consumed
            current_y += max_row_height + row_spacing
            current_row_count += 1

        # Third Method: Stop-sign based overflow adjustment
        if words_text and items_consumed < len(all_items):
            # Scan backwards from the end of the last row to find a stop sign
            found_stop_sign = False
            for r_idx in range(len(current_image_rows) - 1, -1, -1):
                row = current_image_rows[r_idx]
                for w_idx in range(len(row) - 1, -1, -1):
                    _, text = row[w_idx]
                    if text and any(sign in text for sign in QURANIC_STOP_SIGNS):
                        # Found it! Adjust consumption point
                        # Everything after this word in this row, and all subsequent rows, move back to all_items

                        # Count how many items to keep
                        keep_count = 0
                        for i in range(r_idx):
                            keep_count += len(current_image_rows[i])
                        keep_count += w_idx + 1  # +1 to include the word with the stop sign

                        # If we aren't keeping ALL items (which would mean no change)
                        if keep_count < items_consumed:
                            items_consumed = keep_count
                            current_image_rows = current_image_rows[: r_idx + 1]
                            current_image_rows[-1] = current_image_rows[-1][: w_idx + 1]
                            found_stop_sign = True
                            break
                if found_stop_sign:
                    break

        # Draw the image
        img = Image.new("RGBA", (max_width, image_height), color=(0, 0, 0, 0))
        images.append(img)
        draw_y = padding

        for row in current_image_rows:
            max_h = max(item[0].size[1] for item in row)
            current_x = max_width - padding
            for word_img, _ in row:
                ww, wh = word_img.size
                word_y = draw_y + (max_h - wh) // 2
                img.paste(word_img, (current_x - ww, word_y), mask=word_img if word_img.mode == "RGBA" else None)
                current_x -= ww + word_spacing
            draw_y += max_h + row_spacing

        all_items = all_items[items_consumed:]

    return images


if __name__ == "__main__":
    import os

    from database_manager import DatabaseManager
    import wimage
    import annotate_word
    from verse_number import verse_number

    db = DatabaseManager()
    # Ayatul Kursi (2:255)
    words_text = db.fetch_all_words_from_verse(2, 255)
    print(f"Converting {len(words_text)} words to images...")
    word_images = [wimage.get_wimage(w) for w in words_text]

    print("Annotating words with translations...")
    word_wbw_images = []
    for i in range(0, len(word_images)):
        word_wbw_images.append(annotate_word.annotate_word(word_images[i], 2, 255, i + 1))

    print("Arranging words into verses with stop-sign overflow...")
    word_wbw_images.append(verse_number(255, padding=(0, 42, 0, 0)))
    images = frame(word_wbw_images, words_text=words_text)

    output_dir = "./ayat/new/words/test/"
    os.makedirs(output_dir, exist_ok=True)

    for i, image in enumerate(images):
        save_path = f"{output_dir}/word_to_verse_{i + 1}.png"
        image.save(save_path)
        print(f"Saved: {save_path}")
