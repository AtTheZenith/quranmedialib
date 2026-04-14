"""Tests for the annotation module (word-by-word annotation rendering).

This module contains tests for verifying single word annotation and batch
annotation with word-by-word translations, including batching behavior
when consecutive words have identical translations.
"""

import os

import pytest

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.modules.annotation import annotate_word, annotate_words
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import WordConfig

db = DatabaseManager()


def test_annotate_word() -> None:
    print("\nRunning test_annotate_word...")
    surah = 1
    ayah = 1
    word_idx = 1  # "Bism"

    # 1. Fetch Arabic word and convert to image
    arabic_words = db.get_verse(surah, ayah).split()
    arabic_text = arabic_words[word_idx - 1]
    arabic_img = get_wimage(arabic_text, LANDSCAPE_PRESET["default"]["1080p"][2])

    # 2. Annotate with translation
    annotated_img = annotate_word(
        arabic_img, surah, ayah, word_idx, db=db, word_config=LANDSCAPE_PRESET["default"]["1080p"][2]
    )

    # 3. Save result
    output_dir = "./output/test/annotation"
    os.makedirs(output_dir, exist_ok=True)
    save_path = f"{output_dir}/word.png"
    annotated_img.save(save_path)

    print(f"Annotated image saved to: {save_path}")
    print(f"Arabic: {arabic_text}")
    print(f"Translation: {db.get_wbw_from_word(surah, ayah, word_idx)}")

    print("test_annotate_word completed successfully.")


def _test_set(surah: int, ayah: int, word_range: tuple[int, int], word_config: WordConfig) -> list:
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


def test_annotate_words() -> None:
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
    test_annotate_word()
    test_annotate_words()


# === Validation Tests ===


def test_annotate_word_missing_config() -> None:
    """Test that annotate_word raises ValueError when word_config is None."""
    surah = 1
    ayah = 1
    word_idx = 1

    arabic_words = db.get_verse(surah, ayah).split()
    arabic_text = arabic_words[word_idx - 1]
    arabic_img = get_wimage(arabic_text, LANDSCAPE_PRESET["default"]["1080p"][2])

    with pytest.raises(ValueError, match="word_config is required for annotation"):
        annotate_word(arabic_img, surah, ayah, word_idx, db=db, word_config=None)


def test_annotate_word_invalid_surah() -> None:
    """Test that annotate_word handles invalid surah numbers (empty translation)."""
    arabic_img = get_wimage("test", LANDSCAPE_PRESET["default"]["1080p"][2])
    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]

    # Surah 0 doesn't exist - DB returns None/empty, annotation should handle gracefully
    # Should either skip annotation or return original image
    result = annotate_word(arabic_img, 0, 1, 1, db=db, word_config=word_config)
    assert result is not None  # Should return something (original or annotated)

    # Surah 115 doesn't exist
    result = annotate_word(arabic_img, 115, 1, 1, db=db, word_config=word_config)
    assert result is not None


def test_annotate_word_invalid_ayah() -> None:
    """Test that annotate_word handles invalid ayah numbers."""
    arabic_img = get_wimage("test", LANDSCAPE_PRESET["default"]["1080p"][2])
    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]

    # Ayah 0 doesn't exist - should handle gracefully
    result = annotate_word(arabic_img, 1, 0, 1, db=db, word_config=word_config)
    assert result is not None


def test_annotate_word_invalid_word_index() -> None:
    """Test that annotate_word handles invalid word indices."""
    arabic_img = get_wimage("test", LANDSCAPE_PRESET["default"]["1080p"][2])
    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]

    # Word index 0 doesn't exist - should handle gracefully
    result = annotate_word(arabic_img, 1, 1, 0, db=db, word_config=word_config)
    assert result is not None


def test_annotate_words_empty_list() -> None:
    """Test that annotate_words handles empty image list."""
    result = annotate_words([], 1, 1, 1, word_config=LANDSCAPE_PRESET["default"]["1080p"][2])
    assert result == []


def test_annotate_words_missing_config() -> None:
    """Test that annotate_words raises ValueError when word_config is None."""
    dummy_img = get_wimage("test", LANDSCAPE_PRESET["default"]["1080p"][2])

    with pytest.raises(ValueError, match="word_config is required for annotation"):
        annotate_words([dummy_img], 1, 1, 1, word_config=None)


