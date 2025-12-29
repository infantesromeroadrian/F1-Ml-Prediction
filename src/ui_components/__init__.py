"""UI Components for F1 Race Replay application."""

from src.ui_components.base import BaseComponent
from src.ui_components.controls import RaceControlsComponent
from src.ui_components.driver_info import DriverInfoComponent
from src.ui_components.lap_time_leaderboard import LapTimeLeaderboardComponent
from src.ui_components.leaderboard import LeaderboardComponent
from src.ui_components.legend import LegendComponent
from src.ui_components.progress_bar import RaceProgressBarComponent, extract_race_events
from src.ui_components.qualifying_selector import QualifyingSegmentSelectorComponent
from src.ui_components.track_utils import build_track_from_example_lap, plotDRSzones
from src.ui_components.weather import WeatherComponent

__all__ = [
    "BaseComponent",
    "DriverInfoComponent",
    "LapTimeLeaderboardComponent",
    "LeaderboardComponent",
    "LegendComponent",
    "QualifyingSegmentSelectorComponent",
    "RaceControlsComponent",
    "RaceProgressBarComponent",
    "WeatherComponent",
    "build_track_from_example_lap",
    "extract_race_events",
    "plotDRSzones",
]
