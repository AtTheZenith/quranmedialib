"""Module for rendering verse numbers as images."""

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from quranmedialib.modules.font_cache import get_font
from quranmedialib.resources import get_font_path
from quranmedialib.types import WordConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Translation table for Arabic-Indic numerals
ARABIC_INDIC_TRANS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# Module-level singleton for text measurement
_MEASURE_DRAW = ImageDraw.Draw(Image.new("RGBA", (1, 1)))


def verse_number(
    number: int,
    word_config: WordConfig,
    font_path: Path | str | None = None,
) -> Image.Image:
    """Generates an image of the ayah symbol with the given number.

    Args:
        number: The ayah number to draw (must be non-negative).
        word_config: Configuration containing font size, colors, and padding.
        font_path: Optional path to the font file. Defaults to packaged hafs.otf.

    Returns:
        A PIL Image containing the generated verse number symbol.

    Raises:
        ValueError: If number is negative.
    """
    if number < 0:
        raise ValueError(f"Verse number must be non-negative, got {number}")

    # Resolve font path
    if font_path is None:
        font_path = get_font_path("hafs.otf")
    font_path_str = str(Path(font_path))

    try:
        symbol_font = get_font(font_path_str, word_config.verse_number_size)
    except (OSError, IOError) as e:
        logger.warning("Could not load font from %s: %s. Using default.", font_path, e)
        symbol_font = ImageFont.load_default()

    # Convert number to Arabic-Indic numerals
    number_str = str(number).translate(ARABIC_INDIC_TRANS)

    # Measure text bounding box using module-level singleton
    bbox = _MEASURE_DRAW.textbbox((0, 0), number_str, font=symbol_font, anchor="mm")

    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = word_config.verse_number_padding

    # Create image fitting text plus padding
    img_w = int(text_w + padding.horizontal)
    img_h = int(text_h + padding.vertical)

    img = Image.new("RGBA", (img_w, img_h), color=word_config.background_color)
    draw = ImageDraw.Draw(img)

    # Calculate center position based on padding and text dimensions
    center_x = padding.left + text_w / 2
    center_y = padding.top + text_h / 2

    draw.text((center_x, center_y), number_str, font=symbol_font, fill=word_config.verse_number_color, anchor="mm")

    return img
