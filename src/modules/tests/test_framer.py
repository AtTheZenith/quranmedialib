import os
from src.modules.database_manager import DatabaseManager
from src.modules.wimage import get_wimage
from src.modules.annotate_word import annotate_word
from src.modules.verse_number import verse_number
from src.modules.framer import frame


def test_framer():
    print("\nRunning test_framer...")
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

    # database_manager.close() # Singleton might be closed elsewhere or needed by other tests
    print("test_framer completed successfully.")


if __name__ == "__main__":
    test_framer()
    DatabaseManager().close()
