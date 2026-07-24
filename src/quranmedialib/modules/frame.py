from __future__ import annotations

from PIL import Image

from quranmedialib.types import (
    Color,
    FrameConfig,
    HorizontalAlignment,
    Layerable,
    VerticalAlignment,
)


class Frame:
    """Composition class for layering images onto a fixed-size canvas.

    Attributes:
        config: Configuration for canvas size, padding, and default alignments.
        image: The RGBA canvas image.
    """

    def __init__(self, config: FrameConfig):
        """Initialize the Frame with a transparent RGBA canvas.

        Args:
            config: Framing configuration.
        """
        self.config = config
        self.image = Image.new("RGBA", (config.max_width, config.image_height), (0, 0, 0, 0))

    def layer(
        self,
        image: Image.Image | Layerable,
        alignment: tuple[HorizontalAlignment, VerticalAlignment] | None = None,
        offset: tuple[int, int] | None = None,
        text_color: Color | None = None,
        **kwargs,
    ) -> None:
        """Layer an image or layerable object onto the canvas using specified alignment and offset.

        Args:
            image: The image or layerable object to layer.
            alignment: Optional override for (horizontal, vertical) alignment.
            offset: Optional (x, y) offset to shift the image.
            text_color: Color to use when pasting an 'L' mode mask.
            **kwargs: Additional arguments passed to Layerable.layer().
        """
        # 1. Determine alignment and anchor
        h_align = alignment[0] if alignment else self.config.wimage_horizontal_align
        v_align = alignment[1] if alignment else self.config.wimage_vertical_align

        # We need the dimensions of the object to calculate alignment
        # For PIL Images, it's simple. For Layerables, we expect them to have .width and .height
        # (or we assume they know how to handle their own size relative to the anchor).
        # VImage has .width and .height.

        obj_width = image.width if hasattr(image, "width") else (image.width if isinstance(image, Image.Image) else 0)
        obj_height = (
            image.height if hasattr(image, "height") else (image.height if isinstance(image, Image.Image) else 0)
        )

        rendered_width = kwargs.get("rendered_width", obj_width)
        rendered_height = kwargs.get("rendered_height", obj_height)

        if h_align == HorizontalAlignment.LEFT:
            x = self.config.padding.left
        elif h_align == HorizontalAlignment.RIGHT:
            x = self.config.max_width - rendered_width - self.config.padding.right
        else:
            x = self.config.padding.left + (self.config.content_width - rendered_width) // 2

        if v_align == VerticalAlignment.TOP:
            y = self.config.padding.top
        elif v_align == VerticalAlignment.BOTTOM:
            y = self.config.image_height - rendered_height - self.config.padding.bottom
        else:
            y = self.config.padding.top + (self.config.available_height - rendered_height) // 2

        dx, dy = offset or (self.config.wimage_x_offset, self.config.wimage_y_offset)
        x += dx
        y += dy

        # 2. Delegate rendering
        if isinstance(image, Layerable):
            image.layer(self.image, x, y, **kwargs)
        elif image.mode == "L":
            self.image.paste(text_color or (255, 255, 255, 255), (x, y), mask=image)
        elif image.mode == "RGBA":
            self.image.alpha_composite(image, dest=(x, y))
        else:
            self.image.paste(image, (x, y))

    def render(self) -> Image.Image:
        """Return the final composed image.

        Returns:
            The RGBA canvas image.
        """
        return self.image
