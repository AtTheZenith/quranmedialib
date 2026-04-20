"""Workflow for isolating individual words within a verse."""

import logging
import warnings
from typing import Iterator

from PIL import Image

from quranmedialib.exceptions import ValidationError
from quranmedialib.modules.annotation import annotate_words
from quranmedialib.modules.framer import frame
from quranmedialib.modules.timage import (
    format_isolation_text,
    get_timage,
    normalize_highlight_style,
    prepare_translation_segments,
)
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import WordItem
from quranmedialib.workflows.base import BaseWorkflow

logger = logging.getLogger(__name__)

__all__ = ["IsolateWordsWorkflow"]


class IsolateWordsWorkflow(BaseWorkflow):
    """
    Workflow for isolating each word of a verse in its layout context.
    """

    def get_iterator(
        self,
        surah: int,
        verse_words: list[str],
        translations: list[str],
        ayah: int | None = None,
        wbw_translations: list[str] | None = None,
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """
        Isolates each word (and optionally the verse number) of a verse in its layout context.

        Args:
            surah: The Surah number.
            verse_words: List of Arabic words in the verse.
            translations: List of translation segments (list[str]).
            ayah: Ayah number (optional).
            wbw_translations: List of word-by-word translations (optional).
            **kwargs:
                - annotate: bool (default: True)
                - highlight_style: str (default: "#b#")

        Yields:
            list[Image.Image]: A list of pages for each isolated state.

        Raises:
            ValidationError: If verse_words is empty or surah/ayah out of range.
        """
        surah = self._validate_surah(surah)
        if ayah is not None:
            self._validate_ayah(ayah)

        if not verse_words:
            raise ValidationError("verse_words must be a non-empty list")

        annotate = kwargs.get("annotate", True)
        highlight_style = kwargs.get("highlight_style", "#b#")

        # Warn about wbw_translations length mismatch
        if wbw_translations and len(wbw_translations) != len(verse_words):
            warnings.warn(
                f"wbw_translations length ({len(wbw_translations)}) does not match "
                f"verse_words length ({len(verse_words)}). Mismatched indices will be skipped.",
                UserWarning,
                stacklevel=2,
            )

        # 1. Prepare base images and transparent placeholders
        word_images = [get_wimage(word, self.word_config) for word in verse_words]

        if annotate:
            # Standardize: use the plural version which supports batching and caching
            annotated_images = annotate_words(
                images=word_images,
                surah=surah,
                ayah=ayah or 1,
                start=1,
                word_config=self.word_config,
                wbw_translations=wbw_translations,
            )
        else:
            annotated_images = word_images

        # 2. Add verse number if provided
        items_text = list(verse_words)
        if ayah is not None:
            v_img = verse_number(ayah, self.word_config)
            annotated_images.append(v_img)
            items_text.append("")

        # Optimization: Create transparent placeholders once
        transparent_placeholders = [Image.new("RGBA", img.size, (0, 0, 0, 0)) for img in annotated_images]

        # 3. Build isolation table
        total_items = len(annotated_images)
        parsed_trans = prepare_translation_segments(translations)
        norm_highlight = normalize_highlight_style(highlight_style)

        # Pre-compute all formatted translation strings
        # Handle case where there are more words than translation segments
        num_segments = len(parsed_trans)
        formatted_translations = []
        for i in range(total_items):
            if i < num_segments:
                formatted_translations.append(format_isolation_text(parsed_trans, i, norm_highlight))
            else:
                # No matching segment - create transparent placeholder text
                formatted_translations.append("##00000000#(no translation)#")

        for i in range(total_items):
            # Create image list efficiently: use list comprehension with index check
            isolated_images = [
                annotated_images[i] if j == i else transparent_placeholders[j] for j in range(total_items)
            ]

            # Prepare translation image
            t_img = None
            if i < len(formatted_translations):
                t_img = get_timage(
                    formatted_translations[i],
                    self.text_config,
                )

            # Bundle into WordItems for layout
            items = [WordItem(img, text) for img, text in zip(isolated_images, items_text)]

            # Frame the isolated images
            yield frame(
                items,
                translation_images=[t_img] if t_img else None,
                config=self.layout_config,
                word_config=self.word_config,
            )
