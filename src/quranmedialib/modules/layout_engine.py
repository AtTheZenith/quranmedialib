"""Resolution-independent layout engine using UDim2 and AnchorPoint.

Resolves UDim2-based layout definitions to absolute pixel positions
for a given canvas size. All dimensions are computed at render time.
"""

from __future__ import annotations

from dataclasses import dataclass

from quranmedialib.types import PresetLayout, ResolvedRect


@dataclass(frozen=True, slots=True)
class LayoutGuide:
    """Resolved pixel layout for all content areas."""
    arabic: ResolvedRect
    translation: ResolvedRect


class LayoutEngine:
    """Resolves PresetLayout elements to absolute pixel positions.

    Usage:
        engine = LayoutEngine(canvas_width, canvas_height)
        guide = LayoutGuide(
            arabic=engine.resolve_rect(arabic_layout),
            translation=engine.resolve_rect(translation_layout),
        )
    """

    def __init__(self, canvas_width: int, canvas_height: int):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

    def resolve_rect(self, elem: PresetLayout) -> ResolvedRect:
        """Resolve a PresetLayout element to pixel coordinates.

        Args:
            elem: The UDim2-based layout element definition.

        Returns:
            ResolvedRect with absolute pixel positions.
        """
        return elem.resolve(self.canvas_width, self.canvas_height)


__all__ = ["LayoutEngine", "LayoutGuide"]