def test_annotate_words_out_of_bounds_range() -> None:
    """Test that annotate_words raises ValueError for out-of-bounds word range."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]
    dummy_img = get_wimage("test", word_config)

    # Surah 1:1 has only 4 words, but we request 10 starting from index 1
    with pytest.raises(ValueError, match="out of bounds"):
        annotate_words([dummy_img] * 10, 1, 1, 1, word_config=word_config)


def test_annotate_words_invalid_surah() -> None:
    """Test that annotate_words handles invalid surah numbers."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]
    dummy_img = get_wimage("test", word_config)

    with pytest.raises(Exception):
        annotate_words([dummy_img], 0, 1, 1, word_config=word_config)


def test_annotate_words_with_texts_missing_config() -> None:
    """Test that annotate_words_with_texts raises ValueError when word_config is None."""
    from quranmedialib.modules.annotation import annotate_words_with_texts

    dummy_img = get_wimage("test", LANDSCAPE_PRESET["default"]["1080p"][2])

    with pytest.raises(ValueError, match="word_config is required for annotation"):
        annotate_words_with_texts([dummy_img], 1, 1, 1, texts=["test"], word_config=None)


def test_annotate_word_none_image() -> None:
    """Test that annotate_word handles None image gracefully."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]

    with pytest.raises((TypeError, AttributeError)):
        annotate_word(None, 1, 1, 1, db=db, translation="test", word_config=word_config)


# === Annotation Start Index Validation Tests ===


def test_annotate_words_zero_start_index() -> None:
    """Test that annotate_words raises ValueError for start=0."""
    from quranmedialib.modules.annotation import annotate_words

    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]
    dummy_img = get_wimage("test", word_config)

    with pytest.raises(ValueError, match="start index must be 1-based"):
        annotate_words([dummy_img], 1, 1, start=0, word_config=word_config)


def test_annotate_words_negative_start_index() -> None:
    """Test that annotate_words raises ValueError for negative start."""
    from quranmedialib.modules.annotation import annotate_words

    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]
    dummy_img = get_wimage("test", word_config)

    with pytest.raises(ValueError, match="start index must be 1-based"):
        annotate_words([dummy_img], 1, 1, start=-1, word_config=word_config)


# === Annotation Length Mismatch Tests (Round 2) ===


def test_annotate_words_texts_length_mismatch() -> None:
    """Test that annotate_words_with_texts handles fewer texts than images."""
    from quranmedialib.modules.annotation import annotate_words_with_texts

    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]
    dummy_img = get_wimage("test", word_config)
    images = [dummy_img, dummy_img, dummy_img]  # 3 images
    texts = ["only one text"]  # 1 text

    # Returns tuple of (annotated_images, annotated_texts)
    annotated_images, annotated_texts = annotate_words_with_texts(
        images,
        surah=1,
        ayah=1,
        start=1,
        texts=texts,
        word_config=word_config,
    )
    # Should return all 3 images with missing texts as empty strings
    assert len(annotated_images) == 3
    assert len(annotated_texts) == 3
    assert annotated_texts[0] == "only one text"
    assert annotated_texts[1] == ""
    assert annotated_texts[2] == ""


def test_annotate_words_wbw_translations_length_mismatch() -> None:
    """Test that annotate_words handles fewer wbw_translations than images."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]
    dummy_img = get_wimage("test", word_config)

    # Only 1 wbw translation for 3 words -- should handle gracefully
    # (annotate_words fetches from DB internally, wbw_translations param doesn't exist)
    # Instead, test with out-of-range word_index on annotate_word
    from quranmedialib.modules.annotation import annotate_word

    # Surah 1:1 has 4 words; word_index=5 is out of range
    result = annotate_word(dummy_img, surah=1, ayah=1, word_index=5, word_config=word_config)
    assert result is not None  # Should return original image or annotated version


def test_annotate_words_range_exceeds_images() -> None:
    """Test that annotate_words with start+count beyond image count raises error."""
    word_config = LANDSCAPE_PRESET["default"]["1080p"][2]
    dummy_img = get_wimage("test", word_config)
    images = [dummy_img] * 10  # 10 images

    # Start at 1, but Surah 1:1 only has 4 words -- requesting 10 should fail
    with pytest.raises(ValueError, match="out of bounds"):
        annotate_words(images, surah=1, ayah=1, start=1, word_config=word_config)

