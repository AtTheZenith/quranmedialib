import os
from PIL import Image, ImageDraw, ImageFont

# Hardcoded constants
FONT_PATH = "./assets/hafs.otf"

# Translation table for Arabic-Indic numerals
ARABIC_INDIC_TRANS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def verse_number(number, font_size=128, color=(255, 255, 255, 255), padding=(10, 10, 10, 10)):
    """
    Generates an image of the ayah symbol with the given number using Unicode.

    Args:
        number (int): The ayah number to draw.
        font_size (int): Font size for the Unicode symbol.
        color (tuple): RGBA color for the text.
        padding (tuple): (top, bottom, left, right) padding around the symbol.

    Returns:
        PIL.Image: The generated image.
    """
    try:
        symbol_font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception as e:
        print(f"Warning: Could not load font from {FONT_PATH}. Falling back to default. Error: {e}")
        symbol_font = ImageFont.load_default()

    # Convert number to Arabic-Indic numerals using translate
    number_str = str(number).translate(ARABIC_INDIC_TRANS)

    # Calculate bounding box for the symbol to determine image size
    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    symbol_bbox = dummy_draw.textbbox((0, 0), "١", font=symbol_font, anchor="mm")

    # symbol_bbox is (left, top, right, bottom) relative to (0,0)
    symbol_w = symbol_bbox[2] - symbol_bbox[0]
    symbol_h = symbol_bbox[3] - symbol_bbox[1]

    top, bottom, left, right = padding

    # Determine image size based on symbol size + individual padding
    w = symbol_w + left + right
    h = symbol_h + top + bottom

    # Create a blank transparent image
    img = Image.new("RGBA", (int(w), int(h)), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Calculate center position respecting top and left padding
    # anchor="mm" centers the text at the given coord.
    # We want the center of the symbol to be at:
    # x = left + symbol_w / 2
    # y = top + symbol_h / 2
    center_x = left + symbol_w / 2
    center_y = top + symbol_h / 2

    draw.text((center_x, center_y), number_str, font=symbol_font, fill=color, anchor="mm")

    return img


if __name__ == "__main__":
    # Test generation with a single integer
    test_number = 286
    print(f"Generating ayah number {test_number} using Unicode symbol...")

    # Test default padding (10, 10, 10, 10)
    img_default = verse_number(test_number)
    print(f"Default padding size: {img_default.size}")

    # Test uneven 4-tuple padding (top, bottom, left, right)
    custom_padding = (50, 10, 100, 20)
    img_custom = verse_number(test_number, padding=custom_padding)
    print(f"Custom padding {custom_padding} size: {img_custom.size}")

    test_output = "./ayat/new/numbers/"
    os.makedirs(test_output, exist_ok=True)

    output_path_default = os.path.join(test_output, f"{test_number:03d}_default_4tuple.png")
    img_default.save(output_path_default)

    output_path_custom = os.path.join(test_output, f"{test_number:03d}_custom_4tuple.png")
    img_custom.save(output_path_custom)

    print(f"Test generation complete. Saved to {test_output}")
