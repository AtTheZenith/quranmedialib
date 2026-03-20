"""Module for rendering verse numbers as images."""

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from quranmedialib.resources import get_font_path
from quranmedialib.types import WordConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Translation table for Arabic-Indic numerals
ARABIC_INDIC_TRANS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def verse_number(
    number: int,
    word_config: WordConfig,
    font_path: Path | str | None = None,
) -> Image.Image:
    """Generates an image of the ayah symbol with the given number using Unicode.

    Padding semantics: (top, bottom, left, right)

    Args:
        number: The ayah number to draw (must be non-negative).
        word_config: The word configuration containing font size and colors.
        font_path: Optional path to the font file. Defaults to packaged hafs.otf.

    Returns:
        A PIL Image containing the generated verse number symbol.

    Raises:
        ValueError: If `number` is negative or `padding` is invalid.

    Example:
        >>> img = verse_number(286, word_config)
        >>> isinstance(img, Image.Image)
        True
    """
    if number < 0:
        raise ValueError(f"Verse number must be non-negative, got {number}")

    if len(word_config.verse_number_padding) != 4 or any(p < 0 for p in word_config.verse_number_padding):
        raise ValueError(f"Padding must be a 4-tuple of non-negative integers, got {word_config.verse_number_padding}")

    # Resolve font path
    if font_path is None:
        font_path = get_font_path("hafs.otf")

    font_path = Path(font_path) if isinstance(font_path, str) else font_path

    try:
        if not font_path.exists():
            logger.warning(f"Font path {font_path} does not exist. Falling back to default font.")
            symbol_font = ImageFont.load_default()
        else:
            symbol_font = ImageFont.truetype(str(font_path), word_config.verse_number_size)
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

    top, bottom, left, right = word_config.verse_number_padding

    # Create image that fits the text plus padding
    img_w = int(text_w + left + right)
    img_h = int(text_h + top + bottom)

    img = Image.new("RGBA", (img_w, img_h), color=word_config.background_color)
    draw = ImageDraw.Draw(img)

    # Calculate center position to draw the text anchored at "mm"
    # The anchor "mm" will put the exact center of the text at (center_x, center_y)
    center_x = left + text_w / 2
    center_y = top + text_h / 2

    draw.text((center_x, center_y), number_str, font=symbol_font, fill=word_config.verse_number_color, anchor="mm")

    return img
