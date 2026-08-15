from __future__ import annotations

from typing import Any

from PIL import Image

from quranmedialib.types import Color, Layerable, ResolvedRect, SidecarSink, VerticalAlignment


class Frame:
    """Composition class for layering images onto a fixed-size canvas."""

    def __init__(
        self,
        width: int,
        height: int,
        background_color: Color = (0, 0, 0, 0),
        collect_sidecar: bool = False,
    ):
        self.width = width
        self.height = height
        self.image = Image.new("RGBA", (width, height), self._as_rgba(background_color))
        # Layer nodes collected during placement, in placement order. Only
        # populated when ``collect_sidecar`` is True (zero-cost otherwise).
        self.sidecar_layers: list[dict[str, Any]] = [] if collect_sidecar else None

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
        sidecar_record: dict[str, Any] | None = None,
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
            sidecar_record: Optional layer node recorded for this placement when
                ``collect_sidecar`` is enabled. For plain Images, defaults to an
                ``image`` node with the paste box; supply a custom node to give a
                plain image a domain-specific ``class_type`` (e.g. translation).
            **kwargs: Additional args passed to Layerable.layer().
        """
        if isinstance(image, Layerable):
            image.layer(
                self.image,
                rect.left,
                rect.top,
                vertical_alignment=vertical_alignment,
                sidecar_sink=self._collect_sink(),
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
        if self.sidecar_layers is not None:
            if sidecar_record is not None:
                self.sidecar_layers.append(sidecar_record)
            else:
                self.sidecar_layers.append(
                    {
                        "class_type": "image",
                        "x": x,
                        "y": y,
                        "w": image.width,
                        "h": image.height,
                    }
                )

    def _collect_sink(self) -> SidecarSink | None:
        """Return the sidecar sink for Layerable placement, if collecting.

        Returns:
            SidecarSink | None: Appends Layerable nodes to ``sidecar_layers``,
                or None when sidecar collection is disabled.
        """
        if self.sidecar_layers is None:
            return None
        return self.sidecar_layers.append

    def render(self) -> Image.Image:
        """Return the final composed image."""
        return self.image
