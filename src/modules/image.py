from PIL import Image, ImageChops


def color(image: Image.Image, color: tuple[int, int, int, int] = (255, 255, 255, 255)) -> Image.Image:
    """Multiplies the luminance of each pixel with the color.

    Alpha is multiplied by the color's alpha. Does not copy image by default.

    Args:
        image: The input PIL Image.
        color: The RGBA color to multiply with.

    Returns:
        The colorized PIL Image.
    """
    return ImageChops.multiply(image.convert("LA").convert("RGBA"), Image.new("RGBA", image.size, color))


def pad(image: Image.Image, padding: tuple[int, int, int, int] = (20, 20, 20, 20), color: tuple[int, int, int, int] = (0, 0, 0, 0)) -> Image.Image:
    """Pads an image with a given color and padding.

    Args:
        image: The input PIL Image.
        padding: A tuple of (top, bottom, left, right) padding values.
        color: The RGBA color for the padded area.

    Returns:
        The padded PIL Image.
    """
    new_width = image.width + padding[2] + padding[3]
    new_height = image.height + padding[0] + padding[1]
    padded_image = Image.new("RGBA", (new_width, new_height), color=color)
    padded_image.paste(image, (padding[2], padding[0]))
    return padded_image


if __name__ == "__main__":
    # Test color_image function
    test_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
    colored_image = color(test_image.copy())
    with open("./output/test/colored_image.png", "wb") as f:
        colored_image.save(f)

    # Test pad function
    padded_image = pad(test_image.copy())
    with open("./output/test/padded_image.png", "wb") as f:
        padded_image.save(f)
