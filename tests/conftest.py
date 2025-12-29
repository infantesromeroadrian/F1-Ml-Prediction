"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def models_dir(project_root: Path) -> Path:
    """Return the models directory."""
    return project_root / "models"


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    """Return the data directory."""
    return project_root / "data"


@pytest.fixture
def test_fixtures_dir() -> Path:
    """Return the test fixtures directory."""
    return Path(__file__).parent / "fixtures"
