"""Demo script showcasing QuranMediaLib workflows and features.

This script demonstrates various usage patterns including:
- Running SurahWorkflow with every preset combination (aspect ratio x mode)
- Processing verses with and without annotations
- Applying glow effects and saving output images

Run this script to generate sample images for all preset configurations.
"""

from pathlib import Path

from PIL import Image

from quranmedialib import (
    LANDSCAPE_PRESET,
    SQUARE_PRESET,
    STORY_PRESET,
    DatabaseManager,
    Preset,
    SurahWorkflow,
)
from quranmedialib.modules.image import glow
from quranmedialib.utils.parallel import ExecutionMode, ParallelRenderer, worker_heartbeat

RESOLUTION = "1080p"
SURAH_ID = 108


def run_workflow_demo(preset: Preset, annotate: bool) -> list[Image.Image]:
    """Runs a SurahWorkflow for a given preset and returns the generated images.

    Args:
        preset: Unified configuration bundle (frame, word, verse, text).
        annotate: Whether to annotate words with word-by-word translations.

    Returns:
        list[Image.Image]: All rendered page images for the surah.
    """
    workflow = SurahWorkflow(preset)
    iterator = workflow.get_iterator(surah=SURAH_ID, annotate=annotate)
    return [img for page in iterator for img in page]


def _glow_and_save(args: tuple[Image.Image, int, Path]) -> None:
    """Worker function to apply glow and save image in a separate process."""
    img, index, output_path = args

    # Per-process memory safety heartbeat for post-processing workers.
    worker_heartbeat()

    final_img = glow(img)
    filename = f"{(index + 1):02d}.png"
    final_img.save(output_path / filename)
    print(f"Saved {filename}")


def save_images(images: list[Image.Image], output_dir: str) -> None:
    """Applies glow and saves images to the output directory in parallel.

    Args:
        images: Page images to process.
        output_dir: Directory to write the glowing images into.
    """
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    # Glow is CPU-bound (blurs), making it a perfect candidate for multi-processing.
    renderer = ParallelRenderer(mode=ExecutionMode.PROCESS)
    tasks = [(img, i, output_path) for i, img in enumerate(images)]
    list(renderer.map(_glow_and_save, tasks))


def main() -> None:
    """Runs all preset combinations sequentially with parallel image post-processing."""
    db = DatabaseManager()
    all_results: list[Image.Image] = []

    try:
        # Each aspect ratio exposes all three modes at the chosen resolution.
        # "arabic" mode keeps annotations visible (translation is transparent),
        # matching the canonical reference scenarios.
        for presets in (LANDSCAPE_PRESET, STORY_PRESET, SQUARE_PRESET):
            for mode in ("default", "arabic", "translation"):
                annotate = mode != "translation"
                print(f"Rendering {mode} preset...")
                all_results.extend(run_workflow_demo(presets[mode][RESOLUTION], annotate=annotate))

        # Save all results (glow is applied here in parallel)
        save_images(all_results, "output/demo")

    finally:
        db.close()


if __name__ == "__main__":
    main()
