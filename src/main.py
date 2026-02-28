from src.modules.database_manager import DatabaseManager
from src.modules.framer import frame
from src.modules.wimage import get_wimage
from src.modules.annotate_word import annotate_word
from src.modules.verse_number import verse_number


def main():
    db = DatabaseManager()
    surah = 10
    verse = 65
    words = db.fetch_all_words_from_verse(surah, verse)
    word_images = [get_wimage(word) for word in words]
    annotated_images = [annotate_word(image, surah, verse, i + 1) for i, image in enumerate(word_images)]
    annotated_images.append(verse_number(verse, font_size=110, padding=(1, 71, 1, 1)))
    final_images = frame(annotated_images, words)
    for i, image in enumerate(final_images):
        image.save(f"output/test/main_{i}.png")
        print(f"Saved {i + 1}/{len(final_images)} images")

    db.close()


if __name__ == "__main__":
    main()
