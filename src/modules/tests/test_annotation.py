import os

from src.modules.annotation import annotate_word, annotate_words, db
from src.modules.presets import LANDSCAPE_PRESET
from src.modules.wimage import get_wimage


def test_annotate_word():

    print("\nRunning test_annotate_word...")
    surah = 1
    ayah = 1
    word_idx = 1  # "Bism"

    # 1. Fetch Arabic word and convert to image
    arabic_words = db.get_verse(surah, ayah).split()
    arabic_text = arabic_words[word_idx - 1]
    arabic_img = get_wimage(arabic_text, LANDSCAPE_PRESET["default"]["1080p"][2])

    # 2. Annotate with translation
    annotated_img = annotate_word(arabic_img, surah, ayah, word_idx, db=db, word_config=LANDSCAPE_PRESET["default"]["1080p"][2])

    # 3. Save result
    output_dir = "./output/test/annotation"
    os.makedirs(output_dir, exist_ok=True)
    save_path = f"{output_dir}/word.png"
    annotated_img.save(save_path)

    print(f"Annotated image saved to: {save_path}")
    print(f"Arabic: {arabic_text}")
    print(f"Translation: {db.get_wbw_from_word(surah, ayah, word_idx)}")

    print("test_annotate_word completed successfully.")


def _test_set(surah, ayah, word_range, word_config):
    # Fetch all words
    verse_text = db.get_verse(surah, ayah)
    words = verse_text.split()
    word_images = [get_wimage(w, word_config) for w in words]

    # Test batching - slice images to match the requested range
    # word_range is 1-indexed [start, end]
    start_idx = word_range[0]
    end_idx = word_range[1]
    sliced_images = word_images[start_idx - 1 : end_idx]

    annotated_images = annotate_words(sliced_images, surah, ayah, start=start_idx, word_config=word_config)

    print(f"Number of annotated images returned: {len(annotated_images)}")
    return annotated_images


def test_annotate_words():
    print("\nRunning test_annotate_words...")

    output_dir = "./output/test/annotation"
    os.makedirs(output_dir, exist_ok=True)

    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]
    # 1. Non-batched words (Surah 1:1, Words 1 and 2)
    # in (the) name, (of) allah
    annotated_images = _test_set(1, 1, (1, 2), word_config)
    assert len(annotated_images) == 2, f"Expected 2 images, got {len(annotated_images)}"
    annotated_images[0].save(f"{output_dir}/non_batch_1.png")
    annotated_images[1].save(f"{output_dir}/non_batch_2.png")

    # 2. Batched words (Surah 11:89, Words 10 and 11)
    # Both are "(the) people of nuh"
    annotated_images = _test_set(11, 89, (10, 11), word_config)
    assert len(annotated_images) == 1, f"Expected 1 image due to batching, got {len(annotated_images)}"
    annotated_images[0].save(f"{output_dir}/batch_1.png")

    # 3. Batched words (Surah 11:113, Words 10-12)
    # All are "besides allah"
    annotated_images = _test_set(11, 113, (10, 12), word_config)
    assert len(annotated_images) == 1, f"Expected 1 image due to batching, got {len(annotated_images)}"
    annotated_images[0].save(f"{output_dir}/batch_2.png")

    print("test_annotate_words completed successfully.")


if __name__ == "__main__":
    try:
        test_annotate_word()
        test_annotate_words()
    finally:
        db.close()
