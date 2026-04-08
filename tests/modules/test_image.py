"""Tests for the image module (image effects and transformations).

This module contains tests for verifying image processing functions including:
- Color transformation (luminance-based colorization)
- Padding operations (4-directional margins)
- Glow effects (multiple quality modes, RGBA/RGB handling)
- Brightness analysis across different glow configurations
"""

import os
import statistics

from PIL import Image, ImageDraw

from quranmedialib.modules.image import color, glow, pad
from quranmedialib.modules.wimage import get_wimage
from quranmedialib.types import FontResource, Padding, WordConfig


def _save_test_image(img: Image.Image, filename: str) -> None:
    output_dir = "./output/test/image"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    img.save(output_path)
    print(f"Saved image to {output_path}")


def _create_default_word_config() -> WordConfig:
    """Create a default word configuration for testing."""
    return WordConfig(
        font=FontResource.from_packaged("hafs.otf", "Hafs"),
        font_size=72,
        max_rows_per_page=2,
        row_spacing=20,
        word_spacing=13,
        word_padding=Padding(30, 30, 30, 30),
    )


def _analyze_image_brightness(filepath: str) -> dict[str, float]:
    """Calculate comprehensive brightness statistics of an image.

    Returns a dict with mean, median, q1, q3, iqr, p10, p90, min, max, range, stdev.
    """
    img = Image.open(filepath).convert("L")  # Convert to grayscale
    pixels = sorted(list(img.get_flattened_data()))
    n = len(pixels)

    # Basic stats
    median_brightness = statistics.median(pixels)
    mean_brightness = statistics.mean(pixels)

    # Quartiles
    q1_idx = n // 4
    q3_idx = (3 * n) // 4
    q1_brightness = pixels[q1_idx]  # 25th percentile
    q3_brightness = pixels[q3_idx]  # 75th percentile
    iqr = q3_brightness - q1_brightness  # Interquartile range

    # Percentiles (10th, 90th)
    p10_idx = n // 10
    p90_idx = (9 * n) // 10
    p10_brightness = pixels[p10_idx]
    p90_brightness = pixels[p90_idx]

    # Min, max, range
    min_brightness = pixels[0]
    max_brightness = pixels[-1]
    brightness_range = max_brightness - min_brightness

    # Standard deviation
    stdev_brightness = statistics.stdev(pixels) if n > 1 else 0

    return {
        "mean": mean_brightness,
        "median": median_brightness,
        "q1": q1_brightness,
        "q3": q3_brightness,
        "iqr": iqr,
        "p10": p10_brightness,
        "p90": p90_brightness,
        "min": min_brightness,
        "max": max_brightness,
        "range": brightness_range,
        "stdev": stdev_brightness,
    }


def _print_stats(label: str, stats: dict[str, float]) -> None:
    """Print brightness statistics in a formatted way."""
    print(f"  {label:10s}: mean={stats['mean']:6.2f}, median={stats['median']:6.2f}, q1={stats['q1']:6.2f}, q3={stats['q3']:6.2f}, IQR={stats['iqr']:6.2f}, p10={stats['p10']:6.2f}, p90={stats['p90']:6.2f}, stdev={stats['stdev']:6.2f}")


def test_color() -> None:
    print("Testing color function...")
    test_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
    colored_image = color(test_image)
    _save_test_image(colored_image, "colored_image.png")
    print("test_color passed.")


def test_pad() -> None:
    print("Testing pad function...")
    test_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
    padded_image = pad(test_image)
    _save_test_image(padded_image, "padded_image.png")
    print("test_pad passed.")


