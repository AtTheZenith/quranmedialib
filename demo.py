"""Demo script showcasing QuranMediaLib workflows and features.

This script demonstrates various usage patterns including:
- Running SurahWorkflow with different presets (landscape, story, square)
- Processing verses with and without annotations
- Working with Arabic-only, translation-only, and combined modes
- Applying glow effects and saving output images

Run this script to generate sample images for all preset configurations.
"""

import os
from typing import Literal

from PIL import Image

from quranmedialib import (
    LANDSCAPE_PRESET,
    SQUARE_PRESET,
    STORY_PRESET,
    DatabaseManager,
    LayoutConfig,
    TextConfig,
    WordConfig,
    WordItem,
)
from quranmedialib.modules.annotation import annotate_words
from quranmedialib.modules.framer import frame
from quranmedialib.modules.image import glow
from quranmedialib.modules.timage import get_timage
from quranmedialib.modules.verse_number import verse_number
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.workflows.surah import SurahWorkflow


def run_workflow_demo(
    preset_config: tuple[LayoutConfig, TextConfig, WordConfig],
    data: dict[str, int],
    annotate: bool = True,
) -> list[Image.Image]:
    """Runs a SurahWorkflow for a given preset and returns the generated images."""
    layout_config, text_config, word_config = preset_config
    workflow = SurahWorkflow(
        layout_config=layout_config,
        text_config=text_config,
        word_config=word_config,
    )
    iterator = workflow.get_iterator(surah=data["surah"], annotate=annotate)
    return [img for page in iterator for img in page]


def _process_verse_words(
    verse_text: str,
    surah_id: int,
    ayah_num: int,
    word_config: WordConfig,
    db: DatabaseManager,
    annotate: bool = True,
) -> tuple[list[Image.Image], list[str]]:
    """Helper to process words of a single verse: split, generate images, and annotate."""
    words = verse_text.split()
    wimages = [get_wimage(word, word_config) for word in words]

    # Annotate the words
    # Note: 'texts' argument expects the list of original word strings
    return (
        annotate_words(
            wimages,
            surah=surah_id,
            ayah=ayah_num,
            start=1,
            word_config=word_config,
            texts=words,
            db=db,
        )
        if annotate
        else (wimages, words)
    )


def create_square_demo(
    db: DatabaseManager,
    surah_id: int,
    preset: tuple[LayoutConfig, TextConfig, WordConfig],
    mode: Literal["default", "arabic", "translation"] = "default",
) -> list[Image.Image]:
    """Generates images for the Square demo.

    Args:
        db: DatabaseManager instance.
        surah_id: ID of the surah to process.
        preset: Tuple of (layout_config, text_config, word_config).
        mode: 'default' (annotated + trans), 'arabic' (annotated only), 'translation' (trans only).
    """
    layout_config, text_config, word_config = preset

    all_word_images: list[Image.Image] = []
    all_words_text: list[str] = []

    # 1. Process Verses (for default and arabic modes)
    if mode in ["default", "arabic"]:
        verses = db.get_verses_from_surah(surah_id)
        for i, verse_text in enumerate(verses):
            annotated_imgs, annotated_txts = _process_verse_words(
                verse_text, surah_id, i + 1, word_config, db, annotate=(mode == "default")
            )
            all_word_images.extend(annotated_imgs)
            all_words_text.extend(annotated_txts)

            # Add verse number
            v_num_img = verse_number(i + 1, word_config)
            all_word_images.append(v_num_img)
            all_words_text.append(str(i + 1))

    elif mode == "translation":
        # In translation mode, we use a dummy item as per original code
        # "all_items = [WordItem(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), "a")]"
        all_word_images.append(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
        all_words_text.append("a")

    # 2. Process Translation Image
    if mode in ["default", "translation"]:
        translations = db.get_translation_from_surah(surah_id)
        combined_text = "\n".join(translations)
        trans_img = get_timage(combined_text, text_config)
    else:
        # For 'arabic' mode, empty translation image
        trans_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    # 3. Frame
    all_items = [WordItem(img, text) for img, text in zip(all_word_images, all_words_text)]

    return frame(
        all_items,
        translation_images=[trans_img],
        config=layout_config,
        word_config=word_config,
    )


def save_images(images: list[Image.Image], output_dir: str) -> None:
    """Applies glow and saves images to the output directory."""
    os.makedirs(output_dir, exist_ok=True)
    for i, img in enumerate(images):
        # Apply glow before saving as per original main()
        final_img = glow(img)
        filename = f"{(i + 1):02d}.png"
        path = os.path.join(output_dir, filename)
        final_img.save(path)
        print(f"Saved {filename}")


def main() -> None:
    db = DatabaseManager()
    surah_id = 108
    data = {"surah": surah_id}
    resolution = "1080p"
    all_results: list[Image.Image] = []

    try:
        # === Default ===
        # Landscape
        all_results.extend(run_workflow_demo(LANDSCAPE_PRESET["default"][resolution], data))

        # Story
        all_results.extend(run_workflow_demo(STORY_PRESET["default"][resolution], data))

        # Square
        all_results.extend(create_square_demo(db, surah_id, SQUARE_PRESET["default"][resolution], mode="default"))

        # === Arabic ===
        # Landscape
        all_results.extend(run_workflow_demo(LANDSCAPE_PRESET["arabic"][resolution], data, annotate=False))

        # Story
        all_results.extend(run_workflow_demo(STORY_PRESET["arabic"][resolution], data, annotate=False))

        # Square
        all_results.extend(create_square_demo(db, surah_id, SQUARE_PRESET["arabic"][resolution], mode="arabic"))

        # === Translation ===
        # Landscape
        all_results.extend(run_workflow_demo(LANDSCAPE_PRESET["translation"][resolution], data))

        # Story
        all_results.extend(run_workflow_demo(STORY_PRESET["translation"][resolution], data))

        # Square
        all_results.extend(
            create_square_demo(db, surah_id, SQUARE_PRESET["translation"][resolution], mode="translation")
        )

        # Save all results
        save_images(all_results, "output/demo")

    finally:
        db.close()


if __name__ == "__main__":
    main()
