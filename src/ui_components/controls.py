"""Race controls component for playback control."""

import os

import arcade
from src.config import get_config
from src.ui_components.base import BaseComponent


class RaceControlsComponent(BaseComponent):
    """Component that provides interactive buttons for playback control."""

    def __init__(
        self, x: int = 20, y: int = 20, button_size: int = 40, gap: int = 10, visible: bool = True
    ) -> None:
        """
        Initialize race controls component.

        Args:
            x: X position of controls
            y: Y position of controls
            button_size: Size of control buttons
            gap: Gap between buttons
            visible: Initial visibility state
        """
        self.x = x
        self.y = y
        self.button_size = button_size
        self.gap = gap
        self._visible = visible
        self._button_textures: dict[str, arcade.Texture] = {}
        self._load_button_textures()
        self._flashing_button: str | None = None
        self._flash_timer: float = 0.0
        self._flash_duration: float = 0.15  # seconds

    def _load_button_textures(self) -> None:
        """Load button icon textures from images/controls folder."""
        icons_folder = os.path.join("images", "controls")
        if not os.path.exists(icons_folder):
            return

        icon_files = {
            "rewind": "rewind.png",
            "play": "play.png",
            "pause": "pause.png",
            "speed-": "speed-.png",
            "speed+": "speed+.png",
        }

        for key, filename in icon_files.items():
            path = os.path.join(icons_folder, filename)
            if os.path.exists(path):
                try:
                    self._button_textures[key] = arcade.load_texture(path)
                except Exception:
                    pass  # Texture loading failed, will use text fallback

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

    def on_update(self, delta_time: float) -> None:
        """
        Update component state (called each frame).

        Args:
            delta_time: Time elapsed since last frame
        """
        if self._flashing_button:
            self._flash_timer -= delta_time
            if self._flash_timer <= 0:
                self._flashing_button = None

    def draw(self, window) -> None:
        """Draw the race controls component."""
        if not self._visible:
            return

        config = get_config()
        playback_speed = getattr(window, "playback_speed", config.default_playback_speed)
        is_playing = getattr(window, "is_playing", True)

        # Button positions
        buttons: list[tuple[str, float, float, str]] = []
        current_x = self.x

        # Rewind button
        buttons.append(("rewind", current_x, self.y, "⏪"))
        current_x += self.button_size + self.gap

        # Play/Pause button
        if is_playing:
            buttons.append(("pause", current_x, self.y, "⏸"))
        else:
            buttons.append(("play", current_x, self.y, "▶"))
        current_x += self.button_size + self.gap

        # Speed down button
        buttons.append(("speed-", current_x, self.y, "−"))
        current_x += self.button_size + self.gap

        # Speed display
        speed_text = f"{playback_speed:.1f}x"
        speed_text_x = current_x
        speed_text_y = self.y
        arcade.Text(
            speed_text,
            speed_text_x,
            speed_text_y,
            arcade.color.WHITE,
            14,
            anchor_x="center",
            anchor_y="center",
        ).draw()
        current_x += 50

        # Speed up button
        buttons.append(("speed+", current_x, self.y, "+"))

        # Draw buttons
        for btn_key, btn_x, btn_y, fallback_text in buttons:
            btn_rect = arcade.XYWH(btn_x, btn_y, self.button_size, self.button_size)

            # Button background
            bg_color = (60, 60, 60, 200)
            if self._flashing_button == btn_key:
                # Flash effect: brighter color
                flash_alpha = int(200 + 55 * (self._flash_timer / self._flash_duration))
                bg_color = (100, 100, 100, flash_alpha)

            arcade.draw_rect_filled(btn_rect, bg_color)
            arcade.draw_rect_outline(btn_rect, arcade.color.WHITE, 2)

            # Button icon
            if btn_key in self._button_textures:
                texture = self._button_textures[btn_key]
                icon_size = self.button_size * 0.7
                icon_rect = arcade.XYWH(btn_x, btn_y, icon_size, icon_size)
                arcade.draw_texture_rect(rect=icon_rect, texture=texture, angle=0, alpha=255)
            else:
                # Fallback to text
                arcade.Text(
                    fallback_text,
                    btn_x,
                    btn_y,
                    arcade.color.WHITE,
                    20,
                    anchor_x="center",
                    anchor_y="center",
                ).draw()

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int) -> bool:
        """Handle mouse press events for control buttons."""
        if not self._visible:
            return False

        config = get_config()
        playback_speed = getattr(window, "playback_speed", config.default_playback_speed)
        is_playing = getattr(window, "is_playing", True)

        # Calculate button positions (same as in draw)
        buttons: list[tuple[str, float, float]] = []
        current_x = self.x

        buttons.append(("rewind", current_x, self.y))
        current_x += self.button_size + self.gap

        buttons.append(("play_pause", current_x, self.y))
        current_x += self.button_size + self.gap

        buttons.append(("speed-", current_x, self.y))
        current_x += self.button_size + self.gap + 50  # Skip speed display

        buttons.append(("speed+", current_x, self.y))

        # Check which button was clicked
        for btn_key, btn_x, btn_y in buttons:
            btn_left = btn_x - self.button_size / 2
            btn_right = btn_x + self.button_size / 2
            btn_bottom = btn_y - self.button_size / 2
            btn_top = btn_y + self.button_size / 2

            if btn_left <= x <= btn_right and btn_bottom <= y <= btn_top:
                if btn_key == "rewind":
                    window.frame_index = max(0, window.frame_index - int(300 * playback_speed))
                    self.flash_button("rewind")
                elif btn_key == "play_pause":
                    window.is_playing = not is_playing
                    self.flash_button("play_pause")
                elif btn_key == "speed-":
                    speeds = config.playback_speeds
                    current_idx = next(
                        (i for i, s in enumerate(speeds) if s >= playback_speed), len(speeds) - 1
                    )
                    new_idx = max(0, current_idx - 1)
                    window.playback_speed = speeds[new_idx]
                    self.flash_button("speed-")
                elif btn_key == "speed+":
                    speeds = config.playback_speeds
                    current_idx = next(
                        (i for i, s in enumerate(speeds) if s >= playback_speed), len(speeds) - 1
                    )
                    new_idx = min(len(speeds) - 1, current_idx + 1)
                    window.playback_speed = speeds[new_idx]
                    self.flash_button("speed+")
                return True

        return False

    def on_mouse_motion(self, window, x: float, y: float, dx: float, dy: float) -> None:
        """
        Handle mouse motion for hover effects.

        Args:
            window: The arcade window instance
            x: Mouse X position
            y: Mouse Y position
            dx: Mouse X delta
            dy: Mouse Y delta
        """
        # Currently no hover effects implemented
        # Can be used for button highlighting in the future
        pass

    def flash_button(self, button_key: str) -> None:
        """
        Make a button flash briefly.

        Args:
            button_key: The key of the button to flash (e.g., 'play_pause', 'forward', 'rewind',
                       'speed_increase', 'speed_decrease', 'speed+', 'speed-')
        """
        # Map keyboard button names to visual button keys
        button_map = {
            "play_pause": "play_pause",
            "forward": "play_pause",  # Map forward to play_pause visually
            "rewind": "rewind",
            "speed_increase": "speed+",
            "speed_decrease": "speed-",
            "speed+": "speed+",
            "speed-": "speed-",
        }

        # Get the actual button key to flash
        actual_key = button_map.get(button_key, button_key)
        self._flashing_button = actual_key
        self._flash_timer = self._flash_duration
