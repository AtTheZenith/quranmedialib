"""Module for annotating word images with translations.

This module provides functionality to draw translation text (annotation) below
Arabic word images. It supports batching consecutive words that share the same
translation into a single annotated block, maintaining Right-to-Left (RTL) order.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.types import WordConfig


def _get_annotation_font(word_config: WordConfig) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load the font specified in WordConfig for annotations.

    Args:
        word_config: Configuration containing font path and size.

    Returns:
        A loaded PIL font object.

    Raises:
        OSError: If the font file cannot be loaded.
    """
    font_path = word_config.annotation_font_path
    if isinstance(font_path, Path):
        font_path = str(font_path)

    try:
        return ImageFont.truetype(font_path, word_config.annotation_font_size)
    except (OSError, IOError) as e:
        # Re-raise with a bit more context if needed, but keeping it simple for now as requested.
        raise e


def _combine_images_rtl(images: list[Image.Image], word_spacing: int, background_color: tuple[int, int, int, int]) -> Image.Image:
    """Combines multiple word images into a single canvas in RTL order.

    Args:
        images: List of images to combine.
        word_spacing: Pixels of horizontal space between words.
        background_color: RGBA color for the canvas background.

    Returns:
        A single combined PIL Image.
    """
    # Quranic layout is RTL, so the first word in the list (start of verse range)
    # should be on the RIGHT side of the combined image.
    rtl_images = list(reversed(images))
    batch_count = len(rtl_images)

    total_w = sum(img.width for img in rtl_images) + word_spacing * (batch_count - 1)
    max_h = max(img.height for img in rtl_images)

    combined_canvas = Image.new("RGBA", (total_w, max_h), color=background_color)
    current_x = 0
    for img in rtl_images:
        # Vertical alignment: center each word within the maximum height of the batch.
        y_offset = (max_h - img.height) // 2
        combined_canvas.paste(img, (current_x, y_offset), img if img.mode == "RGBA" else None)
        current_x += img.width + word_spacing

    return combined_canvas


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
    """Annotates a single word image with its translation.

    Args:
        image: The source word image.
        surah: Surah number for DB lookup.
        ayah: Ayah number for DB lookup.
        word_index: Word index in verse for DB lookup.
        db: Optional database manager instance.
        translation: Optional pre-fetched translation text.
        word_config: Rendering configuration.

    Returns:
        Annotated image.
    """
    if translation is None:
        database = db if db is not None else DatabaseManager()
        translation = database.get_wbw_from_word(surah, ayah, word_index)

    if not translation:
        return image

    if word_config is None:
        raise ValueError("word_config is required for annotation.")

    font = _get_annotation_font(word_config)
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

    Consecutive words sharing the same WBW translation are combined into a single
    block before annotation is applied.

    Args:
        images: List of word images.
        surah: Surah number.
        ayah: Ayah number.
        start: 1-indexed database start index for the first word in images.
        db: Optional DatabaseManager instance.
        word_config: Rendering configuration.
        texts: Optional list of word strings to return alongside annotated images.

    Returns:
        List of annotated images (may be fewer than input images due to batching).
        If texts is provided, returns (annotated_images, annotated_texts).

    Raises:
        ValueError: If range is out of bounds or config is missing.
    """
    database = db if db is not None else DatabaseManager()
    if not word_config:
        raise ValueError("word_config is required for annotation.")

    # Fetch all WBW translations for the verse to optimize lookups
    verse_wbws = database.get_wbw_from_verse(surah, ayah)
    range_len = len(images)

    if start < 1 or (start + range_len - 1) > len(verse_wbws):
        raise ValueError(f"Range {start}-{start + range_len - 1} out of bounds for verse {surah}:{ayah}.")

    # Slice the translations needed for our specific images
    target_wbws = verse_wbws[start - 1 : start - 1 + range_len]
    font = _get_annotation_font(word_config)

    i = 0
    annotated_images = []
    annotated_texts = []

    while i < range_len:
        current_wbw = target_wbws[i]

        # Find how many consecutive words share this translation
        batch_count = 1
        while (i + batch_count < range_len) and (target_wbws[i + batch_count] == current_wbw):
            batch_count += 1

        if batch_count >= 2:
            # Multi-word batch: Combine first, then annotate
            batch_images = images[i : i + batch_count]
            combined = _combine_images_rtl(batch_images, word_config.word_spacing, word_config.background_color)
            annotated_images.append(
                _annotate_image(combined, current_wbw, font, word_config.annotation_color, word_config.background_color)
            )
            if texts is not None:
                annotated_texts.append(" ".join(texts[i : i + batch_count]))
        else:
            # Single word
            annotated_images.append(
                _annotate_image(images[i], current_wbw, font, word_config.annotation_color, word_config.background_color)
            )
            if texts is not None:
                annotated_texts.append(texts[i])

        i += batch_count

    if texts is not None:
        return annotated_images, annotated_texts
    return annotated_images
