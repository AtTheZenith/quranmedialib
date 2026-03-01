import os
from PIL import Image
from src.modules.image import color, pad, glow


def _save_test_image(img: Image.Image, filename: str):
    output_dir = "./output/test/"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
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


def test_glow():
    print("Testing glow function...")
    # Transparent background with a white circle
    test_image = Image.new("RGBA", (200, 200), color=(0, 0, 0, 0))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(test_image)
    draw.ellipse([50, 50, 150, 150], fill=(255, 255, 255, 255))

    glowed_image = glow(test_image, strength=1.5, radius=30)
    _save_test_image(glowed_image, "glowed_image_rgba.png")

    # RGB test case (white circle on dark grey background)
    test_image_rgb = Image.new("RGB", (200, 200), color=(30, 30, 30))
    draw_rgb = ImageDraw.Draw(test_image_rgb)
    draw_rgb.ellipse([70, 70, 130, 130], fill=(255, 255, 255))
    glowed_image_rgb = glow(test_image_rgb, strength=1.5, radius=30)
    _save_test_image(glowed_image_rgb, "glowed_image_rgb.png")

    # Opaque RGBA test case (RGBA with all alpha=255)
    test_image_opaque = Image.new("RGBA", (200, 200), color=(30, 30, 30, 255))
    draw_opaque = ImageDraw.Draw(test_image_opaque)
    draw_opaque.ellipse([70, 70, 130, 130], fill=(0, 255, 0, 255))
    glowed_image_opaque = glow(test_image_opaque, strength=1.5, radius=30)
    _save_test_image(glowed_image_opaque, "glowed_image_opaque_rgba.png")

    print("test_glow passed.")


def test_image():
    print("\nRunning test_image...")
    test_color()
    test_pad()
    test_glow()
    print("test_image completed successfully.")


if __name__ == "__main__":
    test_image()
