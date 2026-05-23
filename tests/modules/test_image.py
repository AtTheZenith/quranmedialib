"""Tests for the image module (image effects and transformations).

This module contains tests for verifying image processing functions including:
- Color transformation (luminance-based colorization)
- Padding operations (4-directional margins)
- Glow effects (multiple quality modes, RGBA/RGB handling)
- Brightness analysis across different glow configurations
"""

import os

import pytest
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
    hist = img.histogram()
    n = sum(hist)
    if n == 0:
        return {k: 0.0 for k in ["mean", "median", "q1", "q3", "iqr", "p10", "p90", "min", "max", "range", "stdev"]}

    # 1. Mean and Variance for Stdev
    sum_vals = 0
    sum_sq_vals = 0
    for i, count in enumerate(hist):
        sum_vals += i * count
        sum_sq_vals += (i * i) * count

    mean_brightness = sum_vals / n
    variance = (sum_sq_vals / n) - (mean_brightness**2)
    stdev_brightness = variance**0.5 if variance > 0 else 0.0

    # 2. Percentiles using cumulative distribution
    def get_percentile(p: float) -> int:
        target = p * n
        cumulative = 0
        for i, count in enumerate(hist):
            cumulative += count
            if cumulative >= target:
                return i
        return 255

    median_brightness = get_percentile(0.5)
    q1_brightness = get_percentile(0.25)
    q3_brightness = get_percentile(0.75)
    p10_brightness = get_percentile(0.1)
    p90_brightness = get_percentile(0.9)

    # 3. Min, max, range
    min_brightness = next((i for i, count in enumerate(hist) if count > 0), 0)
    max_brightness = next((i for i in range(255, -1, -1) if hist[i] > 0), 255)

    return {
        "mean": mean_brightness,
        "median": float(median_brightness),
        "q1": float(q1_brightness),
        "q3": float(q3_brightness),
        "iqr": float(q3_brightness - q1_brightness),
        "p10": float(p10_brightness),
        "p90": float(p90_brightness),
        "min": float(min_brightness),
        "max": float(max_brightness),
        "range": float(max_brightness - min_brightness),
        "stdev": stdev_brightness,
    }


