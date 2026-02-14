"""
This is a function that takes a list of images from either word_to_image.py or word_by_word.py.
It will manage the 2D grid needed to create the image, based on constraints in row number and width.
If there are too many words to fit in one image, it will overflow into another image that the function will manage.
It should always return a list of images.
"""

from PIL import Image


def convert_words_to_verses(words: list[Image.Image], row_num=5, max_width=1920, image_height=1080):
    """
    Takes a list of words in image form, then manages the 2D grid needed to create the image, based on constraints in row number and width.
    If there are too many words to fit in one image, it will overflow into another image that the function will manage.
    Returns: list[PIL.Image.Image]
    """
    if not words:
        return []

    images = []
    padding = 50
    word_spacing = 20
    row_spacing = 30

    # Group words into rows
    rows = []
    current_row = []
    current_row_width = 0

    for word in words:
        ww, wh = word.size
        # If adding this word exceeds max_width (considering padding and spacing)
        if current_row_width + ww + (word_spacing if current_row else 0) > max_width - 2 * padding:
            if current_row:
                rows.append(current_row)
            current_row = [word]
            current_row_width = ww
        else:
            current_row_width += ww + (word_spacing if current_row else 0)
            current_row.append(word)

    if current_row:
        rows.append(current_row)

    # Distribute rows into images
    current_image = None
    current_y = padding
    current_row_count = 0

    for row in rows:
        max_row_height = max(word.size[1] for word in row)

        # Check if we need a new image: row count reached OR height exceeded
        if current_image is None or current_row_count >= row_num or (current_y + max_row_height + padding > image_height):
            current_image = Image.new("RGBA", (max_width, image_height), color=(0, 0, 0, 0))
            images.append(current_image)
            current_y = padding
            current_row_count = 0

        # Draw row RTL
        current_x = max_width - padding
        for word in row:
            ww, wh = word.size
            # Vertically center word in row
            word_y = current_y + (max_row_height - wh) // 2
            # Place word from right
            current_image.paste(word, (current_x - ww, word_y), mask=word if word.mode == "RGBA" else None)
            current_x -= ww + word_spacing

        current_y += max_row_height + row_spacing
        current_row_count += 1

    return images


if __name__ == "__main__":
    import os

    from database_manager import DatabaseManager
    from word_to_image import convert_word_to_image
    from word_by_word import annotate_word_with_translation

    db = DatabaseManager()
    # Ayatul Kursi (2:255)
    words_text = db.fetch_all_words_from_verse(2, 255)
    print(f"Converting {len(words_text)} words to images...")
    word_images = [convert_word_to_image(w) for w in words_text]

    print("Annotating words with translations...")
    word_wbw_images = []
    for i in range(0, len(word_images)):
        word_wbw_images.append(annotate_word_with_translation(word_images[i], 2, 255, i + 1))

    print("Arranging words into verses...")
    images = convert_words_to_verses(word_wbw_images)

    output_dir = "./ayat/new/words/test/"
    os.makedirs(output_dir, exist_ok=True)

    for i, image in enumerate(images):
        save_path = f"{output_dir}/word_to_verse_{i + 1}.png"
        image.save(save_path)
        print(f"Saved: {save_path}")
