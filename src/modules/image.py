from typing import TypeAlias
from PIL import Image, ImageChops, ImageFilter, ImageEnhance

ColorType: TypeAlias = tuple[int, int, int] | tuple[int, int, int, int]
PaddingType: TypeAlias = tuple[int, int, int, int]


# === Helper Functions ===


def _compute_downscaled_size(image: Image.Image, scale: int) -> tuple[int, int]:
    """Compute a minimum 1x1 downscaled size for an image given an integer scale."""
    return (max(1, image.width // scale), max(1, image.height // scale))


# === Color Function ===


def color(image: Image.Image, color: ColorType = (255, 255, 255, 255)) -> Image.Image:
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


def pad(image: Image.Image, padding: PaddingType = (20, 20, 20, 20), color: ColorType = (0, 0, 0, 0)) -> Image.Image:
    """Adds padding around the image filled with a solid color.

    Args:
        image: The input PIL Image.
        padding: A 4-tuple of (top, bottom, left, right) padding in pixels.
        color: The RGBA color for the padded border area.

    Returns:
        A new PIL Image containing the original image centered by the padding.
    """
    # Ensure color is RGBA
    if len(color) == 3:
        color = (*color, 255)

    new_width = image.width + padding[2] + padding[3]
    new_height = image.height + padding[0] + padding[1]
    padded_image = Image.new("RGBA", (new_width, new_height), color=color)
    padded_image.paste(image, (padding[2], padding[0]))
    return padded_image


# === Glow Function ===


def _glow_rgba(strength, glow_alpha, glow_color, img_rgba):
    # Composite BEHIND original content for RGBA images
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
    expensive due to multiple Gaussian blur passes.

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

    # Prepare RGBA and RGB versions for processing
    img_rgba = image.convert("RGBA")
    img_rgb = img_rgba.convert("RGB")
    alpha = img_rgba.getchannel("A")

    # Determine opacity (inline as it is trivial)
    is_opaque = (initial_mode == "RGB") or (alpha.getextrema() == (255, 255))

    # 1. Prepare the color base for the glow
    if is_opaque:
        # For opaque images, the glow base is simply the image content
        color_base = img_rgb
    else:
        # For RGBA, "bleed" colors into transparent areas to avoid grey edges
        color_base = _prepare_color_base(img_rgba, img_rgb, alpha)

    # 2. Multi-scale blur sequence
    # We combine multiple radii to create a smoother, more natural falloff (Airy disk mimicry)
    radii = [radius // 4, radius // 2, radius, int(radius * 1.5)]

    glow_color = Image.new("RGB", img_rgba.size, (0, 0, 0))
    glow_alpha = None if is_opaque else Image.new("L", img_rgba.size, 0)

    for r in radii:
        if r < 1:
            continue

        # Color component: Screen blending maintains vibrancy and avoids clipping
        blur_c = color_base.filter(ImageFilter.GaussianBlur(r))
        glow_color = ImageChops.screen(glow_color, blur_c)

        if glow_alpha is not None:
            # Alpha component: Use 'lighter' (MAX) blend to maximize spread
            blur_a = alpha.filter(ImageFilter.GaussianBlur(r))
            glow_alpha = ImageChops.lighter(glow_alpha, blur_a)

    # 3. Final Assembly
    if is_opaque:
        # Additive Screen blend for RGB images
        if strength != 1.0:
            glow_color = ImageEnhance.Brightness(glow_color).enhance(strength)
        result = ImageChops.screen(img_rgb, glow_color)
    else:
        result = _glow_rgba(strength, glow_alpha, glow_color, img_rgba)
    return result.convert(initial_mode)