def _print_stats(label: str, stats: dict[str, float]) -> None:
    """Print brightness statistics in a formatted way."""
    fmt = (
        f"  {label:10s}: mean={stats['mean']:6.2f}, "
        f"median={stats['median']:6.2f}, q1={stats['q1']:6.2f}, "
        f"q3={stats['q3']:6.2f}, IQR={stats['iqr']:6.2f}, "
        f"p10={stats['p10']:6.2f}, p90={stats['p90']:6.2f}, "
        f"stdev={stats['stdev']:6.2f}"
    )
    print(fmt)


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

    # Use 500x500 image for realistic testing (glow needs sufficient resolution)
    img_size = 500

    # Create test image with transparency (white circle on transparent)
    test_image_rgba = Image.new("RGBA", (img_size, img_size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(test_image_rgba)
    draw.ellipse([150, 150, 350, 350], fill=(255, 255, 255, 255))

    # Test all quality modes on RGBA
    for quality in ["fast", "balanced", "quality"]:
        glowed = glow(test_image_rgba, strength=1.5, radius=30, quality=quality)
        _save_test_image(glowed, f"glowed_rgba_{quality}.png")

    # Test all quality modes on RGB
    test_image_rgb = Image.new("RGB", (img_size, img_size), color=(30, 30, 30))
    draw_rgb = ImageDraw.Draw(test_image_rgb)
    draw_rgb.ellipse([200, 200, 300, 300], fill=(255, 255, 255))

    for quality in ["fast", "balanced", "quality"]:
        glowed = glow(test_image_rgb, strength=1.5, radius=30, quality=quality)
        _save_test_image(glowed, f"glowed_rgb_{quality}.png")

    # Test opaque RGBA
    test_image_opaque = Image.new("RGBA", (img_size, img_size), color=(30, 30, 30, 255))
    draw_opaque = ImageDraw.Draw(test_image_opaque)
    draw_opaque.ellipse([200, 200, 300, 300], fill=(0, 255, 0, 255))

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

    # Apply generous padding to simulate realistic 500x500 usage
    # This ensures downsampled modes have enough pixels to work with
    target_size = 500
    w, h = wimage.size
    pad_h = (target_size - w) // 2
    pad_v = (target_size - h) // 2
    padded = pad(wimage, Padding(pad_v, pad_v, pad_h, pad_h), color=(0, 0, 0, 0))

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

    # Target size for realistic testing (500x500 equivalent)
    target_size = 500

    # Create comparison strip for each word
    for word, word_name in words:
        wimage = get_wimage(word, word_config)
        # Apply generous padding to reach target size
        w, h = wimage.size
        pad_h = (target_size - w) // 2
        pad_v = (target_size - h) // 2
        padded = pad(wimage, Padding(pad_v, pad_v, pad_h, pad_h), color=(0, 0, 0, 0))

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

    output_dir = "./output/test/image"

    # Avoid redundant generation: check if at least one required image exists
    # If not, run the generation tests.
    if not os.path.exists(os.path.join(output_dir, "glowed_rgba_fast.png")):
        test_glow_quality_modes()
        test_glow_on_padded_wimage()
        test_glow_wimage_comparison()

    # Analyze RGBA glow images

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


# === Validation Tests ===


def test_color_none_image() -> None:
    """Test that color raises error for None image."""
    with pytest.raises(AttributeError):
        color(None, color=(255, 0, 0, 255))  # type: ignore


def test_color_invalid_color_tuple() -> None:
    """Test that color raises ValueError for invalid color tuples."""
    test_image = Image.new("RGBA", (10, 10))

    # Too short color tuple (2 elements)
    with pytest.raises(ValueError, match="Color must be RGB or RGBA tuple"):
        color(test_image, color=(255, 0))  # type: ignore

    # Too long color tuple (5 elements)
    with pytest.raises(ValueError, match="Color must be RGB or RGBA tuple"):
        color(test_image, color=(255, 0, 0, 255, 0))  # type: ignore


def test_pad_invalid_color_tuple() -> None:
    """Test that pad raises ValueError for invalid color tuples."""
    test_image = Image.new("RGBA", (10, 10))

    # Too short color tuple (1 element)
    with pytest.raises(ValueError, match="Color must be RGB or RGBA tuple"):
        pad(test_image, color=(255,))  # type: ignore

    # Too long color tuple (5 elements)
    with pytest.raises(ValueError, match="Color must be RGB or RGBA tuple"):
        pad(test_image, color=(255, 0, 0, 255, 0))  # type: ignore


def test_pad_none_image() -> None:
    """Test that pad raises error for None image."""
    with pytest.raises(AttributeError):
        pad(None, padding=Padding(10, 10, 10, 10))  # type: ignore


def test_pad_negative_padding() -> None:
    """Test that pad handles negative padding by producing smaller image."""
    test_image = Image.new("RGBA", (100, 100))
    negative_padding = Padding(-10, -10, -10, -10)

    # Negative padding creates a smaller image (80x80 instead of 100x100)
    result = pad(test_image, padding=negative_padding)
    assert result.size == (80, 80)  # 100 - 2*10 = 80


def test_glow_none_image() -> None:
    """Test that glow raises error for None image."""
    with pytest.raises(AttributeError):
        glow(None, strength=1.0, radius=50)  # type: ignore


def test_glow_negative_strength() -> None:
    """Test that glow returns copy for negative strength."""
    test_image = Image.new("RGBA", (100, 100))
    result = glow(test_image, strength=-1.0, radius=50)
    # Should return a copy, not raise error
    assert result is not test_image
    assert result.size == test_image.size


def test_glow_negative_radius() -> None:
    """Test that glow returns copy for negative radius."""
    test_image = Image.new("RGBA", (100, 100))
    result = glow(test_image, strength=1.0, radius=-10)
    # Should return a copy, not raise error
    assert result is not test_image
    assert result.size == test_image.size


def test_glow_zero_radius() -> None:
    """Test that glow returns copy for zero radius."""
    test_image = Image.new("RGBA", (100, 100))
    result = glow(test_image, strength=1.0, radius=0)
    # Should return a copy, not raise error
    assert result is not test_image
    assert result.size == test_image.size


def test_glow_invalid_quality_mode() -> None:
    """Test that glow raises error for invalid quality mode."""
    test_image = Image.new("RGBA", (100, 100))

    with pytest.raises(Exception):
        glow(test_image, strength=1.0, radius=50, quality="invalid_mode")  # type: ignore


# === Round 2: Additional Validation Tests ===


def test_pad_negative_padding_produces_minimal_image() -> None:
    """Test that pad with extreme negative padding produces at least a 1x1 image."""
    test_image = Image.new("RGBA", (100, 100))
    negative_padding = Padding(-1000, -1000, -1000, -1000)
    result = pad(test_image, padding=negative_padding)
    assert result.size[0] >= 1
    assert result.size[1] >= 1


def test_color_color_values_out_of_range() -> None:
    """Test that color() handles out-of-range color values."""
    test_image = Image.new("RGBA", (10, 10))
    result = color(test_image, color=(300, 300, 300))
    assert result is not None
    assert result.size == test_image.size


def test_pad_zero_padding() -> None:
    """Test that pad with zero padding returns same-size image."""
    test_image = Image.new("RGBA", (100, 100))
    zero_padding = Padding(0, 0, 0, 0)
    result = pad(test_image, padding=zero_padding)
    assert result.size == (100, 100)


def test_pad_negative_color_values() -> None:
    """Test that pad handles negative color values."""
    test_image = Image.new("RGBA", (10, 10))
    result = pad(test_image, color=(-1, -1, -1))
    assert result is not None


def test_glow_strength_zero() -> None:
    """Test that glow with strength=0 returns a copy."""
    test_image = Image.new("RGBA", (100, 100))
    result = glow(test_image, strength=0.0, radius=10)
    assert result is not test_image
    assert result.size == test_image.size


@pytest.mark.benchmark
def test_glow_quality_modes_benchmark(request: pytest.FixtureRequest) -> None:
    """Benchmark glow quality modes (fast/balanced/quality) on 500x500 RGBA image."""
    import time

    test_image = Image.new("RGBA", (500, 500), color=(255, 255, 255, 255))
    draw = ImageDraw.Draw(test_image)
    draw.rectangle([200, 200, 300, 300], fill=(255, 0, 0, 255))

    modes = ["fast", "balanced", "quality"]
    timings = {}

    for mode in modes:
        start = time.perf_counter()
        for _ in range(10):
            glow(test_image, strength=0.5, radius=20, quality=mode)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 10) * 1000
        timings[mode] = avg_ms

    parts = [f"{mode}={timings[mode]:.1f}ms" for mode in modes]
    request.node.benchmark_data = parts

    print("\nGlow Benchmark (500x500, 10 iterations):")
    for mode in modes:
        print(f"  {mode}: {timings[mode]:.1f}ms")
