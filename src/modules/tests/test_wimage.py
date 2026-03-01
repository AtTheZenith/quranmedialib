import os
from src.modules.wimage import get_wimage, db


def test_wimage():
    print("\nRunning test_wimage...")
    surah = 2
    words = db.fetch_all_words_from_surah(surah)
    output_dir = "./output/test/"
    os.makedirs(output_dir, exist_ok=True)

    print("Processing 20 words...")
    for i in range(20):
        img = get_wimage(words[i])
        img.save(f"{output_dir}/wimage_{i + 1}.png")
    print("Done.")
    print("test_wimage completed successfully.")


if __name__ == "__main__":
    test_wimage()
    db.close()
