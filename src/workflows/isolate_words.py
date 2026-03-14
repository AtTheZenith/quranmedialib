import re
from PIL import Image

from src.modules.annotation import annotate_word
from src.modules.framer import frame, LayoutConfig
from src.modules.verse_number import verse_number
from src.modules.timage import get_timage, TextConfig
from src.modules.wimage import get_wimage


def isolate_words(
    verse_words: list[str],
    translation: list[str],
    surah_number: int,
    ayah_number: int | None = None,
    config: LayoutConfig | None = None,
    text_config: TextConfig | None = None,
    annotate: bool = True,
    highlight_style: str = "#b#",
    wbw_translations: list[str] | None = None,
) -> list[list[Image.Image]]:
    """
    Isolates each word (and optionally the verse number) of a verse in its layout context.

    For each item in the verse, it generates a set of pages where only that item is visible
    (others are made transparent).

    Args:
        verse_words: List of Arabic words in the verse.
        translation: List of translation segments matching verse_words.
        surah_number: The surah index.
        ayah_number: Optional ayah number to include in the layout.
        config: Layout configuration. If None, default config is used.
        annotate: Whether to apply word-level annotations.
        wbw_translations: Optional list of word-by-word translations for annotation.

    Returns:
        A list of lists of PIL Images. Each outer list corresponds to an isolated item,
        and the inner list contains the page(s) generated for that isolation.
    """
    if config is None:
        config = LayoutConfig(
            max_width=1920,
            image_height=1080,
            padding=50,
            word_spacing=20,
            row_spacing=30,
            max_rows_per_page=5,
            bottom_offset=300,
            balanced_wrapping=True,
        )

    # 1. Prepare base images
    word_images = [get_wimage(word) for word in verse_words]

    if annotate:
        annotated_images = [annotate_word(image, surah_number, ayah_number or 1, i + 1, translation=wbw_translations[i] if wbw_translations else None) for i, image in enumerate(word_images)]
    else:
        annotated_images = word_images

    # 2. Add verse number if provided
    items_text = list(verse_words)
    if ayah_number is not None:
        # Default main.py parameters for verse_number: font_size=110, padding=(1, 71, 1, 1)
        v_img = verse_number(ayah_number, font_size=110, padding=(1, 71, 1, 1))
        annotated_images.append(v_img)
        items_text.append("")  # Empty text for the verse number symbol

    # 3. Build isolation table
    isolation_table = []
    total_items = len(annotated_images)

    for i in range(total_items):
        # Create a copy where all items except the i-th one are transparent
        isolated_images = []
        for j in range(total_items):
            if i == j:
                # Keep original image
                isolated_images.append(annotated_images[j].copy())
            else:
                # Make transparent by creating a new empty image
                isolated_images.append(Image.new("RGBA", annotated_images[j].size, (0, 0, 0, 0)))

        # Prepare the full translation sentence with the i-th word highlighted
        # and others transparent.
        # Format: #flags#hex#text#
        tag_pattern = r"#([bi]*)#([0-9a-fA-F]*|)#(.*?)(?=#|$)"
        
        modified_segments = []
        for j, segment in enumerate(translation):
            match = re.search(tag_pattern, segment)
            
            if i == j:
                if match:
                    # Keep existing format
                    modified_segments.append(segment)
                else:
                    # Wrap with highlight style. Ensure style doesn't double-hash.
                    # highlight_style should be like "#b#" or "#b#ffffff#"
                    style = highlight_style
                    if not style.startswith("#"):
                        style = f"#{style}"
                    if not style.endswith("#"):
                        style = f"{style}#"
                    
                    # If highlight_style is only flags (e.g. #b#), we need the extra separator for hex
                    # Our timage pattern is #flags#hex#content#
                    if style.count("#") == 2:
                        style = f"{style}#"  # e.g. #b# -> #b##
                        
                    modified_segments.append(f"{style}{segment}#")
            else:
                if match:
                    # Preserve flags but force transparency (00000000)
                    flags = match.group(1)
                    content = match.group(3)
                    # Strip trailing # if present in content
                    if content.endswith("#"):
                        content = content[:-1]
                    modified_segments.append(f"#{flags}#00000000#{content}#")
                else:
                    # Not a tag, wrap with transparent tag
                    modified_segments.append(f"##00000000#{segment}#")

        full_trans_formatted = " ".join(modified_segments)
        # Verse number isolation (last item) gets an empty translation
        if i >= len(translation):
            full_trans_formatted = ""

        t_img = get_timage(full_trans_formatted, config.content_width, text_config) if full_trans_formatted else None

        # Frame the isolated images
        pages = frame(
            isolated_images,
            words_text=items_text,
            translation_images=[t_img] if t_img else None,
            config=config
        )
        isolation_table.append(pages)

    return isolation_table
