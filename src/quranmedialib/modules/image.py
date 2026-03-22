"""Image processing utilities for QuranMediaLib."""

from PIL import Image, ImageChops, ImageEnhance, ImageFilter

from quranmedialib.types import Color, Padding

# === Helper Functions ===


def _compute_downscaled_size(image: Image.Image, scale: int) -> tuple[int, int]:
    """Compute a minimum 1x1 downscaled size for an image given an integer scale."""
    return (max(1, image.width // scale), max(1, image.height // scale))


# === Color Function ===


def color(image: Image.Image, color: Color = (255, 255, 255, 255)) -> Image.Image:
    """Multiplies the luminance of each pixel with the specified color.

    This function colorizes the image by converting it to grayscale and then
    multiplying it with a solid color layer. Alpha values are preserved.

    Args:
        image: The input PIL Image to colorize.
        color: The RGB or RGBA color to multiply with. If RGB, alpha defaults
            to 255. Values should be in range 0-255.

    Returns:
        The colorized PIL Image as a new object.
    """
    # Ensure color is RGBA
    if len(color) == 3:
        color = (*color, 255)

    # Convert to grayscale with alpha (LA) then back to RGBA for multiplication
    return ImageChops.multiply(image.convert("LA").convert("RGBA"), Image.new("RGBA", image.size, color))


# === Pad Function ===


def pad(image: Image.Image, padding: Padding = (20, 20, 20, 20), color: Color = (0, 0, 0, 0)) -> Image.Image:
    """Adds padding around the image filled with a solid color.

    Args:
        image: The input PIL Image.
        padding: A 4-tuple of (top, bottom, left, right) padding in pixels.
        color: The RGBA color for the padded border area.

    Returns:
        A new PIL Image containing the original image centered by the padding.
    """
    if len(color) == 3:
        color = (*color, 255)
    if len(image.mode) == 3:
        image = image.convert("RGBA")

    up, down, left, right = padding[0], padding[1], padding[2], padding[3]

    new_width = image.width + left + right
    new_height = image.height + up + down
    padded_image = Image.new("RGBA", (new_width, new_height), color=color)
    padded_image.paste(image, (left, up))
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
        glow_alpha = glow_alpha.point(lambda p: min(255, int(p * strength)))

    glow_layer = glow_color.convert("RGBA")
    glow_layer.putalpha(glow_alpha)

    # Build stack: Transparent Base -> Glow Layer -> Original Content
    result = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    result.alpha_composite(glow_layer)
    result.alpha_composite(img_rgba)

    return result


def _prepare_color_base(img_rgba: Image.Image, img_rgb: Image.Image, alpha: Image.Image) -> Image.Image:
    """Prepares the color base for the glow effect by bleeding colors into transparent areas.

    This prevents grey/dark edges when blurring RGBA images.
    """
    scale = 8
    small_size = _compute_downscaled_size(img_rgba, scale)
    small = img_rgba.resize(small_size, resample=Image.Resampling.BOX)
    color_base = small.resize(img_rgba.size, resample=Image.Resampling.NEAREST).convert("RGB")
    color_base.paste(img_rgb, mask=alpha)
    return color_base


def glow(image: Image.Image, strength: float = 1.0, radius: int = 50) -> Image.Image:
    """Applies a soft, radiant glow effect to the image.

    This function mimics a photorealistic glow by creating a multi-scale blur
    of the image's colors and layering it.

    **Behavior:**
    - For images with transparency (RGBA), the glow extends into transparent
    regions and is composited behind the original content.
    - For opaque images (RGB), it uses additive screen blending to ensure
    vibrancy without flattening highlights.

    **Performance Note:**
    Large images combined with large radius values (> 100) can be computationally
    expensive due to multiple blur passes.

    Args:
        image: The input PIL Image to process.
        strength: Intensity of the glow factor. Values > 1.0 make it more
            vibrant/opaque, while values < 1.0 fade it out. Defaults to 1.0.
        radius: The base spread of the glow in pixels. Larger values
            create a wider, softer falloff. Defaults to 50.

    Returns:
        A new PIL Image with the glow effect applied, preserving the
        original image mode.
    """
    if strength <= 0 or radius <= 0:
        return image.copy()

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

    # 1. Prepare the color base for the glow (downscaled for efficient blurring)
    color_base_scale = 8
    if is_opaque:
        # For opaque images, downscale directly from RGB for efficiency
        img_rgb = img_rgba.convert("RGB")
        color_base_size = _compute_downscaled_size(img_rgba, color_base_scale)
        color_base = img_rgb.resize(color_base_size, resample=Image.Resampling.BOX)
    else:
        # For RGBA, "bleed" colors into transparent areas to avoid grey edges
        color_base = _prepare_color_base(img_rgba, img_rgb, alpha)
        # Downscale the color base for efficient blurring
        color_base_size = _compute_downscaled_size(img_rgba, color_base_scale)
        color_base = color_base.resize(color_base_size, resample=Image.Resampling.BOX)

    # 2. Multi-scale blur sequence (downscaled)
    # Scaled radii to match downsampled space for equivalent visual effect
    # Original: [r/4, r/2, r, r*1.5] at full res → now scaled by 1/color_base_scale
    radii = [
        max(1, radius // 4 // color_base_scale),
        max(1, radius // 2 // color_base_scale),
        max(1, radius // color_base_scale),
        max(1, int(radius * 1.5) // color_base_scale),
    ]

    glow_color_size = color_base.size
    glow_color = Image.new("RGB", glow_color_size, (0, 0, 0))
    glow_alpha = None if is_opaque else Image.new("L", glow_color_size, 0)
    
    # Downscale alpha channel to match color_base size
    alpha_small = None if is_opaque else alpha.resize(glow_color_size, resample=Image.Resampling.BOX)

    for r in radii:
        # Color component: BoxBlur is O(1) vs GaussianBlur O(radius²)
        blur_c = color_base.filter(ImageFilter.BoxBlur(r))
        glow_color = ImageChops.screen(glow_color, blur_c)

        if glow_alpha is not None:
            # Alpha component: Use 'lighter' (MAX) blend to maximize spread
            blur_a = alpha_small.filter(ImageFilter.BoxBlur(r))
            glow_alpha = ImageChops.lighter(glow_alpha, blur_a)

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
