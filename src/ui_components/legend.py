"""Legend component for displaying keyboard controls."""

import os

import arcade
from src.ui_components.base import BaseComponent


class LegendComponent(BaseComponent):
    """Component that displays keyboard and button controls legend."""

    def __init__(self, x: int = 20, y: int = 220, visible: bool = True) -> None:
        """
        Initialize legend component.

        Args:
            x: X position of legend
            y: Y position of legend
            visible: Initial visibility state
        """
        self.x = x
        self.y = y
        self._control_icons_textures: dict[str, arcade.Texture] = {}
        self._visible = visible
        self._text = arcade.Text("", 0, 0, arcade.color.WHITE, 14)

        # Load control icons
        icons_folder = os.path.join("images", "controls")
        if os.path.exists(icons_folder):
            for filename in os.listdir(icons_folder):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    texture_name = os.path.splitext(filename)[0]
                    texture_path = os.path.join(icons_folder, filename)
                    self._control_icons_textures[texture_name] = arcade.load_texture(texture_path)

        self.lines = [
            ("Controls:"),
            ("[SPACE]  Pause/Resume"),
            ("Rewind / FastForward", ("[", "/", "]"), ("arrow-left", "arrow-right")),
            ("Speed +/- (0.5x, 1x, 2x, 4x)", ("[", "/", "]"), ("arrow-up", "arrow-down")),
            ("[R]       Restart"),
            ("[D]       Toggle DRS Zones"),
            ("[B]       Toggle Progress Bar"),
        ]

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
        """Draw the legend component."""
        if not self._visible:
            return

        for i, lines in enumerate(self.lines):
            line = lines[0] if isinstance(lines, tuple) else lines
            brackets = lines[1] if isinstance(lines, tuple) and len(lines) > 2 else None
            icon_keys = lines[2] if isinstance(lines, tuple) and len(lines) > 2 else None

            icon_size = 14

            # Draw icons if any
            if icon_keys:
                control_icon_x = self.x + 12
                for key in icon_keys:
                    icon_texture = self._control_icons_textures.get(key)
                    if icon_texture:
                        control_icon_y = self.y - (i * 25) + 5
                        rect = arcade.XYWH(control_icon_x, control_icon_y, icon_size, icon_size)
                        arcade.draw_texture_rect(
                            rect=rect, texture=icon_texture, angle=0, alpha=255
                        )
                        control_icon_x += icon_size + 6

            # Draw brackets if any
            if brackets:
                for j in range(len(brackets)):
                    self._text.font_size = 14
                    self._text.bold = i == 0
                    self._text.color = arcade.color.LIGHT_GRAY if i > 0 else arcade.color.WHITE
                    self._text.text = brackets[j]
                    self._text.x = self.x + (j * (icon_size + 5))
                    self._text.y = self.y - (i * 25)
                    self._text.draw()

            # Draw the text line
            self._text.text = line
            self._text.x = self.x + (60 if icon_keys else 0)
            self._text.y = self.y - (i * 25)
            self._text.draw()
