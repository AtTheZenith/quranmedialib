from PIL import Image, ImageDraw, ImageFont

from src.modules.database_manager import DatabaseManager

db = DatabaseManager()


def _annotate_image(
    image: Image.Image,
    translation: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: tuple[int, int, int, int],
    background_color: tuple[int, int, int, int],
) -> Image.Image:
    """Helper to draw translation text below an image.

    Args:
        image: The base image (Arabic word or combined words).
        translation: The translation text to draw.
        font: The font to use for the translation.
        color: RGBA color for the text.
        background_color: RGBA color for the new image background.

    Returns:
        A new PIL Image with the translation drawn below the input image.
    """
    # Calculate translation dimensions and metrics
    ascent, descent = font.getmetrics()
    bbox = font.getbbox(translation)
    tw = bbox[2] - bbox[0]
    th = ascent + descent

    # Original image dimensions
    iw, ih = image.size

    # New dimensions (no extra vertical padding, preserving previous behavior)
    total_w = max(iw, tw)
    total_h = ih + th

    # Create new image
    new_img = Image.new("RGBA", (total_w, total_h), color=background_color)

    # Paste original image (centered horizontally)
    new_img.paste(image, ((total_w - iw) // 2, 0), image if image.mode == "RGBA" else None)

    # Draw translation text (centered horizontally below the image)
    draw = ImageDraw.Draw(new_img)
    tx = (total_w - tw) // 2 - bbox[0]
    ty = ih + ascent
    draw.text((tx, ty), translation, font=font, fill=color, anchor="ls")

    return new_img


def annotate_word(
    image: Image.Image,
    surah: int,
    ayah: int,
    word_index: int,
    translation_font_size: int = 28,
    color: tuple[int, int, int, int] = (255, 255, 255, 255),
    db: DatabaseManager | None = None,
    translation: str | None = None,
    font_path: str | None = None,
    background_color: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image:
    """Annotates a single word image with its translation."""
    if translation is None:
        database = db if db is not None else globals().get("db")
        if database:
            translation = database.get_wbw_from_word(surah, ayah, word_index)

    if not translation:
        return image

    actual_font_path = font_path if font_path is not None else "./assets/inter.ttf"
    try:
        font = ImageFont.truetype(actual_font_path, translation_font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    return _annotate_image(image, translation, font, color, background_color)


def annotate_words(
    images: list[Image.Image],
    surah: int,
    ayah: int,
    start: int,
    end: int | None = None,
    translation_font_size: int = 28,
    color: tuple[int, int, int, int] = (255, 255, 255, 255),
    db: DatabaseManager | None = None,
    font_path: str | None = None,
    background_color: tuple[int, int, int, int] = (0, 0, 0, 0),
    word_spacing: int = 10,
) -> list[Image.Image]:
    """Annotates a list of word images, batching those with identical translations.

    Args:
        images: List of PIL Images of the Arabic words.
        surah: The surah number.
        ayah: The ayah number.
        start: The 1-indexed database start index for the first word in the list.
        end: Optional 1-indexed database end index.
        translation_font_size: Font size for the translation text.
        color: RGBA color for the translation text.
        db: Optional DatabaseManager instance.
        font_path: Optional path to a .ttf font file.
        background_color: RGBA color for the new image background.
        word_spacing: Spacing between words when combined RTL.

    Returns:
        A list of annotated PIL Images (some may contain multiple Arabic words).

    Raises:
        IndexError: If the range or image count is invalid for the verse.
    """
    database = db if db is not None else globals().get("db")
    if not database:
        raise RuntimeError("DatabaseManager is not provided or initialized.")

    # Validation and index handling
    verse_wbws = database.get_wbw_from_verse(surah, ayah)
    verse_len = len(verse_wbws)

    if end is None:
        end = start + len(images) - 1

    range_len = end - start + 1
    if len(images) != range_len:
        raise IndexError(f"Expected {range_len} images for range {start}-{end}, but got {len(images)}.")

    if start < 1 or end > verse_len:
        raise IndexError(f"Range {start}-{end} is out of bounds for verse {surah}:{ayah} (length {verse_len}).")

    # WBWs for our range (0-indexed slice from 1-indexed database indices)
    target_wbws = verse_wbws[start - 1 : end]

    annotated_list = []

    # Load font once for all annotations in this batch
    actual_font_path = font_path if font_path is not None else "./assets/inter.ttf"
    try:
        font = ImageFont.truetype(actual_font_path, translation_font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    i = 0
    while i < len(images):
        current_wbw = target_wbws[i]

        # Find consecutive words with identical WBW
        batch_count = 1
        while (i + batch_count < len(images)) and (target_wbws[i + batch_count] == current_wbw):
            batch_count += 1

        if batch_count >= 2:
            # Combine batch words RTL
            batch_images = images[i : i + batch_count]
            # Quranic layout is RTL, so the first word (index i) is leftmost in the list but rightmost in image
            # However, the images list reflects the reading order (start to end).
            # To combine RTL: [wordN, ..., word2, word1]
            rtl_images = list(reversed(batch_images))

            total_w = sum(img.width for img in rtl_images) + word_spacing * (batch_count - 1)
            max_h = max(img.height for img in rtl_images)

            combined_canvas = Image.new("RGBA", (total_w, max_h), color=(0, 0, 0, 0))
            current_x = 0
            for img in rtl_images:
                # Vertical alignment: center within max_h
                y_offset = (max_h - img.height) // 2
                combined_canvas.paste(img, (current_x, y_offset), img if img.mode == "RGBA" else None)
                current_x += img.width + word_spacing

            # Annotate combined image
            annotated_list.append(_annotate_image(combined_canvas, current_wbw, font, color, background_color))
        else:
            # Single word annotation
            annotated_list.append(_annotate_image(images[i], current_wbw, font, color, background_color))

        i += batch_count

    return annotated_list
