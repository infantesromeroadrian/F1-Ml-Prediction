"""
ML Predictions Panel - F1 Broadcast Style.

Displays AI predictions for race outcome including:
- Win probability (bar chart)
- Expected finishing position
- Points forecast
"""

import arcade
from typing import Dict, Any, Optional


class MLPredictionsPanel:
    """Panel showing ML predictions for race outcome."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float = 350,
        height: float = 500,
        predictions: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize ML Predictions Panel.

        Args:
            x: X position (top-left corner)
            y: Y position (top-left corner)
            width: Panel width
            height: Panel height
            predictions: Dictionary with ML predictions {driver_code: {win_prob, expected_pos, expected_points}}
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.predictions = predictions or {}

        # Colors
        self.bg_color = (20, 20, 30, 230)  # Dark blue-gray, semi-transparent
        self.border_color = (100, 100, 120, 255)
        self.title_color = (255, 255, 255, 255)
        self.text_color = (220, 220, 220, 255)
        self.bar_color = (0, 180, 255, 200)  # Bright blue
        self.bar_bg_color = (40, 40, 50, 150)

        # Typography
        self.title_font_size = 16
        self.header_font_size = 13
        self.driver_font_size = 12

    def draw(self):
        """Draw the ML predictions panel."""
        if not self.predictions:
            return

        # Draw background
        arcade.draw_lrtb_rectangle_filled(
            self.x,
            self.x + self.width,
            self.y,
            self.y - self.height,
            self.bg_color,
        )

        # Draw border
        arcade.draw_lrtb_rectangle_outline(
            self.x,
            self.x + self.width,
            self.y,
            self.y - self.height,
            self.border_color,
            border_width=2,
        )

        # Draw title
        arcade.draw_text(
            "🤖 AI PREDICTIONS",
            self.x + self.width / 2,
            self.y - 25,
            self.title_color,
            font_size=self.title_font_size,
            bold=True,
            anchor_x="center",
        )

        # Section 1: Win Probability (top 5)
        self._draw_win_probability_section(self.y - 60)

        # Section 2: Expected Finish Position (top 10)
        self._draw_expected_position_section(self.y - 240)

        # Section 3: Points Forecast (top 10)
        self._draw_points_forecast_section(self.y - 380)

    def _draw_win_probability_section(self, start_y: float):
        """Draw win probability bars."""
        # Header
        arcade.draw_text(
            "🏆 WIN PROBABILITY",
            self.x + 15,
            start_y,
            self.text_color,
            font_size=self.header_font_size,
            bold=True,
        )

        # Sort by win probability
        sorted_predictions = sorted(
            self.predictions.items(),
            key=lambda item: item[1].get("win_prob", 0),
            reverse=True,
        )

        # Draw top 5
        for i, (driver, pred) in enumerate(sorted_predictions[:5]):
            if i >= 5:
                break

            win_prob = pred.get("win_prob", 0)
            if win_prob <= 0:
                continue

            y_pos = start_y - 30 - (i * 25)

            # Driver code
            arcade.draw_text(
                driver,
                self.x + 15,
                y_pos,
                self.text_color,
                font_size=self.driver_font_size,
                bold=True,
            )

            # Probability bar background
            bar_x = self.x + 55
            bar_width = self.width - 115
            bar_height = 16

            arcade.draw_lrtb_rectangle_filled(
                bar_x,
                bar_x + bar_width,
                y_pos + bar_height / 2,
                y_pos - bar_height / 2,
                self.bar_bg_color,
            )

            # Probability bar (filled)
            filled_width = bar_width * min(win_prob, 1.0)
            if filled_width > 0:
                # Gradient effect (lighter at the end)
                arcade.draw_lrtb_rectangle_filled(
                    bar_x,
                    bar_x + filled_width,
                    y_pos + bar_height / 2,
                    y_pos - bar_height / 2,
                    self.bar_color,
                )

            # Percentage text
            arcade.draw_text(
                f"{win_prob * 100:.0f}%",
                bar_x + bar_width + 10,
                y_pos,
                self.text_color,
                font_size=self.driver_font_size - 1,
                anchor_x="left",
            )

    def _draw_expected_position_section(self, start_y: float):
        """Draw expected finishing positions."""
        # Header
        arcade.draw_text(
            "📊 EXPECTED FINISH",
            self.x + 15,
            start_y,
            self.text_color,
            font_size=self.header_font_size,
            bold=True,
        )

        # Sort by expected position
        sorted_predictions = sorted(
            self.predictions.items(),
            key=lambda item: item[1].get("expected_position", 20),
        )

        # Draw top 10
        for i, (driver, pred) in enumerate(sorted_predictions[:10]):
            if i >= 10:
                break

            expected_pos = pred.get("expected_position", 0)
            confidence = pred.get("position_confidence", 0)  # Standard deviation

            y_pos = start_y - 25 - (i * 18)

            # Position
            pos_text = f"P{int(round(expected_pos))}"
            arcade.draw_text(
                pos_text,
                self.x + 20,
                y_pos,
                self.text_color,
                font_size=self.driver_font_size,
                bold=True,
            )

            # Driver code
            arcade.draw_text(
                driver,
                self.x + 60,
                y_pos,
                self.text_color,
                font_size=self.driver_font_size,
            )

            # Confidence (±)
            if confidence > 0:
                arcade.draw_text(
                    f"(±{confidence:.1f})",
                    self.x + self.width - 50,
                    y_pos,
                    (150, 150, 150, 255),
                    font_size=self.driver_font_size - 2,
                )

    def _draw_points_forecast_section(self, start_y: float):
        """Draw points forecast."""
        # Header
        arcade.draw_text(
            "💰 POINTS FORECAST",
            self.x + 15,
            start_y,
            self.text_color,
            font_size=self.header_font_size,
            bold=True,
        )

        # Sort by expected points
        sorted_predictions = sorted(
            self.predictions.items(),
            key=lambda item: item[1].get("expected_points", 0),
            reverse=True,
        )

        # Draw top 10
        for i, (driver, pred) in enumerate(sorted_predictions[:10]):
            if i >= 10:
                break

            expected_points = pred.get("expected_points", 0)
            if expected_points <= 0:
                continue

            y_pos = start_y - 25 - (i * 18)

            # Points
            arcade.draw_text(
                f"{int(round(expected_points))}",
                self.x + 25,
                y_pos,
                self.text_color,
                font_size=self.driver_font_size,
                bold=True,
                anchor_x="right",
            )

            # Driver code
            arcade.draw_text(
                driver,
                self.x + 40,
                y_pos,
                self.text_color,
                font_size=self.driver_font_size,
            )

            # Points bar (mini visualization)
            bar_x = self.x + 90
            bar_max_width = self.width - 110
            bar_height = 10
            normalized_points = min(expected_points / 25.0, 1.0)  # Max 25 points

            arcade.draw_lrtb_rectangle_filled(
                bar_x,
                bar_x + (bar_max_width * normalized_points),
                y_pos + bar_height / 2,
                y_pos - bar_height / 2,
                (255, 200, 0, 180),  # Gold color for points
            )

    def update_predictions(self, predictions: Dict[str, Any]):
        """
        Update predictions data.

        Args:
            predictions: New predictions dictionary
        """
        self.predictions = predictions
