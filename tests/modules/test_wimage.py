import os

from quranmedialib import LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.modules.wimage import get_wimage

db = DatabaseManager()


def test_wimage():
    print("\nRunning test_wimage...")
    surah = 2
    verses = db.get_verses_from_surah(surah)
    words = [word for verse in verses for word in verse.split() if word]
    output_dir = "./output/test/wimage"
    os.makedirs(output_dir, exist_ok=True)

    print("Processing word...")
    img = get_wimage(words[0], LANDSCAPE_PRESET["default"]["1080p"][2])
    img.save(f"{output_dir}/wimage.png")
    print("Done.")
    print("test_wimage completed successfully.")


if __name__ == "__main__":
    test_wimage()
    db.close()
