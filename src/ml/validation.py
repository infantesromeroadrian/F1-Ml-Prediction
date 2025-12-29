"""Data validation module for ML pipeline - prevents data leakage and ensures data quality."""

import logging
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# FEATURES PROHIBIDAS EN PREDICTION TIME
# ═══════════════════════════════════════════════════════════════

# Estas features contienen información del futuro (resultado de la carrera)
# NUNCA deben estar presentes en X_train o X_test
FORBIDDEN_FEATURES_AT_PREDICTION = [
    # Race results (información del futuro)
    "race_position",
    "final_position",
    "position",
    "points",
    "dnf",
    "winner",
    "fastest_lap_time",
    "fastest_lap_rank",
    "race_time",
    "time_retired",
    "laps_completed",
    # Features que derivan del resultado
    "podium",
    "points_scored",
    "finished",
    "classified",
]

# Features que SÍ son válidas (disponibles antes de la carrera)
VALID_FEATURES_AT_PREDICTION = [
    # Driver info (conocido antes de la carrera)
    "driver_code",
    "driver_number",
    "constructor",
    # Qualifying/Grid (disponible antes de race start)
    "grid_position",
    "qualifying_position",
    "q1_time",
    "q2_time",
    "q3_time",
    "qualifying_best_time",
    "qualifying_time_from_pole",
    # Historical stats (calculado del pasado)
    "wins_so_far",
    "points_so_far",
    "podiums_so_far",
    "races_so_far",
    "avg_position_so_far",
    "avg_position_last_5",
    "points_per_race",
    "win_rate",
    "podium_rate",
    # Constructor stats (del pasado)
    "constructor_points_so_far",
    "constructor_wins_so_far",
    # Circuit history (del pasado)
    "circuit_wins_history",
    "circuit_races_history",
    "circuit_avg_position",
    # Weather (disponible antes/durante carrera)
    "avg_air_temp",
    "avg_track_temp",
    "avg_humidity",
    "avg_wind_speed",
    "max_rainfall",
    # Derived features (válidas si derivan de features válidas)
    "wins_so_far_log",
    "win_rate_log",
    "points_so_far_log",
    "podiums_so_far_log",
    "points_per_race_log",
    "podium_rate_log",
    "constructor_wins_so_far_log",
    "constructor_points_so_far_log",
    "circuit_wins_history_log",
    "grid_qualifying_diff",
    "grid_position_normalized",
    "momentum_position",
    "constructor_points_normalized",
    "temp_track_air_diff",
    # Encoded features
    "circuit_name_encoded",
    "country_encoded",
    "event_name_encoded",
    "driver_code_encoded",
    # Interaction features
    "grid_qualifying_interaction",
    "historical_grid_interaction",
    "win_rate_constructor_interaction",
    "points_recent_form_interaction",
    "qualifying_gap_grid_interaction",
    # Advanced features
    "win_podium_ratio",
    "momentum_score",
    "position_consistency",
    "performance_index",
    "grid_advantage",
    "qualifying_advantage",
    "estimated_experience",
]


class DataLeakageError(Exception):
    """Raised when data leakage is detected in features."""

    pass


class DataQualityError(Exception):
    """Raised when data quality issues are detected."""

    pass


# ═══════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def validate_no_leakage(df: pd.DataFrame, strict: bool = True) -> None:
    """
    Validate that DataFrame does not contain features from the future.

    This is CRITICAL for ML models. Using future information (like race results)
    in training will create models that perform perfectly on historical data
    but fail completely in production.

    Args:
        df: DataFrame to validate
        strict: If True, raise exception. If False, only warn.

    Raises:
        DataLeakageError: If forbidden features are found and strict=True

    Example:
        >>> features = pd.DataFrame({'grid_position': [1, 2], 'race_position': [1, 2]})
        >>> validate_no_leakage(features)  # Raises DataLeakageError
    """
    leaked_features = set(df.columns) & set(FORBIDDEN_FEATURES_AT_PREDICTION)

    if leaked_features:
        error_msg = (
            f"🚨 DATA LEAKAGE DETECTED! 🚨\n"
            f"Found {len(leaked_features)} forbidden features: {leaked_features}\n\n"
            f"These features contain information from the FUTURE (race results).\n"
            f"Models trained with these features will:\n"
            f"  ✅ Perform perfectly on historical data\n"
            f"  ❌ FAIL COMPLETELY in production\n\n"
            f"Remove these features before training:\n"
        )
        for feat in leaked_features:
            error_msg += f"  - {feat}\n"

        if strict:
            logger.error(error_msg)
            raise DataLeakageError(error_msg)
        else:
            logger.warning(error_msg)


