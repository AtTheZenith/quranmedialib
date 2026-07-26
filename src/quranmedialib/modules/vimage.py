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
        content_width: Available width for row wrapping in pixels.
        rows: The calculated 2D spatial arrangement (items, width, height).
    """

    def __init__(
        self,
        items: list[WordItem],
        verse_config: VerseConfig,
        content_width: int,
    ):
        self.items = items
        self.verse_config = verse_config
        self.content_width = content_width
        self.rows = []  # computed on-demand in get_page_chunk

    def _calculate_layout(self) -> list[tuple[list[WordItem], int, int]]:
        """Calculates the optimal row arrangement for the entire verse.

        Returns:
            A list of (row_items, row_width, max_row_height) tuples.
        """
        if not self.items:
            return []

        # Initial greedy packing
        rows = self._greedy_pack(self.items, self.content_width)

        # Optional balanced wrapping
        if self.verse_config.balanced_wrapping and len(rows) > 1:
            all_items = list(itertools.chain.from_iterable(r[0] for r in rows))
            rows = self._balance_rows(all_items, len(rows), self.content_width)

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
        remaining_items = self.items[start_index:]
        if not remaining_items:
            return [], 0

        # Step 1: Greedy pack into rows
        rows = self._greedy_pack(remaining_items, self.content_width)

        # Trim to max_rows
        if len(rows) > max_rows:
            rows = rows[:max_rows]

        # Step 2: Optional balanced wrapping (PER PAGE)
        if self.verse_config.balanced_wrapping and len(rows) > 1:
            all_items = list(itertools.chain.from_iterable(r[0] for r in rows))
            balanced = self._balance_rows(all_items, len(rows), self.content_width)
            if balanced is not None:
                rows = balanced

        items_consumed = sum(len(r[0]) for r in rows)

        # Step 3: Stop sign adjustment
        if items_consumed < len(remaining_items):
            rows, items_consumed = self._apply_stop_sign_adjustment(rows, items_consumed)

        return rows, items_consumed

    def _apply_stop_sign_adjustment(
        self,
        current_rows: list[tuple[list[WordItem], int, int]],
        items_consumed: int,
    ) -> tuple[list[tuple[list[WordItem], int, int]], int]:
        """Adjusts page breaks backwards to end on a Quranic stop sign."""
        if not current_rows:
            return current_rows, items_consumed

        # 1. Check if the current break is already on a stop sign
        last_row_items = current_rows[-1][0]
        if (
            last_row_items
            and last_row_items[-1].text
            and any(sign in last_row_items[-1].text for sign in QURANIC_STOP_SIGNS)
        ):
            return current_rows, items_consumed

        # 2. Search backwards for the nearest stop sign
        flat_items = []
        for r in current_rows:
            flat_items.extend(r[0])

        for i in range(items_consumed - 1, -1, -1):
            item = flat_items[i]
            if item.text and any(sign in item.text for sign in QURANIC_STOP_SIGNS):
                keep_count = i + 1
                if keep_count < items_consumed:
                    # Reconstruct the rows efficiently
                    adjusted_rows = []
                    count = 0
                    for row_items, width, height in current_rows:
                        if count >= keep_count:
                            break

                        take = min(len(row_items), keep_count - count)
                        if take < len(row_items):
                            # This is the truncated row; recalculate width
                            new_items = row_items[:take]
                            new_width = (
                                sum(it.width for it in new_items)
                                + (len(new_items) - 1) * self.verse_config.word_spacing
                                if new_items
                                else 0
                            )
                            adjusted_rows.append((new_items, new_width, height))
                        else:
                            # Keep the row as is
                            adjusted_rows.append((row_items, width, height))

                        count += take

                    return adjusted_rows, keep_count

        return current_rows, items_consumed

    def layer(
        self,
        canvas: Image.Image,
        x: int,
        y: int,
        word_config: WordConfig,
        rows_to_render: list[tuple[list[WordItem], int, int]] | None = None,
        center: bool = False,
        content_height: int = 0,
        **kwargs,
    ) -> None:
        """Renders the verse (or a subset of rows) directly onto the provided canvas.

        Args:
            canvas: The destination image to draw on.
            x: The anchor X coordinate (left edge of the bounding box).
            y: The anchor Y coordinate (top edge of the bounding box).
            word_config: Rendering rules for words.
            rows_to_render: Specific rows to render. If None, renders all self.rows.
        """
        rows = rows_to_render if rows_to_render is not None else self.rows
        if not rows:
            return

        total_width = max(row[1] for row in rows)
        if center and self.content_width > total_width:
            x += (self.content_width - total_width) // 2

        total_render_height = sum(r[2] for r in rows) + (len(rows) - 1) * self.verse_config.row_spacing
        if center and content_height > total_render_height:
            y += (content_height - total_render_height) // 2

        word_spacing = self.verse_config.word_spacing
        row_spacing = self.verse_config.row_spacing
        global_word_color = word_config.word_color
        draw_y = y

        for row, row_width, max_row_height in rows:
            # RTL anchor relative to bounding box
            # Alignment is already handled by 'x' anchor provided by Frame
            current_x = x + total_width

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
                if canvas.mode == "L":
                    color_to_use = 255
                canvas.paste(color_to_use, (current_x - row_width, draw_y), mask=row_mask)
            else:
                for item in row:
                    w_img = item.image
                    ry = draw_y + (max_row_height - w_img.height) // 2
                    color_to_use = item.color if item.color is not None else global_word_color

                    if w_img.mode == "L":
                        color_to_use = 255 if canvas.mode == "L" else color_to_use
                        canvas.paste(color_to_use, (current_x - w_img.width, ry), mask=w_img)
                    elif w_img.mode == "RGBA" and canvas.mode == "RGBA":
                        canvas.alpha_composite(w_img, dest=(current_x - w_img.width, ry))
                    else:
                        canvas.paste(w_img.convert(canvas.mode), (current_x - w_img.width, ry))

                    current_x -= w_img.width + word_spacing

            draw_y += max_row_height + row_spacing

    def render(
        self,
        word_config: WordConfig,
        rows_to_render: list[tuple[list[WordItem], int, int]] | None = None,
        mode: str = "RGBA",
    ) -> Image.Image:
        """Renders the verse (or a subset of rows) into an image.

        Now implemented as a wrapper around the .layer() method.
        """
        rows = rows_to_render if rows_to_render is not None else self.rows
        if not rows:
            return Image.new(mode, (0, 0), color=(0, 0, 0, 0) if mode == "RGBA" else 0)

        total_width = max(row[1] for row in rows)
        total_height = sum(row[2] for row in rows) + (len(rows) - 1) * self.verse_config.row_spacing

        canvas = Image.new(mode, (total_width, total_height), color=(0, 0, 0, 0) if mode == "RGBA" else 0)
        self.layer(canvas, 0, 0, word_config=word_config, rows_to_render=rows)
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
