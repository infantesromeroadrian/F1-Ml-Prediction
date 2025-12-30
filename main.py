"""Main entry point for F1 Race Replay application."""

import sys
import logging

from src.f1_data.loaders import (
    enable_cache,
    get_circuit_rotation,
    list_rounds,
    list_sprints,
    load_session,
)
from src.f1_data.processors import (
    get_race_telemetry,
    get_quali_telemetry,
)
from src.arcade_replay import run_arcade_replay
from src.interfaces.qualifying import run_qualifying_replay
from src.logging_config import setup_logging
from src.ml.prediction import create_prediction_engine

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def main(
    year: int | None = None,
    round_number: int | None = None,
    playback_speed: float = 1.0,
    session_type: str = "R",
    visible_hud: bool = True,
) -> None:
    """
    Main function to load and run F1 race replay.

    Args:
        year: F1 season year
        round_number: Round number (1-24)
        playback_speed: Playback speed multiplier
        session_type: Session type ('R'=Race, 'S'=Sprint, 'Q'=Qualifying, 'SQ'=Sprint Qualifying)
        visible_hud: Whether to show HUD elements
    """
    logger.info(f"ℹ️ Loading F1 {year} Round {round_number} Session '{session_type}'")

    try:
        session = load_session(year, round_number, session_type)
        logger.info(
            f"ℹ️ Loaded session: {session.event['EventName']} - "
            f"{session.event['RoundNumber']} - {session_type}"
        )
    except Exception as e:
        logger.error(f"❌ Failed to load session: {e}")
        raise

    # Enable cache for fastf1
    enable_cache()

    if session_type == "Q" or session_type == "SQ":
        # Get the drivers who participated and their lap times
        qualifying_session_data = get_quali_telemetry(session, session_type=session_type)

        # Run the arcade screen showing qualifying results
        title = f"{session.event['EventName']} - {'Sprint Qualifying' if session_type == 'SQ' else 'Qualifying Results'}"

        run_qualifying_replay(
            session=session,
            data=qualifying_session_data,
            title=title,
        )

    else:
        # Get the drivers who participated in the race
        race_telemetry = get_race_telemetry(session, session_type=session_type)

        # Get example lap for track layout
        # Qualifying lap preferred for DRS zones (fallback to fastest race lap (no DRS data))
        example_lap = None
        quali_session = None

        try:
            logger.info("ℹ️ Attempting to load qualifying session for track layout...")
            quali_session = load_session(year, round_number, "Q")
            if quali_session is not None and len(quali_session.laps) > 0:
                fastest_quali = quali_session.laps.pick_fastest()
                if fastest_quali is not None:
                    quali_telemetry = fastest_quali.get_telemetry()
                    if "DRS" in quali_telemetry.columns:
                        example_lap = quali_telemetry
                        logger.info(
                            f"ℹ️ Using qualifying lap from driver {fastest_quali['Driver']} for DRS Zones"
                        )
        except Exception as e:
            logger.warning(f"⚠️ Could not load qualifying session: {e}")

        # Fallback: Use fastest race lap
        if example_lap is None:
            fastest_lap = session.laps.pick_fastest()
            if fastest_lap is not None:
                example_lap = fastest_lap.get_telemetry()
                logger.info("ℹ️ Using fastest race lap (DRS detection may use speed-based fallback)")
            else:
                logger.error("❌ No valid laps found in session")
                return

        drivers = session.drivers

        # Get circuit rotation
        circuit_rotation = get_circuit_rotation(session)

        # Load ML prediction engine and make predictions
        ml_predictions = None
        try:
            logger.info("ℹ️ Loading ML prediction engine...")
            prediction_engine = create_prediction_engine()
            if prediction_engine is not None:
                logger.info("ℹ️ Making ML predictions...")
                ml_predictions = prediction_engine.predict(session, quali_session)
                logger.info(f"✅ ML predictions completed for {len(ml_predictions)} drivers")
            else:
                logger.warning("⚠️ ML prediction engine not available (models may not be loaded)")
        except Exception as e:
            logger.warning(f"⚠️ Error making ML predictions: {e}")
            logger.warning("⚠️ Continuing without ML predictions")

        # Run the arcade replay
        run_arcade_replay(
            frames=race_telemetry["frames"],
            track_statuses=race_telemetry["track_statuses"],
            example_lap=example_lap,
            drivers=drivers,
            playback_speed=playback_speed,
            driver_colors=race_telemetry["driver_colors"],
            title=f"{session.event['EventName']} - {'Sprint' if session_type == 'S' else 'Race'}",
            total_laps=race_telemetry["total_laps"],
            circuit_rotation=circuit_rotation,
            visible_hud=visible_hud,
            ml_predictions=ml_predictions,
        )


if __name__ == "__main__":
    # Import interactive selector
    from src.interfaces.selector import interactive_session_selector, quick_select_latest_race

    # Check for special flags first
    if "--list-rounds" in sys.argv:
        year_index = (
            sys.argv.index("--list-rounds") + 1
            if len(sys.argv) > sys.argv.index("--list-rounds") + 1
            else None
        )
        year_to_list = (
            int(sys.argv[year_index]) if year_index and sys.argv[year_index].isdigit() else 2024
        )
        list_rounds(year_to_list)
        sys.exit(0)

    if "--list-sprints" in sys.argv:
        year_index = (
            sys.argv.index("--list-sprints") + 1
            if len(sys.argv) > sys.argv.index("--list-sprints") + 1
            else None
        )
        year_to_list = (
            int(sys.argv[year_index]) if year_index and sys.argv[year_index].isdigit() else 2024
        )
        list_sprints(year_to_list)
        sys.exit(0)

    # Determine selection mode
    if "--interactive" in sys.argv or len(sys.argv) == 1:
        # Interactive mode (default if no args)
        year, round_number, session_type = interactive_session_selector()
    elif "--latest" in sys.argv:
        # Quick select latest race
        year, round_number, session_type = quick_select_latest_race()
    else:
        # CLI argument mode (backwards compatible)
        if "--year" in sys.argv:
            year_index = sys.argv.index("--year") + 1
            year = int(sys.argv[year_index])
        else:
            year = 2024  # Changed default to 2024 (more stable data)

        if "--round" in sys.argv:
            round_index = sys.argv.index("--round") + 1
            round_number = int(sys.argv[round_index])
        else:
            round_number = 1  # Default to first round

        # Session type selection
        session_type = (
            "SQ"
            if "--sprint-qualifying" in sys.argv
            else ("S" if "--sprint" in sys.argv else ("Q" if "--qualifying" in sys.argv else "R"))
        )

    # Playback speed
    playback_speed = 1.0
    if "--speed" in sys.argv:
        speed_index = sys.argv.index("--speed") + 1
        playback_speed = float(sys.argv[speed_index])

    # HUD visibility
    visible_hud = "--no-hud" not in sys.argv

    # Run the replay
    main(year, round_number, playback_speed, session_type=session_type, visible_hud=visible_hud)
