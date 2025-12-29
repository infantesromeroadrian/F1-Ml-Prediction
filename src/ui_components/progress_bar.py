"""Race progress bar component with event markers."""

from typing import Any

import arcade
from src.ui_components.base import BaseComponent

# Event type constants
EVENT_DNF = "dnf"
EVENT_LAP = "lap"
EVENT_YELLOW_FLAG = "yellow_flag"
EVENT_RED_FLAG = "red_flag"
EVENT_SAFETY_CAR = "safety_car"
EVENT_VSC = "vsc"


def extract_race_events(
    frames: list[dict[str, Any]], track_statuses: list[dict[str, Any]], total_laps: int
) -> list[dict[str, Any]]:
    """
    Extract race events from frame data for the progress bar.

    Args:
        frames: List of frame dictionaries from telemetry
        track_statuses: List of track status events
        total_laps: Total number of laps in the race

    Returns:
        List of event dictionaries for the progress bar
    """
    events: list[dict[str, Any]] = []

    if not frames:
        return events

    n_frames = len(frames)

    # Track drivers present in each frame
    prev_drivers = set()
    sample_rate = 25  # Sample every 25 frames (1 second at 25 FPS)

    for i in range(0, n_frames, sample_rate):
        frame = frames[i]
        drivers_data = frame.get("drivers", {})
        current_drivers = set(drivers_data.keys())

        # Detect DNFs (drivers who disappeared)
        if prev_drivers:
            dnf_drivers = prev_drivers - current_drivers
            for driver_code in dnf_drivers:
                prev_frame = frames[max(0, i - sample_rate)]
                driver_info = prev_frame.get("drivers", {}).get(driver_code, {})
                lap = driver_info.get("lap", "?")

                events.append(
                    {
                        "type": EVENT_DNF,
                        "frame": i,
                        "label": driver_code,
                        "lap": lap,
                    }
                )

        prev_drivers = current_drivers

    # Add flag events from track_statuses
    fps = 25
    for status in track_statuses:
        status_code = str(status.get("status", ""))
        start_time = status.get("start_time", 0)
        end_time = status.get("end_time")

        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps) if end_time else start_frame + 250

        if end_frame <= 0:
            continue

        if n_frames > 0:
            end_frame = min(end_frame, n_frames)

        event_type: str | None = None
        if status_code == "2":
            event_type = EVENT_YELLOW_FLAG
        elif status_code == "4":
            event_type = EVENT_SAFETY_CAR
        elif status_code == "5":
            event_type = EVENT_RED_FLAG
        elif status_code in ("6", "7"):
            event_type = EVENT_VSC

        if event_type:
            events.append(
                {
                    "type": event_type,
                    "frame": start_frame,
                    "end_frame": end_frame,
                    "label": "",
                    "lap": None,
                }
            )

    return events


