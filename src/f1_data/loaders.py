"""Session loading functions for FastF1."""

import logging

import fastf1
import fastf1.plotting
from fastf1.core import Session

logger = logging.getLogger(__name__)


def enable_cache(cache_dir: str = ".fastf1-cache") -> None:
    """
    Enable FastF1 cache.

    Args:
        cache_dir: Path to cache directory
    """
    import os

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        logger.info(f"ℹ️ Created FastF1 cache directory: {cache_dir}")

    fastf1.Cache.enable_cache(cache_dir)
    logger.debug(f"🐞 FastF1 cache enabled at {cache_dir}")


def load_session(year: int, round_number: int, session_type: str = "R") -> Session:
    """
    Load a FastF1 session.

    Args:
        year: F1 season year
        round_number: Round number (1-24)
        session_type: Session type ('R'=Race, 'S'=Sprint, 'Q'=Qualifying, etc.)

    Returns:
        Loaded FastF1 session object

    Raises:
        ValueError: If session cannot be loaded
    """
    try:
        logger.info(f"ℹ️ Loading session: {year} Round {round_number} ({session_type})")
        session = fastf1.get_session(year, round_number, session_type)
        session.load(telemetry=True, weather=True)
        logger.info("ℹ️ Session loaded successfully")
        return session
    except Exception as e:
        logger.error(f"❌ Failed to load session: {e}")
        raise ValueError(
            f"Could not load session {year} Round {round_number} ({session_type}): {e}"
        ) from e


def get_driver_colors(session: Session) -> dict[str, tuple[int, int, int]]:
    """
    Get driver color mapping from session.

    Args:
        session: FastF1 session object

    Returns:
        Dictionary mapping driver codes to RGB tuples
    """
    try:
        color_mapping = fastf1.plotting.get_driver_color_mapping(session)
        rgb_colors: dict[str, tuple[int, int, int]] = {}

        for driver, hex_color in color_mapping.items():
            hex_color = hex_color.lstrip("#")
            rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            rgb_colors[driver] = rgb

        logger.debug(f"🐞 Loaded colors for {len(rgb_colors)} drivers")
        return rgb_colors
    except Exception as e:
        logger.warning(f"⚠️ Failed to get driver colors: {e}")
        return {}


def get_circuit_rotation(session: Session) -> float:
    """
    Get circuit rotation angle.

    Args:
        session: FastF1 session object

    Returns:
        Rotation angle in degrees
    """
    try:
        circuit = session.get_circuit_info()
        rotation = circuit.rotation
        logger.debug(f"🐞 Circuit rotation: {rotation}°")
        return rotation
    except Exception as e:
        logger.warning(f"⚠️ Failed to get circuit rotation: {e}")
        return 0.0


def list_rounds(year: int) -> None:
    """
    List all F1 rounds for a given year.

    Args:
        year: F1 season year
    """
    enable_cache()
    logger.info(f"ℹ️ F1 Schedule {year}")
    schedule = fastf1.get_event_schedule(year)
    for _, event in schedule.iterrows():
        print(f"{event['RoundNumber']}: {event['EventName']}")


def list_sprints(year: int) -> None:
    """
    List all sprint rounds for a given year.

    Args:
        year: F1 season year
    """
    enable_cache()
    logger.info(f"ℹ️ F1 Sprint Races {year}")
    schedule = fastf1.get_event_schedule(year)

    # Determine sprint session name based on year
    sprint_name = "sprint_qualifying"
    if year == 2023:
        sprint_name = "sprint_shootout"
    elif year in [2021, 2022]:
        sprint_name = "sprint"

    sprints = schedule[schedule["EventFormat"] == sprint_name]
    if sprints.empty:
        logger.info(f"ℹ️ No sprint races found for {year}.")
        print(f"No sprint races found for {year}.")
    else:
        for _, event in sprints.iterrows():
            print(f"{event['RoundNumber']}: {event['EventName']}")
