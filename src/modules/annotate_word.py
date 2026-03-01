from PIL import Image, ImageDraw, ImageFont

from src.modules.database_manager import DatabaseManager

db = DatabaseManager()


def annotate_word(
    image: Image.Image,
    surah: int,
    ayah: int,
    word_index: int,
    translation_font_size: int = 28,
    color: tuple[int, int, int, int] = (255, 255, 255, 255),
    padding: tuple[int, int, int, int] = (0, 42, 0, 0),
    db: DatabaseManager | None = None,
    translation: str | None = None,
    font_path: str | None = None,
    background_color: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image:
    """Annotates a word image with its translation.

    Creates a new image with the translation drawn below the original image.
    Uses baseline alignment for the translation text to ensure consistency.

    Args:
        image: The input PIL Image of the Arabic word.
        surah: The surah number.
        ayah: The ayah number.
        word_index: The word index within the ayah.
        translation_font_size: Font size for the translation text.
        color: RGBA color for the translation text.
        padding: A tuple of (top, bottom, left, right) padding values.
        db: Optional DatabaseManager instance for dependency injection.
        translation: Optional pre-fetched translation string.
        font_path: Optional path to a .ttf font file. Defaults to "./assets/inter.ttf".
        background_color: RGBA color for the new image background.

    Returns:
        A new PIL Image containing the Arabic word and its translation.

    Raises:
        ValueError: If padding is not a tuple of 4 integers.
    """
    # Validate padding
    if not isinstance(padding, tuple) or len(padding) != 4 or not all(isinstance(p, int) for p in padding):
        raise ValueError("padding must be a tuple of 4 integers (top, bottom, left, right)")

    # Fetch translation if not provided
    if translation is None:
        database = db if db is not None else globals().get("db")
        if database:
            translation = database.fetch_translation_for_word(surah, ayah, word_index)

    # Handle missing or empty translations
    if not translation:
        return image
    # Font settings for translation
    actual_font_path = font_path if font_path is not None else "./assets/inter.ttf"
    try:
        font = ImageFont.truetype(actual_font_path, translation_font_size)
    except (OSError, IOError):
        print(f"Warning: Could not load font at {actual_font_path}. Falling back to default font.")
        font = ImageFont.load_default()

    # Calculate translation dimensions and metrics
    ascent, descent = font.getmetrics()
    # bbox is (left, top, right, bottom)
    bbox = font.getbbox(translation)
    tw = bbox[2] - bbox[0]
    # Height is based on the font's maximum possible height to ensure consistency
    th = ascent + descent

    # Original image dimensions
    iw, ih = image.size

    # Padding and layout
    # padding is (top, bottom, left, right)
    total_w = max(iw, tw + padding[2] + padding[3])
    # The Arabic word sits at the top, followed by padding[0], then translation, then padding[1]
    total_h = ih + padding[0] + th + padding[1]

    # Create new image
    new_img = Image.new("RGBA", (total_w, total_h), color=background_color)

    # Paste original Arabic word (centered horizontally)
    # The Arabic image already has its own internal padding from word_to_image.py
    new_img.paste(image, ((total_w - iw) // 2, 0), image if image.mode == "RGBA" else None)

    # Draw translation text (centered horizontally below the Arabic word)
    draw = ImageDraw.Draw(new_img)
    tx = (total_w - tw) // 2 - bbox[0]
    # Baseline for translation: Arabic image height + top padding + font's ascent
    # anchor="ls" means "left, baseline"
    ty = ih + padding[0] + ascent
    draw.text((tx, ty), translation, font=font, fill=color, anchor="ls")

    return new_img