def validate_temporal_consistency(df: pd.DataFrame, current_year: int, current_round: int) -> None:
    """
    Validate that historical features only use data from the past.

    Ensures that features calculated with historical stats (like wins_so_far)
    only include data from BEFORE the current race.

    Args:
        df: DataFrame with year and round_number columns
        current_year: Year of the race we're predicting
        current_round: Round of the race we're predicting

    Raises:
        DataQualityError: If temporal inconsistencies are detected

    Example:
        >>> # Training data for 2024 Round 10
        >>> validate_temporal_consistency(train_df, 2024, 10)
        >>> # Will fail if train_df contains data from Round 11+
    """
    if "year" not in df.columns or "round_number" not in df.columns:
        logger.warning("Cannot validate temporal consistency: 'year' or 'round_number' missing")
        return

    # Check for future data
    future_data = df[
        (df["year"] > current_year)
        | ((df["year"] == current_year) & (df["round_number"] >= current_round))
    ]

    if len(future_data) > 0:
        error_msg = (
            f"🚨 TEMPORAL INCONSISTENCY DETECTED! 🚨\n"
            f"Found {len(future_data)} rows from the FUTURE:\n"
            f"  Current: {current_year} Round {current_round}\n"
            f"  Future data years: {sorted(future_data['year'].unique())}\n"
            f"  Future data rounds: {sorted(future_data['round_number'].unique())}\n\n"
            f"This will cause data leakage in historical stats calculations.\n"
        )
        logger.error(error_msg)
        raise DataQualityError(error_msg)

    logger.info(
        f"✅ Temporal consistency validated: all data is from BEFORE "
        f"{current_year} Round {current_round}"
    )


def validate_feature_ranges(df: pd.DataFrame) -> None:
    """
    Validate that features are within expected ranges.

    Catches data corruption, outliers, and impossible values.

    Args:
        df: DataFrame to validate

    Raises:
        DataQualityError: If values are out of range

    Example:
        >>> df = pd.DataFrame({'grid_position': [1, 2, 99]})  # 99 is invalid
        >>> validate_feature_ranges(df)  # Raises DataQualityError
    """
    issues = []

    # Grid/qualifying position should be 1-20
    for col in ["grid_position", "qualifying_position"]:
        if col in df.columns:
            invalid = df[(df[col] < 1) | (df[col] > 20)]
            if len(invalid) > 0:
                issues.append(
                    f"{col}: {len(invalid)} values out of range [1, 20]. "
                    f"Min: {df[col].min()}, Max: {df[col].max()}"
                )

    # Points should be 0-26 (25 + 1 fastest lap)
    if "points" in df.columns:
        invalid = df[(df["points"] < 0) | (df["points"] > 26)]
        if len(invalid) > 0:
            issues.append(
                f"points: {len(invalid)} values out of range [0, 26]. "
                f"Min: {df['points'].min()}, Max: {df['points'].max()}"
            )

    # Temperature should be reasonable (-10°C to 60°C)
    for col in ["avg_air_temp", "avg_track_temp"]:
        if col in df.columns:
            invalid = df[(df[col] < -10) | (df[col] > 60)]
            if len(invalid) > 0:
                issues.append(
                    f"{col}: {len(invalid)} values out of range [-10, 60]°C. "
                    f"Min: {df[col].min()}, Max: {df[col].max()}"
                )

    # Win rate should be 0-1
    if "win_rate" in df.columns:
        invalid = df[(df["win_rate"] < 0) | (df["win_rate"] > 1)]
        if len(invalid) > 0:
            issues.append(
                f"win_rate: {len(invalid)} values out of range [0, 1]. "
                f"Min: {df['win_rate'].min()}, Max: {df['win_rate'].max()}"
            )

    if issues:
        error_msg = f"🚨 DATA QUALITY ISSUES DETECTED! 🚨\nFound {len(issues)} problems:\n"
        for issue in issues:
            error_msg += f"  - {issue}\n"
        logger.error(error_msg)
        raise DataQualityError(error_msg)

    logger.info("✅ Feature ranges validated: all values within expected ranges")


