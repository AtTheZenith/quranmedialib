import os
from PIL import Image, ImageDraw, ImageFont

# Hardcoded constants
FONT_PATH = "./assets/hafs.otf"

# Translation table for Arabic-Indic numerals
ARABIC_INDIC_TRANS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def generate_verse_symbol(number, font_size=80, color=(255, 255, 255, 255)):
    """
    Generates an image of the ayah symbol with the given number using Unicode.

    Args:
        number (int): The ayah number to draw.
        font_size (int): Font size for the Unicode symbol.
        color (tuple): RGBA color for the text.

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

    # Determine image size based on symbol bbox + some padding
    w = symbol_bbox[2] - symbol_bbox[0] + 20
    h = symbol_bbox[3] - symbol_bbox[1] + 20

    # Create a blank transparent image
    img = Image.new("RGBA", (int(w), int(h)), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center_x, center_y = w // 2, h // 2
    draw.text((center_x, center_y), number_str, font=symbol_font, fill=color, anchor="mm")

    return img


if __name__ == "__main__":
    # Test generation with a single integer
    test_number = 286
    print(f"Generating ayah number {test_number} using Unicode symbol...")

    img = generate_verse_symbol(test_number)

    test_output = "./ayat/new/numbers/"
    os.makedirs(test_output, exist_ok=True)

    output_path = os.path.join(test_output, f"{test_number:03d}.png")
    img.save(output_path)

    print(f"Test generation complete. Saved to {output_path}")
