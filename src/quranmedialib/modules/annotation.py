"""Module for annotating word images with translations."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.types import WordConfig


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
    db: DatabaseManager | None = None,
    translation: str | None = None,
    word_config: WordConfig | None = None,
) -> Image.Image:
    """Annotates a single word image with its translation."""
    if translation is None:
        database = db if db is not None else DatabaseManager()
        if database:
            translation = database.get_wbw_from_word(surah, ayah, word_index)

    if not translation:
        return image

    # Determine font size
    if word_config is None:
        raise ValueError("word_config is required for annotation.")

    annotation_font_size = word_config.annotation_font_size

    # Resolve font path
    font_path = word_config.annotation_font_path
    if isinstance(font_path, Path):
        font_path = str(font_path)

    try:
        font = ImageFont.truetype(font_path, annotation_font_size)
    except (OSError, IOError) as e:
        raise e

    return _annotate_image(image, translation, font, word_config.annotation_color, word_config.background_color)


def annotate_words(
    images: list[Image.Image],
    surah: int,
    ayah: int,
    start: int,
    db: DatabaseManager | None = None,
    word_config: WordConfig | None = None,
    texts: list[str] | None = None,
) -> list[Image.Image] | tuple[list[Image.Image], list[str]]:
    """Annotates a list of word images, batching those with identical translations.

    Args:
        images: List of PIL Images of the Arabic words.
        surah: The surah number.
        ayah: The ayah number.
        start: The 1-indexed database start index for the first word in the list.
        db: Optional DatabaseManager instance.
        word_config: Optional WordConfig instance to source annotation_font_size.
        texts: Optional list of original word texts to return alongside annotated images.

    Returns:
        A list of annotated PIL Images (some may contain multiple Arabic words),
        and optionally a list of concatenated texts if `texts` was provided.

    Raises:
        ValueError: If the range or image count is invalid for the verse.
    """
    database = db if db is not None else DatabaseManager()
    if not database:
        raise RuntimeError("DatabaseManager is not provided or initialized.")

    # Validation and index handling
    verse_wbws = database.get_wbw_from_verse(surah, ayah)
    verse_len = len(verse_wbws)

    range_len = len(images)
    if start < 1 or range_len > verse_len:
        raise ValueError(
            f"Range {start}-{start + range_len - 1} is out of bounds for verse {surah}:{ayah} (length {verse_len})."
        )

    # WBWs for our range (0-indexed slice from 1-indexed database indices)
    target_wbws = verse_wbws[start - 1 : start - 1 + range_len]

    # Determine font size
    if word_config is None:
        raise ValueError("word_config is required for annotation.")

    # Load font once for all annotations in this batch
    font_path = word_config.annotation_font_path
    if isinstance(font_path, Path):
        font_path = str(font_path)

    try:
        font = ImageFont.truetype(font_path, word_config.annotation_font_size)
    except (OSError, IOError) as e:
        raise e

    i = 0
    annotated_images = []
    annotated_texts = []

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

            total_w = sum(img.width for img in rtl_images) + word_config.word_spacing * (batch_count - 1)
            max_h = max(img.height for img in rtl_images)

            combined_canvas = Image.new("RGBA", (total_w, max_h), color=word_config.background_color)
            current_x = 0
            for img in rtl_images:
                # Vertical alignment: center within max_h
                y_offset = (max_h - img.height) // 2
                combined_canvas.paste(img, (current_x, y_offset), img if img.mode == "RGBA" else None)
                current_x += img.width + word_config.word_spacing

            # Annotate combined image
            annotated_images.append(
                _annotate_image(
                    combined_canvas, current_wbw, font, word_config.annotation_color, word_config.background_color
                )
            )
            if texts is not None:
                # Concatenate text for the batched items
                annotated_texts.append(" ".join(texts[i : i + batch_count]))
        else:
            # Single word annotation
            annotated_images.append(
                _annotate_image(
                    images[i], current_wbw, font, word_config.annotation_color, word_config.background_color
                )
            )
            if texts is not None:
                annotated_texts.append(texts[i])

        i += batch_count

    if texts is not None:
        return annotated_images, annotated_texts
    return annotated_images