def validate_required_features(df: pd.DataFrame, required_features: list[str]) -> None:
    """
    Validate that all required features are present.

    Args:
        df: DataFrame to validate
        required_features: List of feature names that must be present

    Raises:
        DataQualityError: If required features are missing
    """
    missing_features = set(required_features) - set(df.columns)

    if missing_features:
        error_msg = (
            f"🚨 MISSING REQUIRED FEATURES! 🚨\n"
            f"The following {len(missing_features)} features are required but missing:\n"
        )
        for feat in missing_features:
            error_msg += f"  - {feat}\n"
        logger.error(error_msg)
        raise DataQualityError(error_msg)

    logger.info(f"✅ Required features validated: all {len(required_features)} features present")


# ═══════════════════════════════════════════════════════════════
# PYDANTIC MODELS FOR DATA VALIDATION
# ═══════════════════════════════════════════════════════════════


class RaceResult(BaseModel):
    """Validated race result data."""

    driver_code: str = Field(min_length=3, max_length=3)
    driver_number: int = Field(ge=1, le=99)
    constructor: str = Field(min_length=1)
    race_position: int | None = Field(ge=1, le=20, default=None)
    points: float = Field(ge=0, le=26)
    dnf: bool = False
    winner: int = Field(ge=0, le=1)

    @field_validator("points")
    @classmethod
    def validate_winner_points(cls, v: float, info: Any) -> float:
        """Winner must have at least 25 points (unless DNF)."""
        data = info.data
        if "race_position" in data and data["race_position"] == 1:
            if v < 25 and not data.get("dnf", False):
                raise ValueError(f"Winner must have at least 25 points, got {v}")
        return v

    @field_validator("winner")
    @classmethod
    def validate_winner_position(cls, v: int, info: Any) -> int:
        """Winner flag must match position 1."""
        data = info.data
        if "race_position" in data:
            if v == 1 and data["race_position"] != 1:
                raise ValueError(f"Winner flag is 1 but position is {data['race_position']}")
            if v == 0 and data["race_position"] == 1:
                raise ValueError("Winner flag is 0 but position is 1")
        return v


class QualifyingResult(BaseModel):
    """Validated qualifying result data."""

    driver_code: str = Field(min_length=3, max_length=3)
    qualifying_position: int = Field(ge=1, le=20)
    q1_time: float | None = Field(ge=0, default=None)
    q2_time: float | None = Field(ge=0, default=None)
    q3_time: float | None = Field(ge=0, default=None)

    @field_validator("q3_time")
    @classmethod
    def validate_q3_for_top_10(cls, v: float | None, info: Any) -> float | None:
        """Top 10 drivers should have Q3 time."""
        data = info.data
        if "qualifying_position" in data and data["qualifying_position"] <= 10:
            if v is None:
                # Warning, not error (puede haber condiciones especiales)
                logger.warning(f"Driver at P{data['qualifying_position']} missing Q3 time")
        return v


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════


def validate_ml_data(
    df: pd.DataFrame,
    current_year: int | None = None,
    current_round: int | None = None,
    required_features: list[str] | None = None,
    strict: bool = True,
) -> None:
    """
    Run all validation checks on ML data.

    This is the main entry point for data validation. Call this BEFORE training.

    Args:
        df: DataFrame to validate
        current_year: Year of race being predicted (for temporal check)
        current_round: Round of race being predicted (for temporal check)
        required_features: List of features that must be present
        strict: If True, raise exceptions. If False, only warn.

    Raises:
        DataLeakageError: If data leakage detected
        DataQualityError: If data quality issues detected

    Example:
        >>> # Before training
        >>> validate_ml_data(
        ...     X_train,
        ...     current_year=2024,
        ...     current_round=10,
        ...     required_features=['grid_position', 'wins_so_far'],
        ...     strict=True
        ... )
        >>> # Now safe to train
        >>> model.fit(X_train, y_train)
    """
    logger.info(f"🔍 Starting ML data validation ({len(df)} rows, {len(df.columns)} features)")

    # 1. Check for data leakage (CRITICAL)
    validate_no_leakage(df, strict=strict)

    # 2. Check temporal consistency (if applicable)
    if current_year is not None and current_round is not None:
        validate_temporal_consistency(df, current_year, current_round)

    # 3. Check feature ranges
    try:
        validate_feature_ranges(df)
    except DataQualityError as e:
        if strict:
            raise
        else:
            logger.warning(f"Data quality warning: {e}")

    # 4. Check required features (if specified)
    if required_features:
        validate_required_features(df, required_features)

    logger.info("✅ All validation checks passed!")
