"""Module for annotating word images with translations.

This module provides functionality to draw translation text (annotation) below
Arabic word images. It supports batching consecutive words that share the same
translation into a single annotated block, maintaining Right-to-Left (RTL) order.
"""

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import overload

from PIL import Image, ImageDraw, ImageFont

from quranmedialib.database_manager import DatabaseManager
from quranmedialib.modules.font_cache import get_font
from quranmedialib.types import WordConfig

logger = logging.getLogger(__name__)

__all__ = [
    "annotate_words",
    "annotate_words_with_texts",
]


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

    return get_font(font_path, word_config.annotation_font_size)


def _combine_images_rtl(
    images: list[Image.Image], word_spacing: int, background_color: tuple[int, int, int, int]
) -> Image.Image:
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


@functools.lru_cache(maxsize=512)
def _annotate_word_cached(
    text: str,
    translation: str,
    font_path: str,
    font_size: int,
    word_padding: tuple[int, int, int, int],
    word_color: tuple[int, ...],
    bg_color: tuple[int, ...],
    ann_font_path: str,
    ann_font_size: int,
    ann_color: tuple[int, ...],
) -> Image.Image:
    """Cached internal renderer for word + annotation.

    Avoids tobytes() bottleneck by using text/config as keys.
    """
    from quranmedialib.modules.wimage import _get_wimage_cached

    # Re-use cached word image
    image = _get_wimage_cached(text, font_path, font_size, word_padding, word_color, bg_color)

    font = get_font(ann_font_path, ann_font_size)
    return _annotate_image(image, translation, font, ann_color, bg_color)  # type: ignore[arg-type]


def _annotate_word(
    image: Image.Image,
    surah: int,
    ayah: int,
    word_index: int,
    word_config: WordConfig,
    db: DatabaseManager | None = None,
    translation: str | None = None,
    text: str | None = None,
) -> Image.Image:
    """Internal implementation for annotating a single word image.

    This function coordinates database lookup and caching for the annotation process.
    It is the core logic used by the batch-optimized plural API.
    """
    if translation is None:
        database = db if db is not None else DatabaseManager()
        translation = database.get_wbw_from_word(surah, ayah, word_index)

    if not translation:
        return image

    # High-performance path: cache based on text/config instead of bits
    if text:
        return _annotate_word_cached(
            text,
            translation,
            str(word_config.font.path),
            word_config.font_size,
            tuple(word_config.word_padding),
            word_config.word_color,
            word_config.background_color,
            str(word_config.annotation_font_path),
            word_config.annotation_font_size,
            word_config.annotation_color,
        )

    # Fallback to slower bit-based cache for arbitrary images
    font = _get_annotation_font(word_config)
    return _annotate_image(image, translation, font, word_config.annotation_color, word_config.background_color)


@overload
def annotate_words(
    images: list[Image.Image],
    surah: int,
    ayah: int,
    start: int,
    db: DatabaseManager | None = ...,
    word_config: WordConfig | None = ...,
    texts: None = ...,
    wbw_translations: list[str] | None = ...,
) -> list[Image.Image]: ...


@overload
def annotate_words(
    images: list[Image.Image],
    surah: int,
    ayah: int,
    start: int,
    db: DatabaseManager | None = ...,
    word_config: WordConfig | None = ...,
    texts: list[str] = ...,
    wbw_translations: list[str] | None = ...,
) -> tuple[list[Image.Image], list[str]]: ...


