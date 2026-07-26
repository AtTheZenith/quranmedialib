from __future__ import annotations

import warnings

from PIL import Image

from quranmedialib.types import Color, Layerable, ResolvedRect


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
        **kwargs,
    ) -> None:
        """Place content at a resolved pixel rectangle.

        For plain Images, pastes at (rect.left, rect.top).
        For Layerable objects, delegates with the rect position.

        Args:
            image: The image or Layerable to place.
            rect: Resolved pixel position and size.
            text_color: Color for 'L' mode mask images.
            **kwargs: Additional args passed to Layerable.layer().
        """
        if isinstance(image, Layerable):
            image.layer(self.image, rect.left, rect.top, **kwargs)
        elif image.mode == "L":
            self.image.paste(text_color or (255, 255, 255, 255), (rect.left, rect.top), mask=image)
        elif image.mode == "RGBA":
            self.image.alpha_composite(image, dest=(rect.left, rect.top))
        else:
            self.image.paste(image, (rect.left, rect.top))

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