def test_glow() -> None:
    print("Testing glow function...")
    # Transparent background with a white circle
    test_image = Image.new("RGBA", (200, 200), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(test_image)
    draw.ellipse([50, 50, 150, 150], fill=(255, 255, 255, 255))

    glowed_image = glow(test_image, strength=1.5, radius=30)
    _save_test_image(glowed_image, "glowed_image_rgba.png")

    # RGB test case (white circle on dark grey background)
    test_image_rgb = Image.new("RGB", (200, 200), color=(30, 30, 30))
    draw_rgb = ImageDraw.Draw(test_image_rgb)
    draw_rgb.ellipse([70, 70, 130, 130], fill=(255, 255, 255))
    glowed_image_rgb = glow(test_image_rgb, strength=1.5, radius=30)
    _save_test_image(glowed_image_rgb, "glowed_image_rgb.png")

    # Opaque RGBA test case (RGBA with all alpha=255)
    test_image_opaque = Image.new("RGBA", (200, 200), color=(30, 30, 30, 255))
    draw_opaque = ImageDraw.Draw(test_image_opaque)
    draw_opaque.ellipse([70, 70, 130, 130], fill=(0, 255, 0, 255))
    glowed_image_opaque = glow(test_image_opaque, strength=1.5, radius=30)
    _save_test_image(glowed_image_opaque, "glowed_image_opaque_rgba.png")

    print("test_glow passed.")


def test_glow_quality_modes() -> None:
    """Test all three quality modes with both RGB and RGBA images."""
    print("Testing glow quality modes...")

    # Create test image with transparency (white circle on transparent)
    test_image_rgba = Image.new("RGBA", (200, 200), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(test_image_rgba)
    draw.ellipse([50, 50, 150, 150], fill=(255, 255, 255, 255))

    # Test all quality modes on RGBA
    for quality in ["fast", "balanced", "quality"]:
        glowed = glow(test_image_rgba, strength=1.5, radius=30, quality=quality)
        _save_test_image(glowed, f"glowed_rgba_{quality}.png")

    # Test all quality modes on RGB
    test_image_rgb = Image.new("RGB", (200, 200), color=(30, 30, 30))
    draw_rgb = ImageDraw.Draw(test_image_rgb)
    draw_rgb.ellipse([70, 70, 130, 130], fill=(255, 255, 255))

    for quality in ["fast", "balanced", "quality"]:
        glowed = glow(test_image_rgb, strength=1.5, radius=30, quality=quality)
        _save_test_image(glowed, f"glowed_rgb_{quality}.png")

    # Test opaque RGBA
    test_image_opaque = Image.new("RGBA", (200, 200), color=(30, 30, 30, 255))
    draw_opaque = ImageDraw.Draw(test_image_opaque)
    draw_opaque.ellipse([70, 70, 130, 130], fill=(0, 255, 0, 255))

    for quality in ["fast", "balanced", "quality"]:
        glowed = glow(test_image_opaque, strength=1.5, radius=30, quality=quality)
        _save_test_image(glowed, f"glowed_opaque_rgba_{quality}.png")

    print("test_glow_quality_modes passed.")


def test_glow_on_padded_wimage() -> None:
    """Demonstrate glow effect on padded word images with all quality modes."""
    print("Testing glow on padded wimage...")

    # Generate a word image (Arabic word)
    word_config = _create_default_word_config()
    wimage = get_wimage("الله", word_config)

    # Apply additional padding (simulating layout spacing)
    padded = pad(wimage, Padding(50, 50, 50, 50), color=(0, 0, 0, 0))

    # Test all quality modes
    for quality in ["fast", "balanced", "quality"]:
        glowed = glow(padded, strength=1.0, radius=50, quality=quality)
        _save_test_image(glowed, f"wimage_glow_{quality}.png")

    print("test_glow_on_padded_wimage passed.")


def test_glow_wimage_comparison() -> None:
    """Create a side-by-side comparison of all glow quality modes on wimage."""
    print("Testing glow wimage comparison...")

    # Generate word images
    word_config = _create_default_word_config()
    # Use transliterated names for Windows compatibility
    words = [("الله", "allah"), ("محمد", "mohammed"), ("قرآن", "quran")]

    # Create comparison strip for each word
    for word, word_name in words:
        wimage = get_wimage(word, word_config)
        padded = pad(wimage, Padding(50, 50, 50, 50), color=(0, 0, 0, 0))

        # Generate all quality modes
        fast_glow = glow(padded, strength=1.0, radius=50, quality="fast")
        balanced_glow = glow(padded, strength=1.0, radius=50, quality="balanced")
        quality_glow = glow(padded, strength=1.0, radius=50, quality="quality")

        # Create horizontal strip for comparison
        total_width = padded.width * 4  # original + 3 glow modes
        comparison = Image.new("RGBA", (total_width, padded.height), (0, 0, 0, 0))

        comparison.paste(padded, (0, 0))
        comparison.paste(fast_glow, (padded.width, 0))
        comparison.paste(balanced_glow, (padded.width * 2, 0))
        comparison.paste(quality_glow, (padded.width * 3, 0))

        _save_test_image(comparison, f"wimage_comparison_{word_name}.png")

    print("test_glow_wimage_comparison passed.")


def test_glow_brightness_analysis() -> None:
    """Analyze and print comprehensive brightness statistics for all glow quality modes.

    This test generates the glow images (if not already present) and then analyzes
    their brightness using multiple statistical measures: mean, median, quartiles
    (Q1, Q3), IQR, percentiles (P10, P90), and standard deviation.

    This helps verify that the three quality modes have comparable brightness levels.
    """
    print("\n=== Glow Brightness Analysis ===\n")

    # First ensure the test images exist by running the generation tests
    test_glow_quality_modes()
    test_glow_on_padded_wimage()
    test_glow_wimage_comparison()

    output_dir = "./output/test/image"

    # Analyze RGBA glow images
    print("RGBA Glow Images (white circle on transparent):")
    print("-" * 120)
    for quality in ["fast", "balanced", "quality"]:
        filepath = os.path.join(output_dir, f"glowed_rgba_{quality}.png")
        if os.path.exists(filepath):
            stats = _analyze_image_brightness(filepath)
            _print_stats(quality, stats)

    print()

    # Analyze RGB glow images
    print("RGB Glow Images (white circle on dark grey):")
    print("-" * 120)
    for quality in ["fast", "balanced", "quality"]:
        filepath = os.path.join(output_dir, f"glowed_rgb_{quality}.png")
        if os.path.exists(filepath):
            stats = _analyze_image_brightness(filepath)
            _print_stats(quality, stats)

    print()

    # Analyze wimage glow images
    print("Wimage Glow Images (Arabic word):")
    print("-" * 120)
    for quality in ["fast", "balanced", "quality"]:
        filepath = os.path.join(output_dir, f"wimage_glow_{quality}.png")
        if os.path.exists(filepath):
            stats = _analyze_image_brightness(filepath)
            _print_stats(quality, stats)

    print()

    # Analyze comparison strips
    print("Comparison Strips (side-by-side):")
    print("-" * 120)
    # Use transliterated names for Windows compatibility
    for word, word_name in [("الله", "allah"), ("محمد", "mohammed"), ("قرآن", "quran")]:
        filepath = os.path.join(output_dir, f"wimage_comparison_{word_name}.png")
        if os.path.exists(filepath):
            img = Image.open(filepath).convert("L")
            w = img.width // 4
            for i, quality in enumerate(["original", "fast", "balanced", "quality"]):
                crop = img.crop((i * w, 0, (i + 1) * w, img.height))
                # Save crop temporarily to reuse _analyze_image_brightness
                crop_path = os.path.join(output_dir, f"_temp_crop_{word_name}_{quality}.png")
                crop.save(crop_path)
                stats = _analyze_image_brightness(crop_path)
                _print_stats(f"{word_name} {quality}", stats)
                # Clean up temp crop
                if os.path.exists(crop_path):
                    os.remove(crop_path)
            print()

    print("test_glow_brightness_analysis passed.")


if __name__ == "__main__":
    test_color()
    test_pad()
    test_glow()
    test_glow_quality_modes()
    test_glow_on_padded_wimage()
    test_glow_wimage_comparison()
    test_glow_brightness_analysis()
    print("All image tests completed successfully.")
