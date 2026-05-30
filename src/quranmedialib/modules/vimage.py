"""VImage module for representing and rendering a single Quranic verse.

This module handles the internal spatial arrangement of word images for a verse,
including Right-to-Left (RTL) flow, balanced line distribution, and
Quranic stop-sign aware wrapping.
"""

from __future__ import annotations

import itertools
import logging

from PIL import Image

from quranmedialib.modules.text_layout import balance_lines_pyramid
from quranmedialib.types import (
    LayoutConfig,
    VerseConfig,
    WordConfig,
    WordItem,
)

logger = logging.getLogger(__name__)

__all__ = ["VImage", "QURANIC_STOP_SIGNS"]

QURANIC_STOP_SIGNS = ["ۖ", "ۗ", "ۚ", "ۛ", "ۜ", "ۙ", "ۘ"]


class VImage:
    """Represents the layout and rendering of a single Quranic verse.

    Attributes:
        items: The list of WordItems forming the verse.
        verse_config: Layout rules for the verse.
        layout_config: Geometry constraints (e.g., content width).
        rows: The calculated 2D spatial arrangement (items, width, height).
    """

    def __init__(
        self,
        items: list[WordItem],
        verse_config: VerseConfig,
        layout_config: LayoutConfig,
    ):
        self.items = items
        self.verse_config = verse_config
        self.layout_config = layout_config
        self.rows = self._calculate_layout()

    def _calculate_layout(self) -> list[tuple[list[WordItem], int, int]]:
        """Calculates the optimal row arrangement for the entire verse.

        Returns:
            A list of (row_items, row_width, max_row_height) tuples.
        """
        if not self.items:
            return []

        # Initial greedy packing
        rows = self._greedy_pack(self.items, self.layout_config.content_width)

        # Optional balanced wrapping
        if self.verse_config.balanced_wrapping and len(rows) > 1:
            all_items = list(itertools.chain.from_iterable(r[0] for r in rows))
            rows = self._balance_rows(all_items, len(rows), self.layout_config.content_width)

        return rows

    def _greedy_pack(self, items: list[WordItem], target_width: int) -> list[tuple[list[WordItem], int, int]]:
        """Internal greedy divider for a specific width constraint."""
        rows = []
        current_row = []
        current_width = 0
        max_row_height = 0

        for item in items:
            word_width = item.width
            spacing = self.verse_config.word_spacing if current_row else 0

            if current_width + word_width + spacing <= target_width:
                current_row.append(item)
                current_width += word_width + spacing
                max_row_height = max(max_row_height, item.height)
            elif current_row:
                rows.append((current_row, current_width, max_row_height))
                current_row = [item]
                current_width = word_width
                max_row_height = item.height
            else:
                rows.append(([item], item.width, item.height))
                current_row = []
                current_width = 0
                max_row_height = 0

        if current_row:
            rows.append((current_row, current_width, max_row_height))
        return rows

    def _balance_rows(
        self,
        items: list[WordItem],
        target_num_rows: int,
        max_width: int,
    ) -> list[tuple[list[WordItem], int, int]]:
        """Binary searches for the minimum first-line width for balanced layout."""
        widths = [it.width for it in items]
        best_breaks = balance_lines_pyramid(
            widths=widths,
            spacing=self.verse_config.word_spacing,
            target_k=target_num_rows,
            max_width=max_width,
        )

        if best_breaks is None:
            return self._greedy_pack(items, max_width)

        final_rows = []
        current_row = []
        max_row_height = 0
        current_width = 0
        break_set = set(best_breaks)
        for i, item in enumerate(items):
            spacing = self.verse_config.word_spacing if current_row else 0
            if i in break_set:
                final_rows.append((current_row, current_width, max_row_height))
                current_row = []
                current_width = 0
                max_row_height = 0
            current_row.append(item)
            current_width += item.width + spacing
            max_row_height = max(max_row_height, item.height)
        if current_row:
            final_rows.append((current_row, current_width, max_row_height))

        return final_rows

    def get_page_chunk(
        self,
        start_index: int,
        max_rows: int,
    ) -> tuple[list[tuple[list[WordItem], int, int]], int]:
        """Extracts a chunk of rows for a page and adjusts the break for stop signs.

        Args:
            start_index: Index of the first word to process.
            max_rows: Maximum rows allowed on the page.

        Returns:
            A tuple of (rows_for_page, total_items_consumed).
        """
        # Find which rows contain the items starting from start_index
        current_pos = 0
        row_start_idx = -1
        for i, (row, _, _) in enumerate(self.rows):
            if current_pos <= start_index < current_pos + len(row):
                row_start_idx = i
                break
            current_pos += len(row)

        if row_start_idx == -1:
            return [], 0

        # The first row of the chunk might be partially consumed
        offset_in_row = start_index - current_pos
        chunk_rows = []

        # Extract up to max_rows
        for i in range(row_start_idx, min(row_start_idx + max_rows, len(self.rows))):
            row, width, height = self.rows[i]
            items = row[offset_in_row:] if i == row_start_idx else row

            # Recalculate width for sliced first row
            if i == row_start_idx and offset_in_row > 0:
                width = (
                    sum(it.width for it in items) + (len(items) - 1) * self.verse_config.word_spacing if items else 0
                )

            chunk_rows.append((items, width, height))
            offset_in_row = 0  # Reset for subsequent rows

        items_consumed = sum(len(r[0]) for r in chunk_rows)

        # Adjust break backwards to end on a stop sign
        if items_consumed < (len(self.items) - start_index):
            chunk_rows, items_consumed = self._apply_stop_sign_adjustment(chunk_rows, items_consumed)

        return chunk_rows, items_consumed

    def _apply_stop_sign_adjustment(
        self,
        current_rows: list[tuple[list[WordItem], int, int]],
        items_consumed: int,
    ) -> tuple[list[tuple[list[WordItem], int, int]], int]:
        """Adjusts page breaks backwards to end on a Quranic stop sign."""
        if not current_rows:
            return current_rows, items_consumed

        # 1. Check if the current break is already on a stop sign
        last_row = current_rows[-1][0]
        if last_row and last_row[-1].text and any(sign in last_row[-1].text for sign in QURANIC_STOP_SIGNS):
            return current_rows, items_consumed

        # 2. Search backwards for the nearest stop sign
        row_lengths = [len(row) for row in current_rows]
        prefix_sums = [0] + list(itertools.accumulate(row_lengths))

        for row_index in range(len(current_rows) - 1, -1, -1):
            row = current_rows[row_index][0]
            for word_index in range(len(row) - 1, -1, -1):
                item = row[word_index]
                if item.text and any(sign in item.text for sign in QURANIC_STOP_SIGNS):
                    keep_count = prefix_sums[row_index] + word_index + 1
                    if keep_count < items_consumed:
                        adjusted_rows = current_rows[: row_index + 1]
                        items, _, height = adjusted_rows[-1]
                        new_items = items[: word_index + 1]
                        new_width = (
                            sum(it.width for it in new_items) + (len(new_items) - 1) * self.verse_config.word_spacing
                            if new_items
                            else 0
                        )
                        adjusted_rows[-1] = (new_items, new_width, height)
                        return adjusted_rows, keep_count

        return current_rows, items_consumed

    def render(
        self,
        word_config: WordConfig,
        rows_to_render: list[tuple[list[WordItem], int, int]] | None = None,
        mode: str = "RGBA",
    ) -> Image.Image:
        """Renders the verse (or a subset of rows) into an image.

        Args:
            word_config: Rendering rules for words.
            rows_to_render: Specific rows to render. If None, renders all self.rows.
            mode: PIL image mode ('RGBA' or 'L' for mask).

        Returns:
            A rendered PIL Image.
        """
        rows = rows_to_render if rows_to_render is not None else self.rows
        if not rows:
            return Image.new(mode, (0, 0), color=(0, 0, 0, 0))

        total_width = max(row[1] for row in rows)
        total_height = sum(row[2] for row in rows) + (len(rows) - 1) * self.verse_config.row_spacing

        if mode == "L":
            canvas = Image.new(mode, (total_width, total_height), color=0)
        else:
            canvas = Image.new(mode, (total_width, total_height), color=(0, 0, 0, 0))
        draw_y = 0

        word_spacing = self.verse_config.word_spacing
        row_spacing = self.verse_config.row_spacing
        global_word_color = word_config.word_color

        for row, row_width, max_row_height in rows:
            current_x = total_width  # RTL anchor relative to bounding box

            # Align row within the verse bounding box (centering relative to max row width)
            current_x -= (total_width - row_width) // 2 if total_width > row_width else 0
            # Wait, if it's RTL, it's usually right-aligned.
            # But for a standalone VImage, we center it if we want it to be the bounding box.
            # Actually, let's just use right-alignment for now and let the framer handle it.
            # But the VImage itself should be tight.
            current_x = total_width

            first_color = row[0].color if row else None
            can_merge = len(row) > 1 and all(item.image.mode == "L" and item.color == first_color for item in row)

            if can_merge:
                row_mask = Image.new("L", (row_width, max_row_height), 0)
                rx = row_width
                for item in row:
                    w_img = item.image
                    ry = (max_row_height - w_img.height) // 2
                    rx -= w_img.width
                    row_mask.paste(w_img, (rx, ry))
                    rx -= word_spacing

                color_to_use = first_color if first_color is not None else global_word_color
                # Note: canvas is RGBA, mask is L.
                # If mode is "L", we just paste the mask.
                if mode == "L":
                    canvas.paste(row_mask, (current_x - row_width, draw_y))
                else:
                    canvas.paste(color_to_use, (current_x - row_width, draw_y), mask=row_mask)
            else:
                for item in row:
                    w_img = item.image
                    ry = draw_y + (max_row_height - w_img.height) // 2
                    color_to_use = item.color if item.color is not None else global_word_color

                    if w_img.mode == "L":
                        if mode == "L":
                            canvas.paste(w_img, (current_x - w_img.width, ry))
                        else:
                            canvas.paste(color_to_use, (current_x - w_img.width, ry), mask=w_img)
                    else:
                        if mode == "RGBA":
                            canvas.alpha_composite(w_img, dest=(current_x - w_img.width, ry))
                        else:
                            # Fallback for L mode canvas with RGBA images: convert to L
                            canvas.paste(w_img.convert("L"), (current_x - w_img.width, ry))

                    current_x -= w_img.width + word_spacing

            draw_y += max_row_height + row_spacing

        return canvas

    @property
    def width(self) -> int:
        """The maximum width of any row in the verse."""
        return max((row[1] for row in self.rows), default=0)

    @property
    def height(self) -> int:
        """The total height of the verse including row spacings."""
        if not self.rows:
            return 0
        return sum(row[2] for row in self.rows) + (len(self.rows) - 1) * self.verse_config.row_spacing
