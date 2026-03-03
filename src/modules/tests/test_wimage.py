import os
from src.modules.wimage import get_wimage, db


def test_wimage():
    print("\nRunning test_wimage...")
    surah = 2
    verses = db.get_verses_from_surah(surah)
    words = [word for verse in verses for word in verse.split() if word]
    output_dir = "./output/test/"
    os.makedirs(output_dir, exist_ok=True)

    print("Processing word...")
    img = get_wimage(words[0])
    img.save(f"{output_dir}/wimage.png")
    print("Done.")
    print("test_wimage completed successfully.")


if __name__ == "__main__":
    test_wimage()
    db.close()
