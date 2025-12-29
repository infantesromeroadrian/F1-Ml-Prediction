"""Driver info component for displaying detailed telemetry."""

from typing import Any

import arcade
from src.ui_components.base import BaseComponent
from src.ui_components.leaderboard import LeaderboardComponent


class DriverInfoComponent(BaseComponent):
    """Component that displays detailed telemetry for selected drivers."""

    def __init__(self, left: int = 20, width: int = 220, min_top: int = 220) -> None:
        """
        Initialize driver info component.

        Args:
            left: Left position
            width: Component width
            min_top: Minimum top position
        """
        self.left = left
        self.width = width
        self.min_top = min_top

    def draw(self, window) -> None:
        """Draw driver info boxes for selected drivers."""
        # Support multiple selection via window.selected_drivers
        codes = getattr(window, "selected_drivers", [])
        if not codes:
            # Fallback to single selection compatibility
            single = getattr(window, "selected_driver", None)
            codes = [single] if single else []

        if not codes or not window.frames:
            return

        idx = min(int(window.frame_index), window.n_frames - 1)
        frame = window.frames[idx]

        box_width, box_height, gap = self.width, 210, 10
        weather_bottom = getattr(window, "weather_bottom", None)
        current_top = weather_bottom - 20 if weather_bottom else window.height - 200

        for code in codes:
            if code not in frame["drivers"]:
                continue
            if current_top - box_height < self.min_top:
                break

            driver_pos = frame["drivers"][code]
            center_y = current_top - (box_height / 2)
            self._draw_info_box(window, code, driver_pos, center_y, box_width, box_height)
            current_top -= box_height + gap

    def _draw_info_box(
        self,
        window,
        code: str,
        driver_pos: dict[str, Any],
        center_y: float,
        box_width: float,
        box_height: float,
    ) -> None:
        """Draw a single driver info box."""
        center_x = self.left + box_width / 2
        top = center_y + box_height / 2
        bottom = center_y - box_height / 2
        left = center_x - box_width / 2
        right = center_x + box_width / 2

        rect = arcade.XYWH(center_x, center_y, box_width, box_height)
        arcade.draw_rect_filled(rect, (0, 0, 0, 200))

        team_color = window.driver_colors.get(code, arcade.color.GRAY)
        arcade.draw_rect_outline(rect, team_color, 2)

        # Header
        header_height = 30
        header_cy = top - (header_height / 2)
        arcade.draw_rect_filled(
            arcade.XYWH(center_x, header_cy, box_width, header_height), team_color
        )
        arcade.Text(
            f"Driver: {code}",
            left + 10,
            header_cy,
            arcade.color.BLACK,
            14,
            anchor_y="center",
            bold=True,
        ).draw()

        cursor_y = top - header_height - 25
        row_gap = 25
        left_text_x = left + 15

        # Telemetry text
        speed = driver_pos.get("speed", 0)
        arcade.Text(
            f"Speed: {speed:.0f} km/h",
            left + 15,
            cursor_y,
            arcade.color.WHITE,
            12,
            anchor_y="center",
        ).draw()
        cursor_y -= row_gap

        arcade.Text(
            f"Gear: {driver_pos.get('gear', '-')}",
            left + 15,
            cursor_y,
            arcade.color.WHITE,
            12,
            anchor_y="center",
        ).draw()
        cursor_y -= row_gap

        # DRS status
        drs_val = driver_pos.get("drs", 0)
        if drs_val in [10, 12, 14]:
            drs_str, drs_color = "DRS: ON", arcade.color.GREEN
        elif drs_val == 8:
            drs_str, drs_color = "DRS: AVAIL", arcade.color.YELLOW
        else:
            drs_str, drs_color = "DRS: OFF", arcade.color.GRAY

        arcade.Text(
            drs_str, left + 15, cursor_y, drs_color, 12, anchor_y="center", bold=True
        ).draw()
        cursor_y -= row_gap

        # Gaps (calculated from leaderboard)
        gap_ahead, gap_behind = "Ahead: N/A", "Behind: N/A"
        lb = self._find_leaderboard(window)

        REFERENCE_SPEED_MS = 55.56  # 200 km/h = 55.56 m/s

        def calculate_gap(pos1: float, pos2: float) -> tuple[float, float]:
            """Calculate gap between two positions."""
            raw_dist = abs(pos1 - pos2)
            dist = raw_dist / 10.0  # Convert to meters
            time = dist / REFERENCE_SPEED_MS
            return dist, time

        if lb and hasattr(lb, "entries") and lb.entries:
            try:
                idx = next(i for i, e in enumerate(lb.entries) if e[0] == code)

                if idx > 0:  # Car ahead
                    code_ahead = lb.entries[idx - 1][0]
                    curr_pos = lb.entries[idx][3]
                    ahead_pos = lb.entries[idx - 1][3]
                    dist, time = calculate_gap(curr_pos, ahead_pos)
                    gap_ahead = f"Ahead ({code_ahead}): +{time:.2f}s ({dist:.1f}m)"

                if idx < len(lb.entries) - 1:  # Car behind
                    code_behind = lb.entries[idx + 1][0]
                    curr_pos = lb.entries[idx][3]
                    behind_pos = lb.entries[idx + 1][3]
                    dist, time = calculate_gap(curr_pos, behind_pos)
                    gap_behind = f"Behind ({code_behind}): -{time:.2f}s ({dist:.1f}m)"
            except (StopIteration, IndexError):
                pass

        arcade.Text(
            gap_ahead, left_text_x, cursor_y, arcade.color.LIGHT_GRAY, 11, anchor_y="center"
        ).draw()
        cursor_y -= 22
        arcade.Text(
            gap_behind, left_text_x, cursor_y, arcade.color.LIGHT_GRAY, 11, anchor_y="center"
        ).draw()

        # Throttle and brake graphs
        thr = driver_pos.get("throttle", 0)
        brk = driver_pos.get("brake", 0)
        t_r = max(0.0, min(1.0, thr / 100.0))
        b_r = max(0.0, min(1.0, brk / 100.0 if brk > 1.0 else brk))
        bar_w, bar_h, b_y = 20, 80, bottom + 35
        r_center = right - 50

        # Throttle bar
        arcade.Text(
            "THR", r_center - 15, b_y - 20, arcade.color.WHITE, 10, anchor_x="center"
        ).draw()
        arcade.draw_rect_filled(
            arcade.XYWH(r_center - 15, b_y + bar_h / 2, bar_w, bar_h), arcade.color.DARK_GRAY
        )
        if t_r > 0:
            arcade.draw_rect_filled(
                arcade.XYWH(r_center - 15, b_y + (bar_h * t_r) / 2, bar_w, bar_h * t_r),
                arcade.color.GREEN,
            )

        # Brake bar
        arcade.Text(
            "BRK", r_center + 15, b_y - 20, arcade.color.WHITE, 10, anchor_x="center"
        ).draw()
        arcade.draw_rect_filled(
            arcade.XYWH(r_center + 15, b_y + bar_h / 2, bar_w, bar_h), arcade.color.DARK_GRAY
        )
        if b_r > 0:
            arcade.draw_rect_filled(
                arcade.XYWH(r_center + 15, b_y + (bar_h * b_r) / 2, bar_w, bar_h * b_r),
                arcade.color.RED,
            )

    def _find_leaderboard(self, window) -> LeaderboardComponent | None:
        """Find the leaderboard component from window."""
        lb = (
            getattr(window, "leaderboard", None)
            or getattr(window, "leaderboard_ui", None)
            or getattr(window, "leaderboard_comp", None)
        )

        if not lb and hasattr(window, "ui_components"):
            for comp in window.ui_components:
                if isinstance(comp, LeaderboardComponent):
                    return comp

        return lb
