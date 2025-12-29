"""Weather component for displaying race weather information."""

import os
from typing import Any

import arcade
from src.ui_components.base import BaseComponent
from src.ui_components.utils import format_wind_direction


class WeatherComponent(BaseComponent):
    """Component that displays current weather information."""

    def __init__(
        self,
        left: int = 20,
        width: int = 280,
        height: int = 130,
        top_offset: int = 170,
        visible: bool = True,
    ) -> None:
        """
        Initialize weather component.

        Args:
            left: Left position
            width: Component width
            height: Component height
            top_offset: Offset from top of window
            visible: Initial visibility state
        """
        self.left = left
        self.width = width
        self.height = height
        self.top_offset = top_offset
        self.info: dict[str, Any] | None = None
        self._weather_icon_textures: dict[str, arcade.Texture] = {}
        self._visible = visible
        self._text = arcade.Text("", self.left + 12, 0, arcade.color.LIGHT_GRAY, 14, anchor_y="top")

        # Load weather icons
        weather_folder = os.path.join("images", "weather")
        if os.path.exists(weather_folder):
            for filename in os.listdir(weather_folder):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    texture_name = os.path.splitext(filename)[0]
                    texture_path = os.path.join(weather_folder, filename)
                    self._weather_icon_textures[texture_name] = arcade.load_texture(texture_path)

    def set_info(self, info: dict[str, Any] | None) -> None:
        """Set weather information to display."""
        self.info = info

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

    def draw(self, window) -> None:
        """Draw the weather component."""
        if not self._visible:
            return

        panel_top = window.height - self.top_offset
        if not self.info and not getattr(window, "has_weather", False):
            return

        def _fmt(val: float | None, suffix: str = "", precision: int = 1) -> str:
            """Format value with suffix and precision."""
            return f"{val:.{precision}f}{suffix}" if val is not None else "N/A"

        info = self.info or {}

        # Map each weather line to its corresponding icon
        weather_lines = [
            ("Track", f"{_fmt(info.get('track_temp'), '°C')}", "thermometer"),
            ("Air", f"{_fmt(info.get('air_temp'), '°C')}", "thermometer"),
            ("Humidity", f"{_fmt(info.get('humidity'), '%', precision=0)}", "drop"),
            (
                "Wind",
                f"{_fmt(info.get('wind_speed'), ' km/h')} {format_wind_direction(info.get('wind_direction'))}",
                "wind",
            ),
            ("Rain", f"{info.get('rain_state', 'N/A')}", "rain"),
        ]

        start_y = panel_top - 36
        last_y = start_y

        # Draw title
        self._text.font_size = 18
        self._text.bold = True
        self._text.color = arcade.color.WHITE
        self._text.text = "Weather"
        self._text.x = self.left + 12
        self._text.y = panel_top - 10
        self._text.draw()

        # Draw weather lines
        for idx, (label, value, icon_key) in enumerate(weather_lines):
            line_y = start_y - idx * 22
            last_y = line_y

            # Draw weather icon
            weather_texture = self._weather_icon_textures.get(icon_key)
            if weather_texture:
                weather_icon_x = self.left + 24
                weather_icon_y = line_y - 15
                icon_size = 16
                rect = arcade.XYWH(weather_icon_x, weather_icon_y, icon_size, icon_size)
                arcade.draw_texture_rect(rect=rect, texture=weather_texture, angle=0, alpha=255)

            # Draw text
            line_text = f"{label}: {value}"
            self._text.font_size = 14
            self._text.bold = False
            self._text.color = arcade.color.LIGHT_GRAY
            self._text.text = line_text
            self._text.x = self.left + 38
            self._text.y = line_y
            self._text.draw()

        # Track the bottom of the weather panel
        window.weather_bottom = last_y - 20
