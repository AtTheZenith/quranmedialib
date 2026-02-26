# ./assets/en_sahih.db
# table structure:
# "surah","ayah","word","translation"
# (INTEGER, INTEGER, INTEGER, TEXT) where the fourth column is the translation of the corresponding arabic word in corpus.db
# fetch by word only, it is used in parallel with fetch by word from corpus.db (to annotate words with translations)

from PIL import Image, ImageDraw, ImageFont

import database_manager

db = database_manager.DatabaseManager()


def annotate_word(
    image: Image.Image,
    surah: int,
    ayah: int,
    word_index: int,
    translation_font_size: int = 28,
    color: tuple[int, int, int, int] = (255, 255, 255, 255),
    padding: tuple[int, int, int, int] = (0, 42, 0, 0),
) -> Image.Image:
    """Annotates a word image with its translation.

    Creates a new image with the translation drawn below the original image.
    Uses baseline alignment for the translation text to ensure consistency.

    Args:
        image: The input PIL Image of the Arabic word.
        surah: The surah number.
        ayah: The ayah number.
        word_index: The word index within the ayah.
        translation_font_size: Font size for the translation text.
        color: RGBA color for the translation text.
        padding: A tuple of (top, bottom, left, right) padding values.

    Returns:
        A new PIL Image containing the Arabic word and its translation.
    """
    translation = db.fetch_translation_for_word(surah, ayah, word_index)

    # Font settings for translation
    font_path = "./assets/inter.ttf"
    try:
        font = ImageFont.truetype(font_path, translation_font_size)
    except Exception:
        font = ImageFont.load_default()

    # Calculate translation dimensions and metrics
    ascent, descent = font.getmetrics()
    bbox = font.getbbox(translation)
    tw = bbox[2] - bbox[0]
    # Height is based on the font's maximum possible height to ensure consistency
    th = ascent + descent

    # Original image dimensions
    iw, ih = image.size

    # Padding and layout
    # padding is (top, bottom, left, right)
    total_w = max(iw, tw + padding[2] + padding[3])
    # The Arabic word sits at the top, followed by padding[0], then translation, then padding[1]
    total_h = ih + padding[0] + th + padding[1]

    # Create new image
    new_img = Image.new("RGBA", (total_w, total_h), color=(0, 0, 0, 0))

    # Paste original Arabic word (centered horizontally)
    # The Arabic image already has its own internal padding from word_to_image.py
    new_img.paste(image, ((total_w - iw) // 2, 0))

    # Draw translation text (centered horizontally below the Arabic word)
    draw = ImageDraw.Draw(new_img)
    tx = (total_w - tw) // 2 - bbox[0]
    # Baseline for translation: Arabic image height + top padding + font's ascent
    ty = ih + padding[0] + ascent
    draw.text((tx, ty), translation, font=font, fill=color, anchor="ls")

    return new_img


if __name__ == "__main__":
    import wimage
    import os

    surah = 1
    ayah = 1
    word_idx = 1  # "Bismillah"

    # 1. Fetch Arabic word and convert to image
    arabic_words = db.fetch_all_words_from_verse(surah, ayah)
    arabic_text = arabic_words[word_idx - 1]
    arabic_img = wimage.get_wimage(arabic_text)

    # 2. Annotate with translation
    # Using top=0, bottom=42 for compatibility with original design if that was the intent
    annotated_img = annotate_word(arabic_img, surah, ayah, word_idx, padding=(0, 42, 0, 0))

    # 3. Save result
    output_dir = "./ayat/new/words/test/"
    os.makedirs(output_dir, exist_ok=True)
    save_path = f"{output_dir}/word_by_word.png"
    annotated_img.save(save_path)

    print(f"Annotated image saved to: {save_path}")
    print(f"Arabic: {arabic_text}")
    print(f"Translation: {db.fetch_translation_for_word(surah, ayah, word_idx)}")
