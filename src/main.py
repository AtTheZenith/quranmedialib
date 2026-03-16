from src.modules.annotation import annotate_word
from src.modules.database_manager import DatabaseManager
from src.modules.framer import LayoutConfig, frame
from src.modules.image import color, glow
from src.modules.timage import get_timage
from src.modules.verse_number import verse_number
from src.modules.wimage import get_wimage


def main():
    db = DatabaseManager()
    surah = 10
    verse = 65
    words = db.get_verse(surah, verse).split()
    translation = db.get_translation_from_verse(surah, verse)

    word_images = [get_wimage(word) for word in words]
    annotated_images = [annotate_word(image, surah, verse, i + 1) for i, image in enumerate(word_images)]
    db.close()

    annotated_images.append(verse_number(verse, font_size=110, padding=(1, 71, 1, 1)))
    annotated_images[1] = color(annotated_images[1], (255, 0, 0))

    # Pass translation to frame using LayoutConfig

    config = LayoutConfig(
        max_width=1920,
        image_height=1080,
        padding=50,
        word_spacing=20,
        row_spacing=30,
        max_rows_per_page=5,
        bottom_offset=300,
        balanced_wrapping=True,
    )

    translation = translation.replace("grieve you", "##ff0000ff#grieve you#")
    t_img = get_timage(translation, config.content_width)
    final_images = frame(annotated_images, words, translation_images=[t_img], config=config)

    final_images = [glow(image, strength=1.5, radius=30) for image in final_images]
    for i, image in enumerate(final_images):
        save_path = f"output/test/main_{i + 1}.png"
        image.save(save_path)
        print(f"Saved {i + 1}/{len(final_images)} images: {save_path}")


if __name__ == "__main__":
    main()
