import re
from typing import Iterator, NamedTuple
from PIL import Image

from src.modules.annotation import annotate_word
from src.modules.framer import frame
from src.modules.verse_number import verse_number
from src.modules.timage import get_timage
from src.modules.wimage import get_wimage
from src.workflows.base import VerseWorkflow


class ParsedSegment(NamedTuple):
    """Represents a pre-parsed translation segment."""

    flags: str
    hex_color: str
    content: str
    original_had_tag: bool


def _normalize_highlight_style(style: str) -> str:
    """Ensures highlight_style is in the correct #flags#hex# format."""
    if not style.startswith("#"):
        style = f"#{style}"
    if not style.endswith("#"):
        style = f"{style}#"
    # If highlight_style is only flags (e.g. #b#), add separator for empty hex
    if style.count("#") == 2:
        style = f"{style}#"
    return style


def _prepare_translation(translation: list[str]) -> list[ParsedSegment]:
    """Pre-parses translation segments to avoid redundant regex searches in loops."""
    tag_pattern = re.compile(r"#([bi]*)#([0-9a-fA-F]*|)#(.*?)(?=#|$)")
    parsed = []

    for segment in translation:
        if match := tag_pattern.search(segment):
            content = match[3].rstrip("#")
            parsed.append(ParsedSegment(match[1], match[2], content, True))
        else:
            parsed.append(ParsedSegment("", "", segment, False))
    return parsed


def _format_isolated_translation(
    parsed_segments: list[ParsedSegment],
    target_index: int,
    highlight_style: str,
) -> str:
    """Constructs the formatted translation string for a specific word isolation."""
    formatted = []
    for j, seg in enumerate(parsed_segments):
        if j == target_index:
            if seg.original_had_tag:
                # Keep original formatting if it already has tags
                formatted.append(f"#{seg.flags}#{seg.hex_color}#{seg.content}#")
            else:
                # Apply highlight style to plain text
                formatted.append(f"{highlight_style}{seg.content}#")
        elif seg.original_had_tag:
            # Preserve flags but force transparency
            formatted.append(f"#{seg.flags}#00000000#{seg.content}#")
        else:
            # Wrap plain text with transparent tag
            formatted.append(f"##00000000#{seg.content}#")

    return " ".join(formatted)


class IsolateWordsWorkflow(VerseWorkflow):
    """
    Workflow for isolating each word of a verse in its layout context.
    """

    def process_verse(
        self,
        verse_data: dict,
        translation_data: list[str],
        **kwargs,
    ) -> Iterator[list[Image.Image]]:
        """
        Isolates each word (and optionally the verse number) of a verse in its layout context.

        Args:
            verse_data: Dictionary containing:
                - "words": list[str]
                - "surah": int
                - "ayah": int | None (optional)
                - "wbw_translations": list[str] | None (optional)
            translation_data: List of translation segments (list[str]).
            **kwargs:
                - annotate: bool (default: True)
                - highlight_style: str (default: "#b#")

        Yields:
            list[Image.Image]: A list of pages for each isolated state.
        """
        verse_words = verse_data["words"]
        surah_number = verse_data["surah"]
        ayah_number = verse_data.get("ayah")
        wbw_translations = verse_data.get("wbw_translations")

        annotate = kwargs.get("annotate", True)
        highlight_style = kwargs.get("highlight_style", "#b#")

        # 1. Prepare base images and transparent placeholders
        word_images = [get_wimage(word) for word in verse_words]

        if annotate:
            annotated_images = [
                annotate_word(
                    img,
                    surah_number,
                    ayah_number or 1,
                    i + 1,
                    translation=wbw_translations[i] if wbw_translations else None,
                )
                for i, img in enumerate(word_images)
            ]
        else:
            annotated_images = word_images

        # 2. Add verse number if provided
        items_text = list(verse_words)
        if ayah_number is not None:
            v_img = verse_number(ayah_number, font_size=110, padding=(1, 71, 1, 1))
            annotated_images.append(v_img)
            items_text.append("")

        # Optimization: Create transparent placeholders once
        transparent_placeholders = [Image.new("RGBA", img.size, (0, 0, 0, 0)) for img in annotated_images]

        # 3. Build isolation table
        total_items = len(annotated_images)
        parsed_trans = _prepare_translation(translation_data)
        norm_highlight = _normalize_highlight_style(highlight_style)

        for i in range(total_items):
            # Create image list: all items except i-th are transparent placeholders
            isolated_images = list(transparent_placeholders)
            isolated_images[i] = annotated_images[i]

            # Prepare translation image
            t_img = None
            if i < len(parsed_trans):
                full_trans_formatted = _format_isolated_translation(parsed_trans, i, norm_highlight)
                t_img = get_timage(
                    full_trans_formatted,
                    self.layout_config.content_width,
                    self.text_config,
                )

            # Frame the isolated images
            yield frame(
                isolated_images,
                words_text=items_text,
                translation_images=[t_img] if t_img else None,
                config=self.layout_config,
            )
