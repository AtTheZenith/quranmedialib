import os
from src.modules.annotate_word import annotate_word, db
from src.modules.wimage import get_wimage


def test_annotate_word():
    print("\nRunning test_annotate_word...")
    surah = 1
    ayah = 1
    word_idx = 1  # "Bismillah"

    # 1. Fetch Arabic word and convert to image
    arabic_words = db.fetch_all_words_from_verse(surah, ayah)

    # Simple bounds checking
    if not (1 <= word_idx <= len(arabic_words)):
        print(f"Error: word_index {word_idx} out of range for Surah {surah}, Ayah {ayah} (max {len(arabic_words)})")
        return

    arabic_text = arabic_words[word_idx - 1]
    arabic_img = get_wimage(arabic_text)

    # 2. Annotate with translation
    # Using top=0, bottom=42 for compatibility with original design if that was the intent
    annotated_img = annotate_word(arabic_img, surah, ayah, word_idx, padding=(0, 42, 0, 0))

    # 3. Save result
    output_dir = "./output/test/"
    os.makedirs(output_dir, exist_ok=True)
    save_path = f"{output_dir}/word_by_word.png"
    annotated_img.save(save_path)

    print(f"Annotated image saved to: {save_path}")
    print(f"Arabic: {arabic_text}")
    print(f"Translation: {db.fetch_translation_for_word(surah, ayah, word_idx)}")

    print("test_annotate_word completed successfully.")


if __name__ == "__main__":
    test_annotate_word()
    db.close()
