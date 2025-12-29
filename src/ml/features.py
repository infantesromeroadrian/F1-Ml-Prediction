"""Functions for extracting and calculating features for ML model."""

import hashlib
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


def add_feature_columns(df: pd.DataFrame, enhanced: bool = True) -> pd.DataFrame:
    """
    Add additional feature columns to the dataframe.

    Args:
        df: DataFrame with race data
        enhanced: If True, also adds advanced engineered features (default: True)

    Returns:
        DataFrame with additional features

    Note:
        Set enhanced=False for backward compatibility or when you only need base features.
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

    logger.debug("🐞 Added base feature columns")

    # Add enhanced features if requested
    if enhanced:
        result = add_enhanced_features(result)

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


def add_enhanced_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add advanced engineered features for improved model performance.

    This function creates:
    - Log-transformed features for skewed distributions
    - Normalized features for better scaling
    - Interaction features to capture relationships
    - Composite features for domain insights
    - Categorical encodings

    Args:
        df: DataFrame with base features already added

    Returns:
        DataFrame with enhanced features

    Note:
        This function expects add_feature_columns() to have been called first.
    """
    result = df.copy()

    logger.info("🚀 Adding enhanced features...")

    # ===================================================================
    # 1. LOG TRANSFORMATIONS (8 features)
    # ===================================================================
    # Log transforms help with skewed distributions and reduce impact of outliers

    log_features = [
        "wins_so_far",
        "win_rate",
        "points_so_far",
        "podiums_so_far",
        "points_per_race",
        "podium_rate",
        "constructor_wins_so_far",
        "constructor_points_so_far",
        "circuit_wins_history",
    ]

    for col in log_features:
        if col in result.columns:
            # Add 1 to handle zeros, then log transform
            result[f"{col}_log"] = np.log1p(result[col].fillna(0))

    logger.debug("   ✅ Log transformations (8 features)")

    # ===================================================================
    # 2. NORMALIZED FEATURES (2 features)
    # ===================================================================

    # Grid position normalized (0-1 scale, lower is better)
    if "grid_position" in result.columns:
        # Group by race to get max grid position per race
        max_grid = result.groupby(["year", "round_number"])["grid_position"].transform("max")
        result["grid_position_normalized"] = result["grid_position"] / max_grid.replace(0, 1)

    # Constructor points normalized by season
    if "constructor_points_so_far" in result.columns:
        # Normalize by year
        max_constructor_points = result.groupby("year")["constructor_points_so_far"].transform(
            "max"
        )
        result["constructor_points_normalized"] = result[
            "constructor_points_so_far"
        ] / max_constructor_points.replace(0, 1)

    logger.debug("   ✅ Normalized features (2 features)")

    # ===================================================================
    # 3. DIFFERENCE FEATURES (2 features)
    # ===================================================================

    # Grid vs Qualifying difference (penalties, etc.)
    if "grid_position" in result.columns and "qualifying_position" in result.columns:
        result["grid_qualifying_diff"] = result["grid_position"] - result["qualifying_position"]

    # Temperature difference (affects tire strategy)
    if "avg_track_temp" in result.columns and "avg_air_temp" in result.columns:
        result["temp_track_air_diff"] = result["avg_track_temp"] - result["avg_air_temp"]

    logger.debug("   ✅ Difference features (2 features)")

    # ===================================================================
    # 4. MOMENTUM FEATURES (1 feature)
    # ===================================================================

    # Momentum: recent form vs overall form
    if "avg_position_last_5" in result.columns and "avg_position_so_far" in result.columns:
        # Negative means improving (lower position = better)
        result["momentum_position"] = result["avg_position_last_5"] - result["avg_position_so_far"]

    logger.debug("   ✅ Momentum features (1 feature)")

    # ===================================================================
    # 5. CATEGORICAL ENCODINGS (4 features)
    # ===================================================================
    # Use deterministic MD5 hash for categorical encoding

    categorical_cols = ["circuit_name", "country", "event_name", "driver_code"]

    for col in categorical_cols:
        if col in result.columns:
            # Create deterministic hash encoding
            result[f"{col}_encoded"] = result[col].apply(
                lambda x: int(hashlib.md5(str(x).encode()).hexdigest()[:8], 16)
                if pd.notna(x)
                else 0
            )

    logger.debug("   ✅ Categorical encodings (4 features)")

    # ===================================================================
    # 6. INTERACTION FEATURES (5 features)
    # ===================================================================
    # Capture relationships between features

    # Grid position * qualifying gap (captures starting advantage + qualifying performance)
    if "grid_position" in result.columns and "qualifying_time_from_pole" in result.columns:
        result["grid_qualifying_interaction"] = result["grid_position"] * result[
            "qualifying_time_from_pole"
        ].fillna(0)

    # Historical success at circuit * grid position
    if "circuit_wins_history" in result.columns and "grid_position" in result.columns:
        result["historical_grid_interaction"] = (
            result["circuit_wins_history"].fillna(0) * result["grid_position"]
        )

    # Win rate * constructor strength
    if "win_rate" in result.columns and "constructor_points_so_far" in result.columns:
        result["win_rate_constructor_interaction"] = result["win_rate"].fillna(0) * result[
            "constructor_points_so_far"
        ].fillna(0)

    # Points momentum * recent form
    if "points_per_race" in result.columns and "avg_position_last_5" in result.columns:
        # Lower position is better, so invert
        result["points_recent_form_interaction"] = result["points_per_race"].fillna(0) / result[
            "avg_position_last_5"
        ].replace(0, 20)

    # Qualifying gap * grid position (captures quali performance + starting advantage)
    if "qualifying_time_from_pole" in result.columns and "grid_position" in result.columns:
        result["qualifying_gap_grid_interaction"] = (
            result["qualifying_time_from_pole"].fillna(0) * result["grid_position"]
        )

    logger.debug("   ✅ Interaction features (5 features)")

    # ===================================================================
    # 7. COMPOSITE FEATURES (6 features)
    # ===================================================================
    # Domain-specific metrics

    # Win/Podium ratio (how often wins vs podiums)
    if "wins_so_far" in result.columns and "podiums_so_far" in result.columns:
        result["win_podium_ratio"] = result["wins_so_far"] / result["podiums_so_far"].replace(
            0, np.nan
        )

    # Momentum score: combines recent form, points, and wins
    if all(col in result.columns for col in ["avg_position_last_5", "points_per_race", "win_rate"]):
        result["momentum_score"] = (
            (21 - result["avg_position_last_5"].fillna(20))  # Lower position = better
            + result["points_per_race"].fillna(0)
            + (result["win_rate"].fillna(0) * 10)  # Amplify win rate impact
        )

    # Position consistency (lower std = more consistent)
    if "avg_position_so_far" in result.columns and "avg_position_last_5" in result.columns:
        result["position_consistency"] = np.abs(
            result["avg_position_so_far"] - result["avg_position_last_5"]
        )

    # Performance index: combines multiple metrics
    if all(col in result.columns for col in ["win_rate", "podium_rate", "points_per_race"]):
        result["performance_index"] = (
            result["win_rate"].fillna(0) * 3
            + result["podium_rate"].fillna(0) * 2
            + result["points_per_race"].fillna(0)
        )

    # Grid advantage (lower is better)
    if "grid_position" in result.columns:
        result["grid_advantage"] = 21 - result["grid_position"]  # Invert so higher = better

    # Qualifying advantage (closer to pole = better)
    if "qualifying_time_from_pole" in result.columns:
        # Invert and normalize (lower gap = higher advantage)
        max_gap = result.groupby(["year", "round_number"])["qualifying_time_from_pole"].transform(
            "max"
        )
        result["qualifying_advantage"] = 1 - (
            result["qualifying_time_from_pole"].fillna(max_gap) / max_gap.replace(0, 1)
        )

    # Estimated experience (races + circuit history)
    if "races_so_far" in result.columns and "circuit_races_history" in result.columns:
        result["estimated_experience"] = (
            result["races_so_far"].fillna(0)
            + result["circuit_races_history"].fillna(0) * 2  # Circuit experience weighted more
        )

    logger.debug("   ✅ Composite features (6 features)")

    # ===================================================================
    # SUMMARY
    # ===================================================================

    feature_count = sum(
        [
            9,  # Log transformations (9 cols, but wins_so_far_log already counted)
            2,  # Normalized
            2,  # Difference
            1,  # Momentum
            4,  # Categorical
            5,  # Interaction
            6,  # Composite
        ]
    )

    logger.info(f"✅ Enhanced features added: ~{feature_count} new features")

    return result
