from src.modules.annotate_word import annotate_word
from src.modules.database_manager import DatabaseManager
from src.modules.framer import frame
from src.modules.image import color, glow
from src.modules.verse_number import verse_number
from src.modules.wimage import get_wimage


def main():
    db = DatabaseManager()
    surah = 10
    verse = 65
    words = db.fetch_all_words_from_verse(surah, verse)
    word_images = [get_wimage(word) for word in words]
    annotated_images = [annotate_word(image, surah, verse, i + 1) for i, image in enumerate(word_images)]
    db.close()

    annotated_images.append(verse_number(verse, font_size=110, padding=(1, 71, 1, 1)))
    annotated_images[1] = color(annotated_images[1], (255, 0, 0))
    final_images = frame(annotated_images, words)
    final_images = [glow(image, strength=1.5, radius=30) for image in final_images]
    for i, image in enumerate(final_images):
        image.save(f"output/test/main_{i + 1}.png")
        print(f"Saved {i + 1}/{len(final_images)} images")


if __name__ == "__main__":
    main()
