"""Functions for extracting and calculating features for ML model."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_historical_stats(
    df: pd.DataFrame, current_year: int, current_round: int
) -> pd.DataFrame:
    """
    Calculate historical statistics for each driver up to the current race.

    This function calculates cumulative statistics that would have been
    available BEFORE the current race (important for temporal validity).

    Args:
        df: DataFrame with all race data (must be sorted by year, round)
        current_year: Year of the race we're calculating stats for
        current_round: Round number of the race we're calculating stats for

    Returns:
        DataFrame with historical statistics added
    """
    logger.info(f"ℹ️ Calculating historical stats up to {current_year} Round {current_round}")

    # Filter data up to (but not including) current race
    historical_data = df[
        (df["year"] < current_year)
        | ((df["year"] == current_year) & (df["round_number"] < current_round))
    ].copy()

    if historical_data.empty:
        logger.warning("⚠️ No historical data available")
        return df.copy()

    # Initialize result dataframe
    result = df.copy()

    # For each driver, calculate cumulative stats
    for driver_code in result["driver_code"].unique():
        driver_history = historical_data[historical_data["driver_code"] == driver_code]

        if driver_history.empty:
            continue

        # Filter to current race rows for this driver
        current_race_mask = (
            (result["driver_code"] == driver_code)
            & (result["year"] == current_year)
            & (result["round_number"] == current_round)
        )

        if not current_race_mask.any():
            continue

        # Calculate statistics
        wins_so_far = int((driver_history["winner"] == 1).sum())
        points_so_far = float(driver_history["points"].sum())
        podiums_so_far = int((driver_history["race_position"] <= 3).sum())
        races_so_far = len(driver_history)

        # Average position (excluding DNFs)
        finished_races = driver_history[driver_history["dnf"] == 0]
        if not finished_races.empty:
            avg_position = float(finished_races["race_position"].mean())
        else:
            avg_position = None

        # Average position in last 5 races
        last_5 = finished_races.tail(5)
        if not last_5.empty:
            avg_position_last_5 = float(last_5["race_position"].mean())
        else:
            avg_position_last_5 = None

        # Constructor stats
        constructor = result[current_race_mask]["constructor"].iloc[0]
        constructor_history = historical_data[historical_data["constructor"] == constructor]
        constructor_points_so_far = float(constructor_history["points"].sum())
        constructor_wins_so_far = int((constructor_history["winner"] == 1).sum())

        # Circuit-specific stats
        circuit_name = result[current_race_mask]["circuit_name"].iloc[0]
        circuit_history = driver_history[driver_history["circuit_name"] == circuit_name]
        circuit_wins = int((circuit_history["winner"] == 1).sum())
        circuit_races = len(circuit_history)
        if circuit_races > 0:
            circuit_finished = circuit_history[circuit_history["dnf"] == 0]
            if not circuit_finished.empty:
                circuit_avg_position = float(circuit_finished["race_position"].mean())
            else:
                circuit_avg_position = None
        else:
            circuit_avg_position = None

        # Update result dataframe
        result.loc[current_race_mask, "wins_so_far"] = wins_so_far
        result.loc[current_race_mask, "points_so_far"] = points_so_far
        result.loc[current_race_mask, "podiums_so_far"] = podiums_so_far
        result.loc[current_race_mask, "races_so_far"] = races_so_far
        result.loc[current_race_mask, "avg_position_so_far"] = avg_position
        result.loc[current_race_mask, "avg_position_last_5"] = avg_position_last_5
        result.loc[current_race_mask, "constructor_points_so_far"] = constructor_points_so_far
        result.loc[current_race_mask, "constructor_wins_so_far"] = constructor_wins_so_far
        result.loc[current_race_mask, "circuit_wins_history"] = circuit_wins
        result.loc[current_race_mask, "circuit_races_history"] = circuit_races
        result.loc[current_race_mask, "circuit_avg_position"] = circuit_avg_position

    logger.info("ℹ️ Historical stats calculated")
    return result


def add_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add additional feature columns to the dataframe.

    Args:
        df: DataFrame with race data

    Returns:
        DataFrame with additional features
    """
    result = df.copy()

    # Initialize historical columns if they don't exist
    historical_cols = [
        "wins_so_far",
        "points_so_far",
        "podiums_so_far",
        "races_so_far",
        "avg_position_so_far",
        "avg_position_last_5",
        "constructor_points_so_far",
        "constructor_wins_so_far",
        "circuit_wins_history",
        "circuit_races_history",
        "circuit_avg_position",
    ]

    for col in historical_cols:
        if col not in result.columns:
            result[col] = None

    # Calculate derived features
    # Grid position (use qualifying position, fallback to race position if missing)
    if "grid_position" not in result.columns:
        result["grid_position"] = result.get(
            "qualifying_position", result.get("race_position", None)
        )

    # Qualifying time difference from pole (if available)
    if "qualifying_best_time" in result.columns:
        pole_time = result.groupby(["year", "round_number"])["qualifying_best_time"].transform(
            "min"
        )
        result["qualifying_time_from_pole"] = result["qualifying_best_time"] - pole_time

    # Points per race (if races_so_far available)
    if "points_so_far" in result.columns and "races_so_far" in result.columns:
        result["points_per_race"] = result["points_so_far"] / result["races_so_far"].replace(
            0, np.nan
        )

    # Win rate
    if "wins_so_far" in result.columns and "races_so_far" in result.columns:
        result["win_rate"] = result["wins_so_far"] / result["races_so_far"].replace(0, np.nan)

    # Podium rate
    if "podiums_so_far" in result.columns and "races_so_far" in result.columns:
        result["podium_rate"] = result["podiums_so_far"] / result["races_so_far"].replace(0, np.nan)

    logger.debug("🐞 Added feature columns")
    return result


def prepare_ml_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare final dataset for machine learning.

    This function:
    - Ensures proper column order
    - Handles missing values
    - Creates final feature set

    Args:
        df: DataFrame with all features

    Returns:
        DataFrame ready for ML
    """
    result = df.copy()

    # Define column order (features first, then target)
    feature_columns = [
        # Identifiers
        "year",
        "round_number",
        "circuit_name",
        "country",
        "event_name",
        "driver_code",
        "driver_number",
        "constructor",
        # Pre-race features
        "grid_position",
        "qualifying_position",
        "q1_time",
        "q2_time",
        "q3_time",
        "qualifying_best_time",
        "qualifying_time_from_pole",
        # Historical features
        "wins_so_far",
        "points_so_far",
        "podiums_so_far",
        "races_so_far",
        "avg_position_so_far",
        "avg_position_last_5",
        "points_per_race",
        "win_rate",
        "podium_rate",
        # Constructor features
        "constructor_points_so_far",
        "constructor_wins_so_far",
        # Circuit-specific features
        "circuit_wins_history",
        "circuit_races_history",
        "circuit_avg_position",
        "circuit_length",
        # Weather features
        "avg_air_temp",
        "avg_track_temp",
        "avg_humidity",
        "avg_wind_speed",
        "max_rainfall",
        "had_rain",
    ]

    # Target variables
    target_columns = ["race_position", "points", "winner", "dnf", "status", "fastest_lap_time"]

    # Reorder columns (only include columns that exist)
    all_columns = [col for col in feature_columns + target_columns if col in result.columns]
    other_columns = [col for col in result.columns if col not in all_columns]

    result = result[all_columns + other_columns]

    # Sort by year, round, race_position for easier inspection
    result = result.sort_values(["year", "round_number", "race_position"], na_position="last")

    logger.info(f"ℹ️ Prepared ML dataset with {len(result)} rows and {len(result.columns)} columns")
    return result
