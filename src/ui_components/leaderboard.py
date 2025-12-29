"""Leaderboard component for displaying driver positions."""

import os
from typing import Any

import arcade
from src.ui_components.base import BaseComponent

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore


class LeaderboardComponent(BaseComponent):
    """Component that displays live driver positions and tyre compounds."""

    def __init__(
        self, x: int, right_margin: int = 260, width: int = 240, visible: bool = True
    ) -> None:
        """
        Initialize leaderboard component.

        Args:
            x: X position of leaderboard
            right_margin: Right margin from window edge
            width: Component width
            visible: Initial visibility state
        """
        self.x = x
        self.width = width
        self.entries: list[tuple[str, tuple[int, int, int], dict[str, Any], float]] = []
        self.rects: list[tuple[str, float, float, float, float]] = []
        self.selected: list[str] = []
        self.row_height = 25
        self._tyre_textures: dict[str, arcade.Texture] = {}
        self._visible = visible
        self.ml_predictions = None  # DataFrame with ML predictions

        # Load tyre textures
        tyres_folder = os.path.join("images", "tyres")
        if os.path.exists(tyres_folder):
            for filename in os.listdir(tyres_folder):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    texture_name = os.path.splitext(filename)[0]
                    texture_path = os.path.join(tyres_folder, filename)
                    self._tyre_textures[texture_name] = arcade.load_texture(texture_path)

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

    def set_visible(self) -> None:
        """Set visibility to True."""
        self._visible = True

    def set_entries(
        self, entries: list[tuple[str, tuple[int, int, int], dict[str, Any], float]]
    ) -> None:
        """
        Set leaderboard entries.

        Args:
            entries: List of tuples (code, color, pos_dict, progress_m)
        """
        self.entries = entries

    def set_ml_predictions(self, ml_predictions: Any | None) -> None:
        """
        Set ML predictions data.

        Args:
            ml_predictions: DataFrame with ML predictions (driver_code, winner_probability, predicted_position, predicted_points)
        """
        self.ml_predictions = ml_predictions

    def draw(self, window) -> None:
        """Draw the leaderboard component."""
        if not self._visible:
            return

        self.selected = getattr(window, "selected_drivers", [])
        leaderboard_y = window.height - 40
        arcade.Text(
            "Leaderboard",
            self.x,
            leaderboard_y,
            arcade.color.WHITE,
            20,
            bold=True,
            anchor_x="left",
            anchor_y="top",
        ).draw()

        self.rects = []
        for i, (code, color, pos, progress_m) in enumerate(self.entries):
            current_pos = i + 1
            top_y = leaderboard_y - 30 - ((current_pos - 1) * self.row_height)
            bottom_y = top_y - self.row_height
            left_x = self.x
            right_x = self.x + self.width
            self.rects.append((code, left_x, bottom_y, right_x, top_y))

            # Highlight selected drivers
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
                text_color = color

            # Draw driver text
            text = (
                f"{current_pos}. {code}"
                if pos.get("rel_dist", 0) != 1
                else f"{current_pos}. {code}   OUT"
            )
            arcade.Text(text, left_x, top_y, text_color, 16, anchor_x="left", anchor_y="top").draw()

            # Draw tyre icon first (so ML predictions don't overlap)
            tyre_texture = self._tyre_textures.get(str(pos.get("tyre", "?")).upper())
            tyre_icon_x = None
            if tyre_texture:
                tyre_icon_x = left_x + self.width - 10
                tyre_icon_y = top_y - 12
                icon_size = 16
                rect = arcade.XYWH(tyre_icon_x, tyre_icon_y, icon_size, icon_size)
                arcade.draw_texture_rect(rect=rect, texture=tyre_texture, angle=0, alpha=255)

                # DRS indicator
                drs_val = pos.get("drs", 0)
                is_drs_on = drs_val and int(drs_val) >= 10
                drs_color = arcade.color.GREEN if is_drs_on else arcade.color.GRAY
                drs_dot_x = tyre_icon_x - icon_size - 4
                drs_dot_y = tyre_icon_y
                arcade.draw_circle_filled(drs_dot_x, drs_dot_y, 4, drs_color)

            # Draw ML predictions if available (after tyre icon to avoid overlap)
            if self.ml_predictions is not None and pd is not None:
                try:
                    driver_pred = self.ml_predictions[self.ml_predictions["driver_code"] == code]
                    if not driver_pred.empty:
                        pred_row = driver_pred.iloc[0]

                        # Show winner probability and predicted position/points
                        # Format: 🏆X% = Probabilidad de ganar | PX = Posición final predicha | Xpts = Puntos predichos
                        ml_text_parts = []

                        # Winner probability (Probabilidad de ganar la carrera)
                        # W84% = 84% de probabilidad de ganar (using 'W' instead of emoji for compatibility)
                        if "winner_probability" in pred_row and pd.notna(
                            pred_row["winner_probability"]
                        ):
                            win_prob = float(pred_row["winner_probability"])
                            if win_prob > 0.1:  # Only show if > 10%
                                ml_text_parts.append(f"W{win_prob * 100:.0f}%")

                        # Predicted position (Posición final predicha por el modelo)
                        # P4 = El modelo predice que terminará en posición 4
                        # Solo se muestra si difiere de la posición actual en el leaderboard
                        if "predicted_position" in pred_row and pd.notna(
                            pred_row["predicted_position"]
                        ):
                            pred_pos = int(pred_row["predicted_position"])
                            if pred_pos != current_pos:
                                ml_text_parts.append(f"P{pred_pos}")

                        # Predicted points (Puntos predichos según la posición final)
                        # 25pts = El modelo predice que obtendrá 25 puntos
                        if "predicted_points" in pred_row and pd.notna(
                            pred_row["predicted_points"]
                        ):
                            pred_pts = float(pred_row["predicted_points"])
                            if pred_pts > 0:
                                ml_text_parts.append(f"{pred_pts:.0f}pts")

                        # Draw ML predictions text (smaller, positioned to avoid overlap)
                        if ml_text_parts:
                            ml_text = " | ".join(ml_text_parts)
                            # Position to the left of tyre icon if it exists, otherwise right-aligned
                            # Leave space for DRS indicator (4px circle + 4px gap) and tyre icon (16px)
                            if tyre_icon_x is not None:
                                # Position before DRS indicator and tyre icon
                                ml_text_x = tyre_icon_x - icon_size - 8 - 8  # Left of DRS + tyre
                                anchor = "right"
                            else:
                                ml_text_x = right_x - 10
                                anchor = "right"

                            # Calculate text width to ensure it doesn't overlap with driver name
                            text_width_estimate = (
                                len(ml_text) * 6
                            )  # Approximate width per character
                            min_x = left_x + 80  # Leave space for "1. VER" format
                            if ml_text_x < min_x:
                                ml_text_x = min_x
                                anchor = "left"

                            arcade.Text(
                                ml_text,
                                ml_text_x,
                                top_y - 2,
                                arcade.color.YELLOW,
                                10,
                                anchor_x=anchor,
                                anchor_y="top",
                            ).draw()
                except Exception:
                    # Silently fail if there's an error accessing predictions
                    pass

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
                # Single click: clear others and toggle selection
                elif len(self.selected) == 1 and self.selected[0] == code:
                    self.selected = []
                else:
                    self.selected = [code]

                # Propagate selection to window
                window.selected_drivers = self.selected
                window.selected_driver = self.selected[-1] if self.selected else None
                return True
        return False
