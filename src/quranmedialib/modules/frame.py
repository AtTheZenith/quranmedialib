from __future__ import annotations

import warnings

from PIL import Image

from quranmedialib.types import Color, Layerable, ResolvedRect, VerticalAlignment


class Frame:
    """Composition class for layering images onto a fixed-size canvas."""

    def __init__(self, width: int, height: int, background_color: Color = (0, 0, 0, 0)):
        self.width = width
        self.height = height
        self.image = Image.new("RGBA", (width, height), self._as_rgba(background_color))

    @staticmethod
    def _as_rgba(color: Color) -> tuple[int, int, int, int]:
        if len(color) == 3:
            return (*color, 255)
        return color

    def layer_at(
        self,
        image: Image.Image | Layerable,
        rect: ResolvedRect,
        text_color: Color | None = None,
        keep_bottom: bool = False,
        vertical_alignment: VerticalAlignment = VerticalAlignment.CENTER,
        **kwargs,
    ) -> None:
        """Place content at a resolved pixel rectangle.

        For plain Images, pastes at (rect.left, rect.top).
        For Layerable objects, delegates with the rect position.

        Args:
            image: The image or Layerable to place.
            rect: Resolved pixel position and size.
            text_color: Color for 'L' mode mask images.
            keep_bottom: If True, aligns image bottom with rect bottom.
            vertical_alignment: Vertical anchoring for Layerable content. Ignored for
                plain Images.
            **kwargs: Additional args passed to Layerable.layer().
        """
        if isinstance(image, Layerable):
            image.layer(
                self.image,
                rect.left,
                rect.top,
                vertical_alignment=vertical_alignment,
                **kwargs,
            )
            return
        x, y = rect.left, rect.top
        if keep_bottom:
            y = rect.top + rect.height - image.height
        if rect.width > image.width:
            x = rect.left + (rect.width - image.width) // 2
        if image.mode == "L":
            self.image.paste(text_color or (255, 255, 255, 255), (x, y), mask=image)
        elif image.mode == "RGBA":
            self.image.alpha_composite(image, dest=(x, y))
        else:
            self.image.paste(image, (x, y))

    def layer(
        self,
        image: Image.Image | Layerable,
        alignment: tuple | None = None,
        offset: tuple[int, int] | None = None,
        text_color: Color | None = None,
        **kwargs,
    ) -> None:
        """DEPRECATED: Use layer_at() with a resolved rect instead.

        Legacy compat shim. Places content at offset (0,0) with no scaling.
        """
        warnings.warn(
            "Frame.layer() is deprecated. Use Frame.layer_at() with a ResolvedRect instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        dx, dy = offset or (0, 0)
        rect = ResolvedRect(left=dx, top=dy, width=0, height=0)
        self.layer_at(image, rect, text_color, **kwargs)

    def render(self) -> Image.Image:
        """Return the final composed image."""
        return self.image
