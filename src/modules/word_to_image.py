# ./assets/corpus.db
# table structure:
# "surah","ayah","word","ar1","ar2","ar3","ar4","ar5","pos1","pos2","pos3","pos4","pos5","count","root_ar","lemma","verb_type","verf_form"
# concatenate ar1-ar5 to get the word
# font is ./assets/hafs.otf

"""
This is a function that will be used to convert words to images.
It will use the database manager to fetch words from the database.
It will use the pillow library to create images.
It can be imported to create workflows and to prevent large files, as this is a library monorepo.
"""

import os
from PIL import Image, ImageDraw, ImageFont
from database_manager import DatabaseManager

db = DatabaseManager()


def convert_word_to_image(text):
    """
    Converts a word string into an image using the hafs font.
    """

    font_path = "./assets/hafs.otf"
    font_size = 128
    font = ImageFont.truetype(font_path, font_size)

    # Calculate text dimensions for dynamic image sizing
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    # Create image with padding
    padding = 20
    img = Image.new(
        "RGBA",
        (w + padding * 2, h + padding * 2),
        color=(
            0,
            0,
            0,
        ),
    )
    draw = ImageDraw.Draw(img)

    # Draw text centered with respect to its bounding box
    draw.text((padding - bbox[0], padding - bbox[1]), text, font=font, fill=(255, 255, 255, 255))

    return img


if __name__ == "__main__":
    surah = 2
    words = db.fetch_all_words_from_surah(surah)
    output_dir = "./ayat/new/words/test/"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Processing {len(words)} words...")
    for i in range(0, len(words)):
        img = convert_word_to_image(words[i])
        img.save(f"{output_dir}/{i + 1}.png")
    print("Done.")
