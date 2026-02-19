# ./assets/en_sahih.db
# table structure:
# "surah","ayah","word","translation"
# (INTEGER, INTEGER, INTEGER, TEXT) where the fourth column is the translation of the corresponding arabic word in corpus.db
# fetch by word only, it is used in parallel with fetch by word from corpus.db (to annotate words with translations)

from PIL import Image, ImageDraw, ImageFont

import database_manager

db = database_manager.DatabaseManager()


def annotate_with_translation(image, surah, ayah, word_index, translation_font_size=28, color=(255, 255, 255, 255)):
    """
    Annotates a word (as given in image) with its translation.
    Creates a new image with the translation drawn below the original image.
    Uses baseline alignment for the translation text to ensure consistency.
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
    padding = 10
    total_w = max(iw, tw + padding * 2)
    # The Arabic word sits at the top, followed by padding, then the translation box
    total_h = ih + padding + th + padding

    # Create new image
    new_img = Image.new("RGBA", (total_w, total_h), color=(0, 0, 0, 0))

    # Paste original Arabic word (centered horizontally)
    # The Arabic image already has its own internal padding from word_to_image.py
    new_img.paste(image, ((total_w - iw) // 2, 0))

    # Draw translation text (centered horizontally below the Arabic word)
    draw = ImageDraw.Draw(new_img)
    tx = (total_w - tw) // 2 - bbox[0]
    # Baseline for translation: Arabic image height + padding + font's ascent
    ty = ih + padding + ascent
    draw.text((tx, ty), translation, font=font, fill=color, anchor="ls")

    return new_img


if __name__ == "__main__":
    import word_to_image
    import os

    surah = 1
    ayah = 1
    word_idx = 1  # "Bismillah"

    # 1. Fetch Arabic word and convert to image
    arabic_words = db.fetch_all_words_from_verse(surah, ayah)
    arabic_text = arabic_words[word_idx - 1]
    arabic_img = word_to_image.convert_word_to_image(arabic_text)

    # 2. Annotate with translation
    annotated_img = annotate_with_translation(arabic_img, surah, ayah, word_idx)

    # 3. Save result
    output_dir = "./ayat/new/words/test/"
    os.makedirs(output_dir, exist_ok=True)
    save_path = f"{output_dir}/word_by_word.png"
    annotated_img.save(save_path)

    print(f"Annotated image saved to: {save_path}")
    print(f"Arabic: {arabic_text}")
    print(f"Translation: {db.fetch_translation_for_word(surah, ayah, word_idx)}")
