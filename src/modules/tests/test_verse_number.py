import os
from src.modules.verse_number import verse_number, logger


def test_verse_number():
    print("\nRunning test_verse_number...")
    test_number = 286
    logger.info(f"Generating ayah number {test_number} using Unicode symbol...")

    # Test default padding (10, 10, 10, 10)
    img_default = verse_number(test_number)
    logger.info(f"Default padding size: {img_default.size}")

    # Test custom padding (top=50, right=20, bottom=10, left=100)
    custom_padding = (50, 20, 10, 100)
    img_custom = verse_number(test_number, padding=custom_padding)
    logger.info(f"Custom padding {custom_padding} size: {img_custom.size}")

    output_dir = "./output/test/"
    os.makedirs(output_dir, exist_ok=True)

    img_default.save(os.path.join(output_dir, f"verse_number_{test_number:03d}_default.png"))
    img_custom.save(os.path.join(output_dir, f"verse_number_{test_number:03d}_custom.png"))

    logger.info(f"Test generation complete. Saved to {output_dir}")
    print("test_verse_number completed successfully.")


if __name__ == "__main__":
    test_verse_number()
