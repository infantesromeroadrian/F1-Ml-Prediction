"""Unit tests for configuration module."""

import os
from pathlib import Path

from src.config import AppConfig, get_config, reset_config


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that default configuration values are set correctly."""
        config = AppConfig()
        assert config.fps == 25
        assert config.screen_width == 1920
        assert config.screen_height == 1200
        assert config.log_level == "INFO"
        assert config.environment == "development"

    def test_dt_calculation(self) -> None:
        """Test delta time calculation from FPS."""
        config = AppConfig()
        expected_dt = 1.0 / 25
        assert abs(config.dt - expected_dt) < 1e-6

    def test_environment_variable_override(self) -> None:
        """Test that environment variables override defaults."""
        os.environ["F1_FPS"] = "30"
        os.environ["F1_LOG_LEVEL"] = "DEBUG"

        config = AppConfig()

        assert config.fps == 30
        assert config.log_level == "DEBUG"

        # Cleanup
        del os.environ["F1_FPS"]
        del os.environ["F1_LOG_LEVEL"]

    def test_ensure_directories_creates_dirs(self, tmp_path: Path) -> None:
        """Test that ensure_directories creates necessary directories."""
        cache_dir = tmp_path / "test_cache"
        data_dir = tmp_path / "test_data"

        config = AppConfig()
        config.fastf1_cache_dir = str(cache_dir)
        config.computed_data_dir = str(data_dir)

        config.ensure_directories()

        assert cache_dir.exists()
        assert data_dir.exists()


class TestGetConfig:
    """Tests for get_config singleton function."""

    def test_get_config_returns_same_instance(self) -> None:
        """Test that get_config returns the same instance on multiple calls."""
        reset_config()  # Ensure clean state

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reset_config_creates_new_instance(self) -> None:
        """Test that reset_config allows creating a new config instance."""
        config1 = get_config()
        reset_config()
        config2 = get_config()

        assert config1 is not config2
