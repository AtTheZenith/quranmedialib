import os

from quranmedialib import LANDSCAPE_PRESET
from quranmedialib.modules.verse_number import logger, verse_number


def test_verse_number():
    print("\nRunning test_verse_number...")
    test_number = 286
    logger.info(f"Generating ayah number {test_number} using Unicode symbol...")

    # Test default padding (10, 10, 10, 10)
    img_default = verse_number(test_number, LANDSCAPE_PRESET["default"]["1080p"][2])
    logger.info(f"Default padding size: {img_default.size}")

    output_dir = "./output/test/verse_number"
    os.makedirs(output_dir, exist_ok=True)

    img_default.save(os.path.join(output_dir, f"{test_number:03d}_default.png"))

    logger.info(f"Test generation complete. Saved to {output_dir}")
    print("test_verse_number completed successfully.")


if __name__ == "__main__":
    test_verse_number()
