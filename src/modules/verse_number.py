import os
import logging
from typing import Union, Tuple
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hardcoded constants
FONT_PATH = "./assets/hafs.otf"

# Translation table for Arabic-Indic numerals
ARABIC_INDIC_TRANS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# Type aliases
Color = Union[Tuple[int, int, int], Tuple[int, int, int, int]]
Padding = Tuple[int, int, int, int]


def verse_number(
    number: int,
    font_size: int = 128,
    color: Color = (255, 255, 255, 255),
    padding: Padding = (10, 10, 10, 10),
    font_path: str = FONT_PATH,
    background_color: Color = (0, 0, 0, 0),
) -> Image.Image:
    """Generates an image of the ayah symbol with the given number using Unicode.

    Padding semantics: (top, bottom, left, right)

    Args:
        number: The ayah number to draw (must be non-negative).
        font_size: Font size for the Unicode symbol.
        color: RGB or RGBA color for the text.
        padding: A 4-tuple of (top, bottom, left, right) padding values.
        font_path: Path to the .otf or .ttf font file.
        background_color: RGB or RGBA color for the image background.

    Returns:
        A PIL Image containing the generated verse number symbol.

    Raises:
        ValueError: If `number` is negative or `padding` is invalid.

    Example:
        >>> img = verse_number(286, font_size=64)
        >>> isinstance(img, Image.Image)
        True
    """
    if number < 0:
        raise ValueError(f"Verse number must be non-negative, got {number}")

    if len(padding) != 4 or any(p < 0 for p in padding):
        raise ValueError(f"Padding must be a 4-tuple of non-negative integers, got {padding}")

    try:
        if not os.path.exists(font_path):
            logger.warning(f"Font path {font_path} does not exist. Falling back to default font.")
            symbol_font = ImageFont.load_default()
        else:
            symbol_font = ImageFont.truetype(font_path, font_size)
    except (OSError, IOError) as e:
        logger.warning(f"Could not load font from {font_path}. Falling back to default. Error: {e}")
        symbol_font = ImageFont.load_default()

    # Convert number to Arabic-Indic numerals
    number_str = str(number).translate(ARABIC_INDIC_TRANS)

    # Use a dummy image to measure the actual text bounding box
    # We use "mm" (middle-middle) anchor for easier centering later
    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), number_str, font=symbol_font, anchor="mm")

    # bbox is (left, top, right, bottom) relative to the anchor point (0, 0)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    top, bottom, left, right = padding

    # Create image that fits the text plus padding
    img_w = int(text_w + left + right)
    img_h = int(text_h + top + bottom)

    img = Image.new("RGBA", (img_w, img_h), color=background_color)
    draw = ImageDraw.Draw(img)

    # Calculate center position to draw the text anchored at "mm"
    # The anchor "mm" will put the exact center of the text at (center_x, center_y)
    center_x = left + text_w / 2
    center_y = top + text_h / 2

    draw.text((center_x, center_y), number_str, font=symbol_font, fill=color, anchor="mm")

    return img
