from src.modules.annotation import annotate_word
from src.modules.database_manager import DatabaseManager
from src.modules.framer import frame
from src.modules.image import color, glow
from src.modules.presets import LANDSCAPE_PRESET
from src.modules.timage import get_timage
from src.modules.verse_number import verse_number
from src.modules.wimage import get_wimage


def main():
    db = DatabaseManager()
    surah = 10
    verse = 65
    words = db.get_verse(surah, verse).split()
    translation = db.get_translation_from_verse(surah, verse)

    # Use a preset for layout and text configuration
    config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    word_images = [get_wimage(word) for word in words]
    annotated_images = [annotate_word(image, surah, verse, i + 1) for i, image in enumerate(word_images)]
    db.close()

    annotated_images.append(
        verse_number(
            verse,
            font_size=word_config.verse_number_size,
            padding=word_config.verse_number_padding,
        )
    )
    annotated_images[1] = color(annotated_images[1], (255, 0, 0))

    translation = translation.replace("grieve you", "##ff0000ff#grieve you#")
    t_img = get_timage(translation, config.content_width, config=text_config)
    final_images = frame(annotated_images, words, translation_images=[t_img], config=config, word_config=word_config)

    final_images = [glow(image, strength=1.5, radius=30) for image in final_images]
    output_dir = "output/demo"
    import os
    os.makedirs(output_dir, exist_ok=True)
    for i, image in enumerate(final_images):
        save_path = f"{output_dir}/{(i + 1):02d}.png"
        image.save(save_path)
        print(f"Saved {i + 1}/{len(final_images)} images: {save_path}")


if __name__ == "__main__":
    main()
