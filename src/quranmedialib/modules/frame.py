from __future__ import annotations

from PIL import Image

from quranmedialib.types import (
    Color,
    FrameConfig,
    HorizontalAlignment,
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
        image: Image.Image,
        alignment: tuple[HorizontalAlignment, VerticalAlignment] | None = None,
        offset: tuple[int, int] | None = None,
        text_color: Color | None = None,
    ) -> None:
        """Layer an image onto the canvas using specified alignment and offset.

        Args:
            image: Image to layer.
            alignment: Optional override for (horizontal, vertical) alignment.
            offset: Optional (x, y) offset to shift the image.
            text_color: Color to use when pasting an 'L' mode mask.
        """
        h_align = alignment[0] if alignment else self.config.wimage_horizontal_align
        v_align = alignment[1] if alignment else self.config.wimage_vertical_align

        if h_align == HorizontalAlignment.LEFT:
            x = self.config.padding.left
        elif h_align == HorizontalAlignment.RIGHT:
            x = self.config.max_width - image.width - self.config.padding.right
        else:
            x = (self.config.max_width - image.width) // 2

        if v_align == VerticalAlignment.TOP:
            y = self.config.padding.top
        elif v_align == VerticalAlignment.BOTTOM:
            y = self.config.image_height - image.height - self.config.padding.bottom
        else:
            y = (self.config.image_height - image.height) // 2

        dx, dy = offset or (self.config.wimage_x_offset, self.config.wimage_y_offset)
        x += dx
        y += dy

        if image.mode == "L":
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
