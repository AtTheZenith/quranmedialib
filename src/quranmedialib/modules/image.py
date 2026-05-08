"""Image processing utilities for QuranMediaLib."""

import logging
from typing import Literal

from PIL import Image, ImageChops, ImageEnhance, ImageFilter

from quranmedialib.types import Color, Padding, MAX_GLOW_RADIUS

__all__ = [
    "color",
    "glow",
    "pad",
]

# === Helper Functions ===


def _compute_downscaled_size(image: Image.Image, scale: int) -> tuple[int, int]:
    """Compute a minimum 1x1 downscaled size for an image given an integer scale."""
    return (max(1, image.width // scale), max(1, image.height // scale))


# === Color Function ===


def color(image: Image.Image, color: Color = (255, 255, 255, 255)) -> Image.Image:
    # sourcery skip: extract-duplicate-method
    """Multiplies the luminance of each pixel with the specified color.

    Treats the input's alpha channel (or luminance if L) as a mask for the new solid color.

    Args:
        image: The input PIL Image to colorize.
        color: The RGB or RGBA color to multiply with. If RGB, alpha defaults to 255.

    Returns:
        The colorized PIL Image as a new object.
    """
    if len(color) not in (3, 4):
        raise ValueError(f"Color must be RGB or RGBA tuple (3 or 4 values), got {len(color)}")

    # Ensure color is RGBA
    rgba_color = color if len(color) == 4 else (*color, 255)

    # Fast path for mask-like images or alpha images
    if image.mode in ("RGBA", "LA", "L"):
        mask = image.getchannel("A") if "A" in image.mode else image
        result = Image.new("RGBA", image.size, rgba_color)
        result.putalpha(mask)
        return result

    # Fallback for RGB/etc: use luminance as mask
    mask = image.convert("L")
    result = Image.new("RGBA", image.size, rgba_color)
    result.putalpha(mask)
    return result


# === Pad Function ===


def pad(image: Image.Image, padding: Padding = Padding(20, 20, 20, 20), color: Color = (0, 0, 0, 0)) -> Image.Image:
    """Adds padding around the image filled with a solid color.

    Args:
        image: The input PIL Image.
        padding: A Padding object or 4-tuple of (top, bottom, left, right).
        color: The RGBA color for the padded border area.

    Returns:
        A new PIL Image containing the original image offset by the padding.

    Raises:
        ValueError: If color tuple length is not 3 or 4.
    """
    if len(color) not in (3, 4):
        raise ValueError(f"Color must be RGB or RGBA tuple (3 or 4 values), got {len(color)} values: {color}")

    # Ensure image is RGBA for transparency support in padding
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # If padding is a tuple, convert to Padding object for attribute access
    if not isinstance(padding, Padding):
        padding = Padding(*padding)

    new_width = max(1, image.width + padding.horizontal)
    new_height = max(1, image.height + padding.vertical)
    padded_image = Image.new("RGBA", (new_width, new_height), color=color)
    padded_image.paste(image, (padding.left, padding.top))

    return padded_image


# === Glow Function ===


def _glow_rgba(
    strength: float,
    glow_alpha: Image.Image,
    glow_color: Image.Image,
    img_rgba: Image.Image,
) -> Image.Image:
    """Composite glow layer behind original content for RGBA images."""
    if strength != 1.0:
        glow_alpha = ImageEnhance.Brightness(glow_alpha).enhance(strength)

    glow_layer = glow_color.convert("RGBA")
    glow_layer.putalpha(glow_alpha)

    # Build stack: Glow Layer -> Original Content
    result = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    result.alpha_composite(glow_layer)
    result.alpha_composite(img_rgba)
    return result


def _prepare_color_base(
    img_rgba: Image.Image, img_rgb: Image.Image, alpha: Image.Image, small_size: tuple[int, int]
) -> Image.Image:
    """Prepares the color base for the glow effect by bleeding colors into transparent areas."""
    small_rgba = img_rgba.resize(small_size, resample=Image.Resampling.BOX)
    small_rgb = small_rgba.convert("RGB")
    alpha_small = alpha.resize(small_size, resample=Image.Resampling.BOX)
    small_rgb.paste(img_rgb.resize(small_size, resample=Image.Resampling.BOX), mask=alpha_small)
    return small_rgb


def glow(
    image: Image.Image,
    strength: float = 1.0,
    radius: int = 50,
    quality: Literal["fast", "balanced", "quality"] = "balanced",
) -> Image.Image:
    """Applies a soft, radiant glow effect to the image.

    This function mimics a photorealistic glow by creating a multi-scale blur
    of the image's colors and layering it.

    **Behavior:**
    - For images with transparency (RGBA), the glow extends into transparent
    regions and is composited behind the original content.
    - For opaque images (RGB), it uses additive screen blending to ensure
    vibrancy without flattening highlights.

    **Quality Modes:**
    - ``"fast"``: GaussianBlur downsampled 4x. Fast Gaussian option with
      good quality-to-speed ratio.
    - ``"balanced"``: GaussianBlur downsampled 2x. Balance between speed and
      quality. Recommended default.
    - ``"quality"``: GaussianBlur at full resolution. True Gaussian distribution,
      smoothest results but slowest for large radii.

    **Performance Note:**
    Large images combined with large radius values (> 100) can be computationally
    expensive. The "fast" mode uses 4x downsampling, "balanced" uses 2x,
    and "quality" uses full resolution Gaussian blur. Larger radii and higher
    resolutions increase processing time.

    Args:
        image: The input PIL Image to process.
        strength: Intensity of the glow factor. Values > 1.0 make it more
            vibrant/opaque, while values < 1.0 fade it out. Defaults to 1.0.
        radius: The base spread of the glow in pixels. Larger values
            create a wider, softer falloff. Defaults to 50.
        quality: The blur quality mode. "fast" uses GaussianBlur downsampled 4x,
            "balanced" uses GaussianBlur downsampled 2x, and "quality" uses
            full-resolution GaussianBlur. Defaults to "balanced".

    Returns:
        A new PIL Image with the glow effect applied, preserving the
        original image mode.
    """
    if strength <= 0 or radius <= 0:
        return image.copy()

    if radius > MAX_GLOW_RADIUS:
        logger = logging.getLogger(__name__)
        logger.warning("Glow radius %d exceeds maximum %d, clamping", radius, MAX_GLOW_RADIUS)
        radius = MAX_GLOW_RADIUS

    # Capture initial state
    initial_mode = image.mode

    # Determine opacity early (skip expensive getextrema for RGB mode)
    is_opaque = initial_mode == "RGB"

    # Prepare RGBA version and alpha channel
    img_rgba = image.convert("RGBA")
    alpha = img_rgba.getchannel("A")

    # For non-opaque images, verify full opacity by checking alpha channel
    if not is_opaque:
        is_opaque = alpha.getextrema() == (255, 255)

    # Defer RGB conversion until needed
    img_rgb = None if is_opaque else img_rgba.convert("RGB")

    # 1. Prepare the color base for the glow (downscaled based on quality mode)
    quality_scale = {"fast": 4, "balanced": 2, "quality": 1}
    color_base_scale = quality_scale[quality]
    color_base_size = _compute_downscaled_size(img_rgba, color_base_scale)
    if is_opaque:
        # For opaque images, downscale directly from RGB for efficiency
        img_rgb = img_rgba.convert("RGB")
        color_base = img_rgb.resize(color_base_size, resample=Image.Resampling.BOX)
    else:
        # For RGBA, "bleed" colors into transparent areas to avoid grey edges
        # Reuse pre-computed color_base_size (PERF-012: avoid redundant calculation)
        color_base = _prepare_color_base(img_rgba, img_rgb, alpha, color_base_size)

    # 2. Multi-scale blur sequence (downscaled)
    # Scaled radii to match downsampled space for equivalent visual effect
    # Original: [r/4, r/2, r, r*1.5] at full res → now scaled by 1/color_base_scale
    # After upscaling, effective blur = r_downsampled * color_base_scale ≈ r_original
    # Use floating point; minimum radius varies by quality mode (fast needs larger minimum)
    min_radius = 1.0 if quality == "fast" else 0.5
    radii = [
        max(min_radius, radius / 4 / color_base_scale),
        max(min_radius, radius / 2 / color_base_scale),
        max(min_radius, radius / color_base_scale),
        max(min_radius, radius * 1.5 / color_base_scale),
    ]

    # Pre-allocate blur buffers — reuse across radii iterations
    glow_color = Image.new("RGB", color_base_size, (0, 0, 0))
    glow_alpha = None if is_opaque else Image.new("L", color_base_size, 0)
    alpha_small = None if is_opaque else alpha.resize(color_base_size, resample=Image.Resampling.BOX)

    # Gaussian blur with radii scaled to downsampled space
    for r in radii:
        # PERF: Filter results are processed directly into screen/lighter to avoid buffer copies
        blur_res = color_base.filter(ImageFilter.GaussianBlur(r))
        glow_color = ImageChops.screen(glow_color, blur_res)

        if glow_alpha is not None:
            blur_alpha_res = alpha_small.filter(ImageFilter.GaussianBlur(r))
            glow_alpha = ImageChops.lighter(glow_alpha, blur_alpha_res)

    # 3. Upscale glow result to original size
    glow_color = glow_color.resize(img_rgba.size, resample=Image.Resampling.BILINEAR)
    if glow_alpha is not None:
        glow_alpha = glow_alpha.resize(img_rgba.size, resample=Image.Resampling.BILINEAR)

    # 4. Final Assembly
    if is_opaque:
        # Additive Screen blend for RGB images
        if strength != 1.0:
            glow_color = ImageEnhance.Brightness(glow_color).enhance(strength)
        result = ImageChops.screen(img_rgb, glow_color)
    else:
        result = _glow_rgba(strength, glow_alpha, glow_color, img_rgba)
    return result.convert(initial_mode)
