"""Resolution-independent layout engine using UDim2 and AnchorPoint.

Resolves UDim2-based layout definitions to absolute pixel positions
for a given frame size. All dimensions are computed at render time
(the term "frame" here means canvas — this is multimedia-oriented).
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
        engine = LayoutEngine(frame_width, frame_height)
        guide = LayoutGuide(
            arabic=engine.resolve_rect(arabic_layout),
            translation=engine.resolve_rect(translation_layout),
        )
    """

    def __init__(self, frame_width: int, frame_height: int):
        self.frame_width = frame_width
        self.frame_height = frame_height

    def resolve_rect(self, elem: PresetLayout) -> ResolvedRect:
        """Resolve a PresetLayout element to pixel coordinates.

        Args:
            elem: The UDim2-based layout element definition.

        Returns:
            ResolvedRect with absolute pixel positions.
        """
        return elem.resolve(self.frame_width, self.frame_height)


__all__ = ["LayoutEngine", "LayoutGuide"]
