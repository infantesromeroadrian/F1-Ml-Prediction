"""Qualifying segment selector component."""

from typing import Any

import arcade
from src.lib.time import format_time
from src.ui_components.base import BaseComponent


class QualifyingSegmentSelectorComponent(BaseComponent):
    """Modal component for selecting a driver's qualifying segment to view telemetry."""

    def __init__(self, width: int = 400, height: int = 300) -> None:
        """
        Initialize qualifying segment selector component.

        Args:
            width: Modal width
            height: Modal height
        """
        self.width = width
        self.height = height
        self.driver_result: dict[str, Any] | None = None
        self.selected_segment: str | None = None

    def draw(self, window) -> None:
        """Draw the qualifying segment selector modal."""
        if not getattr(window, "selected_driver", None):
            return

        code = window.selected_driver
        results = window.data["results"]
        driver_result = next((res for res in results if res["code"] == code), None)

        if not driver_result:
            return

        # Calculate modal position (centered)
        center_x = window.width // 2
        center_y = window.height // 2
        left = center_x - self.width // 2
        right = center_x + self.width // 2
        top = center_y + self.height // 2
        bottom = center_y - self.height // 2

        # Draw modal background
        modal_rect = arcade.XYWH(center_x, center_y, self.width, self.height)
        arcade.draw_rect_filled(modal_rect, (40, 40, 40, 230))
        arcade.draw_rect_outline(modal_rect, arcade.color.WHITE, 2)

        # Draw title
        title = f"Qualifying Sessions - {driver_result.get('code', '')}"
        arcade.Text(
            title,
            left + 20,
            top - 30,
            arcade.color.WHITE,
            18,
            bold=True,
            anchor_x="left",
            anchor_y="center",
        ).draw()

        # Draw segments
        segment_height = 50
        start_y = top - 80
        segments: list[dict[str, Any]] = []

        if driver_result.get("Q1") is not None:
            segments.append({"time": driver_result["Q1"], "segment": 1})
        if driver_result.get("Q2") is not None:
            segments.append({"time": driver_result["Q2"], "segment": 2})
        if driver_result.get("Q3") is not None:
            segments.append({"time": driver_result["Q3"], "segment": 3})

        for i, data in enumerate(segments):
            segment = f"Q{data['segment']}"
            segment_top = start_y - (i * (segment_height + 10))
            segment_bottom = segment_top - segment_height

            # Highlight if selected
            segment_rect = arcade.XYWH(
                center_x, segment_top - segment_height // 2, self.width - 40, segment_height
            )

            if segment == self.selected_segment:
                arcade.draw_rect_filled(segment_rect, arcade.color.LIGHT_GRAY)
                text_color = arcade.color.BLACK
            else:
                arcade.draw_rect_filled(segment_rect, (60, 60, 60))
                text_color = arcade.color.WHITE

            arcade.draw_rect_outline(segment_rect, arcade.color.WHITE, 1)

            # Draw segment info
            segment_text = f"{segment.upper()}"
            time_text = format_time(float(data.get("time", 0)))

            arcade.Text(
                segment_text,
                left + 30,
                segment_top - 20,
                text_color,
                16,
                bold=True,
                anchor_x="left",
                anchor_y="center",
            ).draw()
            arcade.Text(
                time_text,
                right - 30,
                segment_top - 20,
                text_color,
                14,
                anchor_x="right",
                anchor_y="center",
            ).draw()

        # Draw close button
        close_btn_rect = arcade.XYWH(right - 30, top - 30, 20, 20)
        arcade.draw_rect_filled(close_btn_rect, arcade.color.RED)
        arcade.Text(
            "×",
            right - 30,
            top - 30,
            arcade.color.WHITE,
            16,
            bold=True,
            anchor_x="center",
            anchor_y="center",
        ).draw()

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int) -> bool:
        """Handle mouse press events for segment selection and close button."""
        if not getattr(window, "selected_driver", None):
            return False

        # Calculate modal position (same as in draw)
        center_x = window.width // 2
        center_y = window.height // 2
        left = center_x - self.width // 2
        right = center_x + self.width // 2
        top = center_y + self.height // 2

        # Check close button
        close_btn_left = right - 30 - 10
        close_btn_right = right - 30 + 10
        close_btn_bottom = top - 30 - 10
        close_btn_top = top - 30 + 10

        if close_btn_left <= x <= close_btn_right and close_btn_bottom <= y <= close_btn_top:
            window.selected_driver = None
            window.selected_drivers = []
            if hasattr(window, "leaderboard"):
                window.leaderboard.selected = []
            self.selected_segment = None
            return True

        # Check segment clicks
        code = window.selected_driver
        results = window.data["results"]
        driver_result = next((res for res in results if res["code"] == code), None)

        if driver_result:
            segments: list[dict[str, Any]] = []
            if driver_result.get("Q1") is not None:
                segments.append({"time": driver_result["Q1"], "segment": 1})
            if driver_result.get("Q2") is not None:
                segments.append({"time": driver_result["Q2"], "segment": 2})
            if driver_result.get("Q3") is not None:
                segments.append({"time": driver_result["Q3"], "segment": 3})

            segment_height, start_y = 50, top - 80

            for i, data in enumerate(segments):
                s_top = start_y - (i * (segment_height + 10))
                s_bottom = s_top - segment_height
                if left + 20 <= x <= right - 20 and s_bottom <= y <= s_top:
                    try:
                        if hasattr(window, "load_driver_telemetry"):
                            window.load_driver_telemetry(code, f"Q{data['segment']}")
                        window.selected_driver = None
                        window.selected_drivers = []
                        if hasattr(window, "leaderboard"):
                            window.leaderboard.selected = []
                    except Exception as e:
                        # Error should be logged, not printed
                        if hasattr(window, "logger"):
                            window.logger.error(f"❌ Error starting telemetry load: {e}")
                    return True
        return True  # Consume all clicks when visible
