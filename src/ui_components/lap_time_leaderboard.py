"""Lap time leaderboard component for qualifying sessions."""

from typing import Any

import arcade
from src.ui_components.base import BaseComponent


class LapTimeLeaderboardComponent(BaseComponent):
    """Component that displays qualifying lap times and driver positions."""

    def __init__(self, x: int, right_margin: int = 260, width: int = 240) -> None:
        """
        Initialize lap time leaderboard component.

        Args:
            x: X position of leaderboard
            right_margin: Right margin from window edge (unused, kept for compatibility)
            width: Component width
        """
        self.x = x
        self.width = width
        self.entries: list[dict[str, Any]] = []
        self.rects: list[tuple[str, float, float, float, float]] = []
        self.selected: list[str] = []
        self.row_height = 25
        self._visible = True

    def set_entries(self, entries: list[dict[str, Any]]) -> None:
        """
        Set leaderboard entries.

        Args:
            entries: List of dicts with keys: pos, code, color, time
        """
        self.entries = entries or []

    @property
    def visible(self) -> bool:
        """Get visibility state."""
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        """Set visibility state."""
        self._visible = value

    def toggle_visibility(self) -> bool:
        """Toggle visibility and return new state."""
        self._visible = not self._visible
        return self._visible

    def draw(self, window) -> None:
        """Draw the lap time leaderboard component."""
        if not self._visible:
            return

        self.selected = getattr(window, "selected_drivers", [])
        leaderboard_y = window.height - 40
        arcade.Text(
            "Lap Times",
            self.x,
            leaderboard_y,
            arcade.color.WHITE,
            20,
            bold=True,
            anchor_x="left",
            anchor_y="top",
        ).draw()

        self.rects = []
        for i, entry in enumerate(self.entries):
            pos = entry.get("pos", i + 1)
            code = entry.get("code", "")
            color = entry.get("color", arcade.color.WHITE)
            time_str = entry.get("time", "")
            current_pos = i + 1
            top_y = leaderboard_y - 30 - ((current_pos - 1) * self.row_height)
            bottom_y = top_y - self.row_height
            left_x = self.x
            right_x = self.x + self.width
            self.rects.append((code, left_x, bottom_y, right_x, top_y))

            # Selection highlight
            if code in self.selected:
                rect = arcade.XYWH(
                    (left_x + right_x) / 2,
                    (top_y + bottom_y) / 2,
                    right_x - left_x,
                    top_y - bottom_y,
                )
                arcade.draw_rect_filled(rect, arcade.color.LIGHT_GRAY)
                text_color = arcade.color.BLACK
            else:
                text_color = (
                    tuple(color) if isinstance(color, (list, tuple)) else arcade.color.WHITE
                )

            # Draw code on left, time right-aligned
            arcade.Text(
                f"{pos}. {code}", left_x + 8, top_y, text_color, 16, anchor_x="left", anchor_y="top"
            ).draw()
            arcade.Text(
                time_str, right_x - 8, top_y, text_color, 14, anchor_x="right", anchor_y="top"
            ).draw()

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int) -> bool:
        """Handle mouse press events for driver selection."""
        for code, left, bottom, right, top in self.rects:
            if left <= x <= right and bottom <= y <= top:
                is_multi = modifiers & arcade.key.MOD_SHIFT

                if is_multi:
                    if code in self.selected:
                        self.selected.remove(code)
                    else:
                        self.selected.append(code)
                elif len(self.selected) == 1 and self.selected[0] == code:
                    self.selected = []
                else:
                    self.selected = [code]

                window.selected_drivers = self.selected
                window.selected_driver = self.selected[-1] if self.selected else None
                return True
        return False