class RaceProgressBarComponent(BaseComponent):
    """Component that displays race progress with event markers."""

    # Event type constants
    EVENT_DNF = EVENT_DNF
    EVENT_LAP = EVENT_LAP
    EVENT_YELLOW_FLAG = EVENT_YELLOW_FLAG
    EVENT_RED_FLAG = EVENT_RED_FLAG
    EVENT_SAFETY_CAR = EVENT_SAFETY_CAR
    EVENT_VSC = EVENT_VSC

    # Color palette
    COLORS = {
        "background": (30, 30, 30, 200),
        "progress_fill": (0, 180, 0),
        "progress_border": (100, 100, 100),
        "dnf": (220, 50, 50),
        "lap_marker": (80, 80, 80),
        "yellow_flag": (255, 220, 0),
        "red_flag": (220, 30, 30),
        "safety_car": (255, 140, 0),
        "vsc": (255, 165, 0),
        "text": (220, 220, 220),
        "current_position": (255, 255, 255),
    }

    def __init__(
        self,
        left_margin: int = 340,
        right_margin: int = 260,
        bottom: int = 30,
        height: int = 24,
        marker_height: int = 16,
    ) -> None:
        """
        Initialize progress bar component.

        Args:
            left_margin: Left margin from window edge
            right_margin: Right margin from window edge
            bottom: Distance from bottom of window
            height: Height of the progress bar
            marker_height: Height of event markers
        """
        self.left_margin = left_margin
        self.right_margin = right_margin
        self.bottom = bottom
        self.height = height
        self.marker_height = marker_height
        self._visible = False

        # Cached data
        self._events: list[dict[str, Any]] = []
        self._total_frames = 0
        self._total_laps = 0
        self._bar_left = 0.0
        self._bar_width = 0.0

        # Hover state
        self._hover_event: dict[str, Any] | None = None
        self._mouse_x = 0.0
        self._mouse_y = 0.0

    def set_race_data(
        self, total_frames: int, total_laps: int, events: list[dict[str, Any]]
    ) -> None:
        """
        Set race data for the progress bar.

        Args:
            total_frames: Total number of frames in the race
            total_laps: Total number of laps in the race
            events: List of event dictionaries
        """
        self._total_frames = max(1, total_frames)
        self._total_laps = total_laps or 1
        self._events = sorted(events, key=lambda e: e.get("frame", 0))

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

    def _calculate_bar_dimensions(self, window) -> None:
        """Calculate bar dimensions based on window size."""
        self._bar_left = float(self.left_margin)
        self._bar_width = float(max(100, window.width - self.left_margin - self.right_margin))

    def _frame_to_x(self, frame: int, clamp: bool = True) -> float:
        """
        Convert frame number to X position on the bar.

        Args:
            frame: Frame number to convert
            clamp: Whether to clamp frame to valid range

        Returns:
            X position on the bar
        """
        if self._total_frames <= 0:
            return self._bar_left

        if clamp:
            frame = max(0, min(frame, self._total_frames))

        progress = frame / self._total_frames
        return self._bar_left + (progress * self._bar_width)

    def _x_to_frame(self, x: float) -> int:
        """
        Convert X position to frame number.

        Args:
            x: X position on the bar

        Returns:
            Frame number
        """
        if self._bar_width <= 0:
            return 0
        progress = (x - self._bar_left) / self._bar_width
        return int(progress * self._total_frames)

    def on_resize(self, window) -> None:
        """Handle window resize."""
        self._calculate_bar_dimensions(window)

    def draw(self, window) -> None:
        """Draw the progress bar component."""
        if not self._visible:
            return

        self._calculate_bar_dimensions(window)
        current_frame = int(getattr(window, "frame_index", 0))
        bar_center_y = self.bottom + self.height / 2

        # Draw background bar
        bg_rect = arcade.XYWH(
            self._bar_left + self._bar_width / 2, bar_center_y, self._bar_width, self.height
        )
        arcade.draw_rect_filled(bg_rect, self.COLORS["background"])
        arcade.draw_rect_outline(bg_rect, self.COLORS["progress_border"], 2)

        # Draw progress fill
        if self._total_frames > 0:
            progress_ratio = min(1.0, current_frame / self._total_frames)
            progress_width = progress_ratio * self._bar_width
            if progress_width > 0:
                progress_rect = arcade.XYWH(
                    self._bar_left + progress_width / 2,
                    bar_center_y,
                    progress_width,
                    self.height - 4,
                )
                arcade.draw_rect_filled(progress_rect, self.COLORS["progress_fill"])

        # Draw lap markers
        if self._total_laps > 1:
            for lap in range(1, self._total_laps + 1):
                lap_frame = int((lap / self._total_laps) * self._total_frames)
                lap_x = self._frame_to_x(lap_frame)
                arcade.draw_line(
                    lap_x,
                    self.bottom + 2,
                    lap_x,
                    self.bottom + self.height - 2,
                    self.COLORS["lap_marker"],
                    1,
                )
                if lap == 1 or lap == self._total_laps or lap % 10 == 0:
                    arcade.Text(
                        str(lap),
                        lap_x,
                        self.bottom - 4,
                        self.COLORS["text"],
                        9,
                        anchor_x="center",
                        anchor_y="top",
                    ).draw()

        # Draw event markers
        for event in self._events:
            event_x = self._frame_to_x(event.get("frame", 0))
            self._draw_event_marker(event, event_x, bar_center_y)

        # Draw current position indicator
        current_x = self._frame_to_x(current_frame)
        arcade.draw_line(
            current_x,
            self.bottom - 2,
            current_x,
            self.bottom + self.height + 2,
            self.COLORS["current_position"],
            3,
        )

    def _draw_event_marker(self, event: dict[str, Any], x: float, center_y: float) -> None:
        """Draw a single event marker based on type."""
        event_type = event.get("type", "")
        marker_top = self.bottom + self.height + self.marker_height

        if event_type == self.EVENT_DNF:
            size = 6
            color = self.COLORS["dnf"]
            y = marker_top - size
            arcade.draw_line(x - size, y - size, x + size, y + size, color, 2)
            arcade.draw_line(x - size, y + size, x + size, y - size, color, 2)
        elif event_type in (
            self.EVENT_YELLOW_FLAG,
            self.EVENT_RED_FLAG,
            self.EVENT_SAFETY_CAR,
            self.EVENT_VSC,
        ):
            color = self.COLORS.get(event_type, self.COLORS["yellow_flag"])
            self._draw_flag_segment(event, color)

    def _draw_flag_segment(self, event: dict[str, Any], color: tuple) -> None:
        """Draw a flag segment on the progress bar."""
        start_frame = event.get("frame", 0)
        end_frame = event.get("end_frame", start_frame + 100)

        clamped_start = max(0, min(start_frame, self._total_frames))
        clamped_end = max(0, min(end_frame, self._total_frames))

        if clamped_start >= clamped_end:
            return

        start_x = self._frame_to_x(clamped_start, clamp=False)
        end_x = self._frame_to_x(clamped_end, clamp=False)

        bar_right = self._bar_left + self._bar_width
        start_x = max(self._bar_left, min(start_x, bar_right))
        end_x = max(self._bar_left, min(end_x, bar_right))

        segment_width = end_x - start_x
        if segment_width <= 0:
            return

        segment_width = max(4, segment_width)
        segment_rect = arcade.XYWH(
            start_x + segment_width / 2, self.bottom + self.height + 4, segment_width, 6
        )
        arcade.draw_rect_filled(segment_rect, color)

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int) -> bool:
        """Handle mouse click to seek to position."""
        if not self._visible:
            return False

        if (
            self._bar_left <= x <= self._bar_left + self._bar_width
            and self.bottom - 5 <= y <= self.bottom + self.height + 5
        ):
            target_frame = self._x_to_frame(x)
            if hasattr(window, "frame_index"):
                window.frame_index = float(max(0, min(target_frame, self._total_frames - 1)))
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
        if not self._visible:
            return

        self._mouse_x = x
        self._mouse_y = y

        # Check if mouse is over the progress bar area
        if (
            self._bar_left <= x <= self._bar_left + self._bar_width
            and self.bottom <= y <= self.bottom + self.height + self.marker_height + 10
        ):
            # Find nearest event
            mouse_frame = self._x_to_frame(x)
            nearest_event = None
            min_dist = float("inf")

            for event in self._events:
                event_frame = event.get("frame", 0)
                dist = abs(event_frame - mouse_frame)
                if dist < min_dist and dist < self._total_frames * 0.02:  # Within 2% of timeline
                    min_dist = dist
                    nearest_event = event

            self._hover_event = nearest_event
        else:
            self._hover_event = None

    def draw_overlays(self, window) -> None:
        """
        Draw tooltips and other overlays that should appear on top of all UI elements.

        Args:
            window: The arcade window instance
        """
        if not self._visible:
            return

        # Draw hover tooltip if applicable
        if self._hover_event:
            self._draw_tooltip(window, self._hover_event)

    def _draw_tooltip(self, window, event: dict[str, Any]) -> None:
        """
        Draw a tooltip for a hovered event.

        Args:
            window: The arcade window instance
            event: Event dictionary to show tooltip for
        """
        event_type = event.get("type", "")
        label = event.get("label", "")
        lap = event.get("lap", "")

        # Build tooltip text
        type_names = {
            self.EVENT_DNF: "DNF",
            self.EVENT_YELLOW_FLAG: "Yellow Flag",
            self.EVENT_RED_FLAG: "Red Flag",
            self.EVENT_SAFETY_CAR: "Safety Car",
            self.EVENT_VSC: "Virtual SC",
        }

        tooltip_text = type_names.get(event_type, "Event")
        if label:
            tooltip_text = f"{tooltip_text}: {label}"
        if lap:
            tooltip_text = f"{tooltip_text} (Lap {lap})"

        # Calculate position
        event_x = self._frame_to_x(event.get("frame", 0))
        tooltip_x = min(max(event_x, 100), window.width - 100)
        tooltip_y = self.bottom + self.height + self.marker_height + 20

        # Draw tooltip background
        padding = 8
        text_obj = arcade.Text(tooltip_text, 0, 0, (255, 255, 255), 12)
        text_width = text_obj.content_width

        bg_rect = arcade.XYWH(tooltip_x, tooltip_y, text_width + padding * 2, 20)
        arcade.draw_rect_filled(bg_rect, (40, 40, 40, 230))
        arcade.draw_rect_outline(bg_rect, (100, 100, 100), 1)

        # Draw text
        arcade.Text(
            tooltip_text,
            tooltip_x,
            tooltip_y,
            (255, 255, 255),
            12,
            anchor_x="center",
            anchor_y="center",
        ).draw()
