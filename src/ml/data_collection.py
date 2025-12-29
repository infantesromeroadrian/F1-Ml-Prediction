"""Functions for collecting historical F1 race data."""

import logging
from typing import Any

import fastf1
import pandas as pd
from fastf1 import get_session
from fastf1.core import Session
from src.f1_data.loaders import enable_cache

logger = logging.getLogger(__name__)


def get_season_schedule(year: int) -> pd.DataFrame:
    """
    Get the complete schedule for a season.

    Args:
        year: F1 season year

    Returns:
        DataFrame with schedule information
    """
    try:
        enable_cache()
        schedule = fastf1.get_event_schedule(year)
        logger.info(f"ℹ️ Loaded schedule for {year}: {len(schedule)} events")
        return schedule
    except Exception as e:
        logger.error(f"❌ Failed to load schedule for {year}: {e}")
        raise


def extract_race_results(session: Session) -> pd.DataFrame:
    """
    Extract race results from a session.

    Args:
        session: FastF1 race session object

    Returns:
        DataFrame with race results (driver, position, points, etc.)
    """
    try:
        results = session.results

        race_data: list[dict[str, Any]] = []

        for _, row in results.iterrows():
            driver_code = row["Abbreviation"]
            driver_number = row["DriverNumber"]
            constructor = row["TeamName"]
            position = int(row["Position"]) if pd.notna(row["Position"]) else None
            points = float(row["Points"]) if pd.notna(row["Points"]) else 0.0
            status = str(row["Status"]) if pd.notna(row["Status"]) else "Unknown"

            # Check if finished
            dnf = status != "Finished" or position is None

            # Get fastest lap info
            fastest_lap = row.get("FastestLapTime", None)
            fastest_lap_time = None
            if pd.notna(fastest_lap):
                try:
                    fastest_lap_time = fastest_lap.total_seconds()
                except (AttributeError, TypeError):
                    fastest_lap_time = None

            race_data.append(
                {
                    "driver_code": driver_code,
                    "driver_number": driver_number,
                    "constructor": constructor,
                    "race_position": position,
                    "points": points,
                    "status": status,
                    "dnf": dnf,
                    "fastest_lap_time": fastest_lap_time,
                    "winner": 1 if position == 1 else 0,
                }
            )

        df = pd.DataFrame(race_data)
        logger.info(f"ℹ️ Extracted race results for {len(df)} drivers")
        return df

    except Exception as e:
        logger.error(f"❌ Error extracting race results: {e}")
        raise


def extract_qualifying_results(session: Session) -> pd.DataFrame:
    """
    Extract qualifying results from a session.

    Args:
        session: FastF1 qualifying session object

    Returns:
        DataFrame with qualifying results (position, Q1/Q2/Q3 times)
    """
    try:
        results = session.results

        quali_data: list[dict[str, Any]] = []

        for _, row in results.iterrows():
            driver_code = row["Abbreviation"]
            position = int(row["Position"]) if pd.notna(row["Position"]) else None

            # Extract Q1, Q2, Q3 times
            q1_time = row.get("Q1", None)
            q2_time = row.get("Q2", None)
            q3_time = row.get("Q3", None)

            def convert_time_to_seconds(time_val: Any) -> float | None:
                """Convert pandas Timedelta to seconds."""
                if pd.isna(time_val):
                    return None
                try:
                    return time_val.total_seconds()
                except (AttributeError, TypeError):
                    return None

            q1_seconds = convert_time_to_seconds(q1_time)
            q2_seconds = convert_time_to_seconds(q2_time)
            q3_seconds = convert_time_to_seconds(q3_time)

            # Best qualifying time (prefer Q3, then Q2, then Q1)
            best_time = (
                q3_seconds
                if q3_seconds is not None
                else (q2_seconds if q2_seconds is not None else q1_seconds)
            )

            quali_data.append(
                {
                    "driver_code": driver_code,
                    "qualifying_position": position,
                    "q1_time": q1_seconds,
                    "q2_time": q2_seconds,
                    "q3_time": q3_seconds,
                    "qualifying_best_time": best_time,
                }
            )

        df = pd.DataFrame(quali_data)
        logger.info(f"ℹ️ Extracted qualifying results for {len(df)} drivers")
        return df

    except Exception as e:
        logger.error(f"❌ Error extracting qualifying results: {e}")
        raise


