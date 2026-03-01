from PIL import Image
from src.modules.image import color, pad


def _save_test_image(img: Image.Image, filename: str):
    output_path = f"./output/test/{filename}"
    img.save(output_path)
    print(f"Saved image to {output_path}")


def test_color():
    print("Testing color function...")
    test_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
    colored_image = color(test_image.copy())
    _save_test_image(colored_image, "colored_image.png")
    print("test_color passed.")


def test_pad():
    print("Testing pad function...")
    test_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
    padded_image = pad(test_image.copy())
    _save_test_image(padded_image, "padded_image.png")
    print("test_pad passed.")


def test_image():
    print("\nRunning test_image...")
    test_color()
    test_pad()
    print("test_image completed successfully.")


if __name__ == "__main__":
    test_image()