def annotate_words(
    images: list[Image.Image],
    surah: int,
    ayah: int,
    start: int,
    db: DatabaseManager | None = None,
    word_config: WordConfig | None = None,
    texts: list[str] | None = None,
    wbw_translations: list[str] | None = None,
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
        wbw_translations: Optional pre-fetched WBW translations for the verse.
            If provided, avoids redundant database queries.

    Returns:
        List of annotated images (may be fewer than input images due to batching).
        If texts is provided, returns (annotated_images, annotated_texts).

    Raises:
        ValueError: If range is out of bounds or config is missing.
    """
    result, annotated_texts = _annotate_words_internal(
        images, surah, ayah, start, db, word_config, wbw_translations, texts
    )

    return (result, annotated_texts) if texts is not None else result


def annotate_words_with_texts(
    images: list[Image.Image],
    surah: int,
    ayah: int,
    start: int,
    texts: list[str],
    db: DatabaseManager | None = None,
    word_config: WordConfig | None = None,
    wbw_translations: list[str] | None = None,
) -> tuple[list[Image.Image], list[str]]:
    """Annotates word images and returns images with texts.

    This is a type-safe wrapper around annotate_words that always returns a tuple.

    Args:
        images: List of word images.
        surah: Surah number.
        ayah: Ayah number.
        start: 1-indexed database start index for the first word in images.
        texts: List of word strings to return alongside annotated images.
        db: Optional DatabaseManager instance.
        word_config: Rendering configuration.
        wbw_translations: Optional pre-fetched WBW translations for the verse.

    Returns:
        Tuple of (annotated_images, annotated_texts).

    Raises:
        ValueError: If range is out of bounds or config is missing.
    """
    result, annotated_texts = _annotate_words_internal(
        images, surah, ayah, start, db, word_config, wbw_translations, texts
    )
    return result, annotated_texts  # type: ignore[return-value]  # texts is always provided here


def _annotate_words_internal(
    images: list[Image.Image],
    surah: int,
    ayah: int,
    start: int,
    db: DatabaseManager | None,
    word_config: WordConfig | None,
    wbw_translations: list[str] | None = None,
    texts: list[str] | None = None,
) -> tuple[list[Image.Image], list[str] | None]:
    """Internal implementation for annotating words.

    Args:
        images: List of word images.
        surah: Surah number.
        ayah: Ayah number.
        start: 1-indexed database start index for the first word in images.
        db: Optional DatabaseManager instance.
        word_config: Rendering configuration.
        wbw_translations: Optional pre-fetched WBW translations.
        texts: Optional list of word texts to extract.

    Returns:
        Tuple of (annotated_images, annotated_texts or None).

    Raises:
        ValueError: If range is out of bounds or config is missing.
    """
    database = db if db is not None else DatabaseManager()
    if not word_config:
        raise ValueError("word_config is required for annotation.")

    if start < 1:
        raise ValueError(
            f"start index must be 1-based (>= 1), got {start}. "
            "The start parameter represents the 1-indexed word position in the verse."
        )

    # Use pre-fetched translations if provided, otherwise fetch from DB
    if wbw_translations is not None:
        verse_wbws = wbw_translations
    else:
        verse_wbws = database.get_wbw_from_verse(surah, ayah)

    range_len = len(images)

    # Slice the translations needed for our specific images
    if start - 1 >= len(verse_wbws):
        raise ValueError(f"start index {start} is out of bounds for the verse (length {len(verse_wbws)})")

    # Pad with None if images exceed translations to maintain backward compatibility and handle mismatches
    target_wbws = verse_wbws[start - 1 : start - 1 + range_len]
    if len(target_wbws) < range_len:
        target_wbws.extend([None] * (range_len - len(target_wbws)))

    font = _get_annotation_font(word_config)

    i = 0
    annotated_images = []
    annotated_texts: list[str] = []

    while i < range_len:
        current_wbw = target_wbws[i]

        # Find how many consecutive words share this translation
        batch_count = 1
        while (i + batch_count < range_len) and (target_wbws[i + batch_count] == current_wbw):
            batch_count += 1

        # Use the provided text to enable caching if possible
        batch_images = images[i : i + batch_count]

        # If no translation, return plain image (NO batching/combining)
        if not current_wbw:
            img = batch_images[0]
            annotated_images.append(img)
            if texts is not None:
                batch_text = texts[i] if texts and i < len(texts) else ""
                annotated_texts.append(batch_text)
            batch_count = 1  # Force single item processing
        elif batch_count >= 2:
            # Multi-word batch: Combine first, then annotate
            combined = _combine_images_rtl(batch_images, word_config.word_spacing, word_config.background_color)
            annotated_images.append(
                _annotate_image(combined, current_wbw, font, word_config.annotation_color, word_config.background_color)
            )
            if texts is not None:
                batch_text = " ".join(texts[i : i + batch_count]) if i < len(texts) else ""
                annotated_texts.append(batch_text)
        else:
            # Single word - use high-performance cached path if text exists
            img = batch_images[0]
            txt = texts[i] if texts and i < len(texts) else None

            ann_img = _annotate_word(
                image=img,
                surah=surah,
                ayah=ayah,
                word_index=start + i,
                word_config=word_config,
                db=db,
                translation=current_wbw,
                text=txt,
            )
            annotated_images.append(ann_img)

            if texts is not None and i < len(texts):
                annotated_texts.append(texts[i])
            elif texts is not None:
                annotated_texts.append("")  # Missing text placeholder

        i += batch_count

    return annotated_images, annotated_texts if texts is not None else None
