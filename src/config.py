"""Configuration management for F1 Race Replay application."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    """Application configuration with environment variable support."""

    # FPS and timing
    fps: int = 25

    # Cache and data directories
    fastf1_cache_dir: str = ".fastf1-cache"
    computed_data_dir: str = "computed_data"

    # UI layout
    screen_width: int = 1920
    screen_height: int = 1200
    left_ui_margin: int = 340
    right_ui_margin: int = 260

    # Track rendering
    track_width: int = 200
    track_padding: float = 0.05

    # Playback defaults
    default_playback_speed: float = 1.0
    playback_speeds: list[float] = field(default_factory=lambda: [0.5, 1.0, 2.0, 4.0])

    # Progress bar
    progress_bar_height: int = 24
    progress_bar_marker_height: int = 16
    progress_bar_bottom: int = 30

    # Leaderboard
    leaderboard_width: int = 240
    leaderboard_row_height: int = 25

    # Weather component
    weather_panel_width: int = 280
    weather_panel_height: int = 130
    weather_top_offset: int = 170

    # Driver info
    driver_info_width: int = 220
    driver_info_min_top: int = 220

    # Controls
    control_button_size: int = 40
    control_button_spacing: int = 70
    control_speed_offset: int = 200

    # Logging
    log_level: str = "INFO"
    log_format: str = (
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    use_emoji_prefixes: bool = True

    # Environment
    environment: str = "development"

    def __post_init__(self) -> None:
        """Load values from environment variables after initialization."""
        # FPS and timing
        self.fps = int(os.getenv("F1_FPS", self.fps))

        # Directories
        self.fastf1_cache_dir = os.getenv("F1_FASTF1_CACHE_DIR", self.fastf1_cache_dir)
        self.computed_data_dir = os.getenv("F1_COMPUTED_DATA_DIR", self.computed_data_dir)

        # UI layout
        self.screen_width = int(os.getenv("F1_SCREEN_WIDTH", self.screen_width))
        self.screen_height = int(os.getenv("F1_SCREEN_HEIGHT", self.screen_height))
        self.left_ui_margin = int(os.getenv("F1_LEFT_UI_MARGIN", self.left_ui_margin))
        self.right_ui_margin = int(os.getenv("F1_RIGHT_UI_MARGIN", self.right_ui_margin))

        # Logging
        self.log_level = os.getenv("F1_LOG_LEVEL", self.log_level).upper()
        self.use_emoji_prefixes = os.getenv("F1_USE_EMOJI_PREFIXES", "true").lower() == "true"
        self.environment = os.getenv("F1_ENVIRONMENT", self.environment).lower()

    @property
    def dt(self) -> float:
        """Calculate delta time from FPS."""
        return 1.0 / self.fps

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        Path(self.fastf1_cache_dir).mkdir(parents=True, exist_ok=True)
        Path(self.computed_data_dir).mkdir(parents=True, exist_ok=True)


# Global config instance
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig()
        _config.ensure_directories()
    return _config


def reset_config() -> None:
    """Reset the global config (useful for testing)."""
    global _config
    _config = None