def extract_weather_data(session: Session) -> dict[str, Any] | None:
    """
    Extract weather data from a session.

    Args:
        session: FastF1 session object

    Returns:
        Dictionary with weather information or None if not available
    """
    try:
        weather_df = getattr(session, "weather_data", None)

        if weather_df is None or weather_df.empty:
            logger.debug("🐞 No weather data available for session")
            return None

        # Get average weather conditions during the race
        weather_info = {
            "avg_air_temp": float(weather_df["AirTemp"].mean())
            if "AirTemp" in weather_df.columns
            else None,
            "avg_track_temp": float(weather_df["TrackTemp"].mean())
            if "TrackTemp" in weather_df.columns
            else None,
            "avg_humidity": float(weather_df["Humidity"].mean())
            if "Humidity" in weather_df.columns
            else None,
            "avg_wind_speed": float(weather_df["WindSpeed"].mean())
            if "WindSpeed" in weather_df.columns
            else None,
            "max_rainfall": float(weather_df["Rainfall"].max())
            if "Rainfall" in weather_df.columns
            else 0.0,
            "had_rain": bool((weather_df["Rainfall"] > 0.5).any())
            if "Rainfall" in weather_df.columns
            else False,
        }

        logger.debug("🐞 Extracted weather data")
        return weather_info

    except Exception as e:
        logger.warning(f"⚠️ Error extracting weather data: {e}")
        return None


def extract_circuit_info(session: Session) -> dict[str, Any]:
    """
    Extract circuit information from a session.

    Args:
        session: FastF1 session object

    Returns:
        Dictionary with circuit information
    """
    try:
        event = session.event
        circuit_info = session.get_circuit_info()

        circuit_data = {
            "circuit_name": str(event["Location"]),
            "country": str(event["Country"]),
            "round_number": int(event["RoundNumber"]),
            "event_name": str(event["EventName"]),
            "circuit_length": float(circuit_info.circuit_length)
            if hasattr(circuit_info, "circuit_length")
            else None,
        }

        logger.debug(f"🐞 Extracted circuit info: {circuit_data['circuit_name']}")
        return circuit_data

    except Exception as e:
        logger.warning(f"⚠️ Error extracting circuit info: {e}")
        return {
            "circuit_name": "Unknown",
            "country": "Unknown",
            "round_number": None,
            "event_name": "Unknown",
            "circuit_length": None,
        }


def collect_race_data(
    year: int, round_number: int, load_telemetry: bool = False
) -> pd.DataFrame | None:
    """
    Collect complete race data for a specific race.

    Args:
        year: F1 season year
        round_number: Round number
        load_telemetry: Whether to load telemetry (slower but more data)

    Returns:
        DataFrame with race data for all drivers, or None if race not found
    """
    try:
        logger.info(f"ℹ️ Collecting data for {year} Round {round_number}")

        # Load race session
        try:
            race_session = get_session(year, round_number, "R")
            race_session.load(telemetry=load_telemetry, weather=True)
        except Exception as e:
            logger.warning(f"⚠️ Could not load race session: {e}")
            return None

        # Load qualifying session
        quali_session = None
        try:
            quali_session = get_session(year, round_number, "Q")
            quali_session.load(telemetry=False, weather=False)
        except Exception as e:
            logger.warning(f"⚠️ Could not load qualifying session: {e}")

        # Extract data
        race_results = extract_race_results(race_session)
        quali_results = (
            extract_qualifying_results(quali_session) if quali_session else pd.DataFrame()
        )
        weather_data = extract_weather_data(race_session)
        circuit_data = extract_circuit_info(race_session)

        # Merge race and qualifying results
        if not quali_results.empty:
            merged = race_results.merge(quali_results, on="driver_code", how="left")
        else:
            merged = race_results.copy()
            merged["qualifying_position"] = None
            merged["q1_time"] = None
            merged["q2_time"] = None
            merged["q3_time"] = None
            merged["qualifying_best_time"] = None

        # Add weather and circuit data to all rows
        for key, value in circuit_data.items():
            merged[key] = value

        if weather_data:
            for key, value in weather_data.items():
                merged[key] = value
        else:
            # Fill with None if no weather data
            merged["avg_air_temp"] = None
            merged["avg_track_temp"] = None
            merged["avg_humidity"] = None
            merged["avg_wind_speed"] = None
            merged["max_rainfall"] = 0.0
            merged["had_rain"] = False

        # Add metadata
        merged["year"] = year
        merged["round_number"] = round_number

        # Grid position (same as qualifying position for most cases)
        merged["grid_position"] = merged["qualifying_position"]

        logger.info(f"ℹ️ Collected data for {len(merged)} drivers")
        return merged

    except Exception as e:
        logger.error(f"❌ Error collecting race data for {year} Round {round_number}: {e}")
        return None
