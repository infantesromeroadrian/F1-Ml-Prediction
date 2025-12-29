"""Machine Learning prediction module for F1 race predictions."""

import hashlib
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastf1.core import Session
from src.ml.data_collection import (
    extract_circuit_info,
    extract_qualifying_results,
    extract_race_results,
    extract_weather_data,
)
from src.ml.features import (
    add_feature_columns,
    calculate_historical_stats,
)

logger = logging.getLogger(__name__)

# Default model paths (relative to project root)
# Try models/ first, then notebooks/models/ as fallback
DEFAULT_MODELS_DIR = Path("models")
DEFAULT_MODELS_DIR_FALLBACK = Path("notebooks/models")
DEFAULT_MODEL_INFO_FILE = "optimized_models_info_20251225_000229.json"
DEFAULT_FEATURE_NAMES_FILE = "enhanced_feature_names_20251225_000229.json"


class F1PredictionEngine:
    """Engine for making F1 race predictions using trained ML models."""

    def __init__(
        self,
        models_dir: Path | None = None,
        model_info_file: str | None = None,
        feature_names_file: str | None = None,
    ) -> None:
        """
        Initialize the prediction engine.

        Args:
            models_dir: Directory containing model files (default: models, fallback: notebooks/models)
            model_info_file: Name of model info JSON file
            feature_names_file: Name of feature names JSON file
        """
        # Try to find models directory (models/ first, then notebooks/models/)
        if models_dir is None:
            if DEFAULT_MODELS_DIR.exists():
                self.models_dir = DEFAULT_MODELS_DIR
            elif DEFAULT_MODELS_DIR_FALLBACK.exists():
                self.models_dir = DEFAULT_MODELS_DIR_FALLBACK
            else:
                self.models_dir = DEFAULT_MODELS_DIR  # Use default even if doesn't exist yet
        else:
            self.models_dir = Path(models_dir)
        self.model_info_file = model_info_file or DEFAULT_MODEL_INFO_FILE
        self.feature_names_file = feature_names_file or DEFAULT_FEATURE_NAMES_FILE

        # Model objects (loaded lazily)
        self.classifier_model: Any = None
        self.position_regressor: Any = None
        self.points_regressor: Any = None

        # Feature names and metadata
        self.feature_names: list[str] = []
        self.model_info: dict[str, Any] = {}

        # Historical data cache (for calculating historical stats)
        self.historical_data: pd.DataFrame | None = None

        # Encoders and transformers (if needed)
        self.label_encoders: dict[str, Any] = {}

        logger.info(f"ℹ️ F1PredictionEngine initialized with models_dir={self.models_dir}")

    def load_models(self) -> bool:
        """
        Load all ML models from disk.

        Returns:
            True if all models loaded successfully, False otherwise
        """
        try:
            model_info_path = self.models_dir / self.model_info_file

            if not model_info_path.exists():
                logger.warning(f"⚠️ Model info file not found: {model_info_path}")
                return False

            # Load model info
            with open(model_info_path) as f:
                self.model_info = json.load(f)

            logger.info(f"ℹ️ Loaded model info from {model_info_path}")

            # Load feature names
            feature_names_path = self.models_dir / self.feature_names_file
            if feature_names_path.exists():
                with open(feature_names_path) as f:
                    self.feature_names = json.load(f)
                logger.info(f"ℹ️ Loaded {len(self.feature_names)} feature names")
            else:
                logger.warning(f"⚠️ Feature names file not found: {feature_names_path}")
                return False

            # Helper function to resolve model path (handles paths with or without "models/" prefix)
            def resolve_model_path(path_str: str) -> Path:
                """Resolve model path, handling both absolute and relative paths."""
                path = Path(path_str)
                # If path starts with "models/", extract just the filename
                if path.parts[0] == "models" and len(path.parts) > 1:
                    filename = path.name
                # If it's just a filename, use it directly
                elif len(path.parts) == 1:
                    filename = path
                else:
                    filename = path.name

                # Try in current models_dir first
                candidate = self.models_dir / filename
                if candidate.exists():
                    return candidate

                # Try in fallback directory
                if self.models_dir != DEFAULT_MODELS_DIR_FALLBACK:
                    fallback_candidate = DEFAULT_MODELS_DIR_FALLBACK / filename
                    if fallback_candidate.exists():
                        return fallback_candidate

                # Return the candidate even if it doesn't exist (will be handled by caller)
                return candidate

            # Load classification model
            classifier_path = resolve_model_path(self.model_info["classification"]["path"])
            if classifier_path.exists():
                with open(classifier_path, "rb") as f:
                    self.classifier_model = pickle.load(f)
                logger.info(f"✅ Loaded classifier: {classifier_path}")
            else:
                logger.error(f"❌ Classifier not found: {classifier_path}")
                return False

            # Load position regressor
            position_path = resolve_model_path(self.model_info["regression_position"]["path"])
            if position_path.exists():
                with open(position_path, "rb") as f:
                    self.position_regressor = pickle.load(f)
                logger.info(f"✅ Loaded position regressor: {position_path}")
            else:
                logger.warning(f"⚠️ Position regressor not found: {position_path}")

            # Load points regressor
            points_path = resolve_model_path(self.model_info["regression_points"]["path"])
            if points_path.exists():
                with open(points_path, "rb") as f:
                    self.points_regressor = pickle.load(f)
                logger.info(f"✅ Loaded points regressor: {points_path}")
            else:
                logger.warning(f"⚠️ Points regressor not found: {points_path}")

            return True

        except Exception as e:
            logger.error(f"❌ Error loading models: {e}")
            return False

    def load_historical_data(self, historical_data_path: str | None = None) -> bool:
        """
        Load historical race data for calculating historical features.

        Args:
            historical_data_path: Path to historical_races.csv (default: data/processed/historical_races.csv)

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if historical_data_path is None:
                historical_data_path = "data/processed/historical_races.csv"

            if not os.path.exists(historical_data_path):
                logger.warning(f"⚠️ Historical data not found: {historical_data_path}")
                logger.warning("⚠️ Historical features will be unavailable")
                return False

            self.historical_data = pd.read_csv(historical_data_path)
            logger.info(f"ℹ️ Loaded historical data: {len(self.historical_data)} races")
            return True

        except Exception as e:
            logger.error(f"❌ Error loading historical data: {e}")
            return False

    def prepare_features_from_session(
        self,
        race_session: Session,
        qualifying_session: Session | None = None,
    ) -> pd.DataFrame:
        """
        Prepare features for prediction from F1 session data.

        This function extracts pre-race data (qualifying, weather, etc.) and
        calculates historical statistics to create features for ML prediction.

        Args:
            race_session: FastF1 race session object
            qualifying_session: Optional qualifying session (if not provided, will try to load)

        Returns:
            DataFrame with features for each driver (one row per driver)
        """
        logger.info(f"ℹ️ Preparing features for {race_session.event['EventName']}")

        try:
            year = race_session.event["EventDate"].year
            round_number = race_session.event["RoundNumber"]

            # Extract race results (for driver list and basic info)
            race_results = extract_race_results(race_session)

            # Extract qualifying results
            if qualifying_session is None:
                try:
                    from fastf1 import get_session

                    qualifying_session = get_session(year, round_number, "Q")
                    qualifying_session.load()
                except Exception as e:
                    logger.warning(f"⚠️ Could not load qualifying session: {e}")
                    qualifying_session = None

            qualifying_results = None
            if qualifying_session is not None:
                qualifying_results = extract_qualifying_results(qualifying_session)

            # Extract weather data
            weather_data = extract_weather_data(race_session)

            # Extract circuit info
            circuit_info = extract_circuit_info(race_session)

            # Merge all data
            driver_data = race_results.copy()

            if qualifying_results is not None:
                driver_data = driver_data.merge(
                    qualifying_results, on="driver_code", how="left", suffixes=("", "_quali")
                )

            # Add weather and circuit info (same for all drivers)
            if weather_data is not None:
                for key, value in weather_data.items():
                    driver_data[key] = value

            if circuit_info is not None:
                for key, value in circuit_info.items():
                    driver_data[key] = value

            # Add year and round
            driver_data["year"] = year
            driver_data["round_number"] = round_number

            # Convert driver_number to numeric if it exists (FastF1 returns it as string)
            if "driver_number" in driver_data.columns:
                driver_data["driver_number"] = (
                    pd.to_numeric(driver_data["driver_number"], errors="coerce")
                    .fillna(0)
                    .astype(int)
                )

            # Calculate historical statistics if historical data is available
            if self.historical_data is not None:
                # Combine historical data with current race data
                all_data = pd.concat([self.historical_data, driver_data], ignore_index=True)
                all_data = all_data.sort_values(["year", "round_number"])

                # Calculate historical stats
                driver_data = calculate_historical_stats(
                    all_data, current_year=year, current_round=round_number
                )

                # Filter back to current race
                driver_data = driver_data[
                    (driver_data["year"] == year) & (driver_data["round_number"] == round_number)
                ]

            # Add feature columns
            driver_data = add_feature_columns(driver_data)

            logger.info(f"ℹ️ Prepared features for {len(driver_data)} drivers")
            return driver_data

        except Exception as e:
            logger.error(f"❌ Error preparing features: {e}")
            raise

    def _apply_transformations(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply log transformations to skewed features.

        Args:
            df: DataFrame with features

        Returns:
            DataFrame with transformed features
        """
        result = df.copy()

        # Features to apply log1p transformation
        log_features = [
            "wins_so_far",
            "win_rate",
            "points_so_far",
            "podiums_so_far",
            "constructor_points_so_far",
            "constructor_wins_so_far",
            "circuit_wins_history",
            "points_per_race",
            "podium_rate",
        ]

        for feat in log_features:
            if feat in result.columns:
                original_name = feat
                new_name = f"{feat}_log"
                # Apply log1p (log(1+x)) to handle zeros
                result[new_name] = np.log1p(result[original_name].fillna(0))

        return result

    def _create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create derived features (differences, normalized, etc.).

        Args:
            df: DataFrame with features

        Returns:
            DataFrame with derived features
        """
        result = df.copy()

        # Grid-qualifying difference
        if "grid_position" in result.columns and "qualifying_position" in result.columns:
            result["grid_qualifying_diff"] = (
                result["grid_position"] - result["qualifying_position"]
            ).fillna(0)

        # Grid position normalized
        if "grid_position" in result.columns:
            mean_grid = result["grid_position"].mean()
            if pd.notna(mean_grid) and mean_grid > 0:
                result["grid_position_normalized"] = (result["grid_position"] / mean_grid).fillna(
                    1.0
                )
            else:
                result["grid_position_normalized"] = 1.0

        # Momentum position
        if "avg_position_so_far" in result.columns and "avg_position_last_5" in result.columns:
            result["momentum_position"] = (
                result["avg_position_so_far"] - result["avg_position_last_5"]
            ).fillna(0)

        # Constructor points normalized
        if "constructor_points_so_far" in result.columns:
            max_constructor_points = result["constructor_points_so_far"].max()
            if pd.notna(max_constructor_points) and max_constructor_points > 0:
                result["constructor_points_normalized"] = (
                    result["constructor_points_so_far"] / max_constructor_points
                ).fillna(0)
            else:
                result["constructor_points_normalized"] = 0.0

        # Temperature difference (track - air)
        if "avg_track_temp" in result.columns and "avg_air_temp" in result.columns:
            result["temp_track_air_diff"] = (
                result["avg_track_temp"] - result["avg_air_temp"]
            ).fillna(0)

        # Experience level
        if "races_so_far" in result.columns:
            result["experience_level"] = pd.cut(
                result["races_so_far"].fillna(0),
                bins=[0, 10, 50, float("inf")],
                labels=["Rookie", "Experienced", "Veteran"],
            ).astype(str)
            result["experience_level"] = result["experience_level"].fillna("Rookie")

        # Rain category
        if "max_rainfall" in result.columns:
            result["rain_category"] = pd.cut(
                result["max_rainfall"].fillna(0),
                bins=[0, 0.1, 1.0, float("inf")],
                labels=["Dry", "Light", "Heavy"],
            ).astype(str)
            result["rain_category"] = result["rain_category"].fillna("Dry")

        # Qualifying gap category
        if "qualifying_time_from_pole" in result.columns:
            result["qualifying_gap_category"] = pd.cut(
                result["qualifying_time_from_pole"].fillna(10.0),
                bins=[0, 0.5, 2.0, float("inf")],
                labels=["Close", "Medium", "Far"],
            ).astype(str)
            result["qualifying_gap_category"] = result["qualifying_gap_category"].fillna("Far")

        return result

    def _create_advanced_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create advanced interaction and temporal features.

        Args:
            df: DataFrame with features

        Returns:
            DataFrame with advanced features
        """
        result = df.copy()

        # Interaction features
        if "grid_position" in result.columns and "qualifying_position" in result.columns:
            result["grid_qualifying_interaction"] = (
                result["grid_position"] * result["qualifying_position"]
            ).fillna(0)

        if "grid_position" in result.columns and "avg_position_so_far" in result.columns:
            result["historical_grid_interaction"] = (
                result["grid_position"] * result["avg_position_so_far"]
            ).fillna(0)

        if "win_rate" in result.columns and "constructor_wins_so_far" in result.columns:
            result["win_rate_constructor_interaction"] = result["win_rate"].fillna(0) * result[
                "constructor_wins_so_far"
            ].fillna(0)

        if "points_per_race" in result.columns and "avg_position_last_5" in result.columns:
            result["points_recent_form_interaction"] = result["points_per_race"].fillna(0) * (
                21 - result["avg_position_last_5"].fillna(10.5)
            )

        if "qualifying_time_from_pole" in result.columns and "grid_position" in result.columns:
            result["qualifying_gap_grid_interaction"] = (
                result["qualifying_time_from_pole"].fillna(10.0) * result["grid_position"]
            ).fillna(0)

        # Win/podium ratio
        if "wins_so_far" in result.columns and "podiums_so_far" in result.columns:
            result["win_podium_ratio"] = (
                result["wins_so_far"].fillna(0) / (result["podiums_so_far"].fillna(0) + 1)
            ).fillna(0)

        # Momentum score
        if "points_per_race" in result.columns and "avg_position_last_5" in result.columns:
            result["momentum_score"] = result["points_per_race"].fillna(0) * (
                21 - result["avg_position_last_5"].fillna(10.5)
            )

        # Position consistency
        if "avg_position_so_far" in result.columns:
            # Lower std = more consistent (we'll use inverse)
            result["position_consistency"] = 1.0 / (result["avg_position_so_far"].fillna(10.5) + 1)

        # Performance index
        if all(col in result.columns for col in ["win_rate", "podium_rate", "points_per_race"]):
            result["performance_index"] = (
                result["win_rate"].fillna(0) * 0.4
                + result["podium_rate"].fillna(0) * 0.3
                + (result["points_per_race"].fillna(0) / 25.0) * 0.3
            )
        else:
            result["performance_index"] = 0.0

        # Grid advantage
        if "grid_position" in result.columns:
            result["grid_advantage"] = (21 - result["grid_position"]) / 20.0

        # Qualifying advantage
        if "qualifying_position" in result.columns:
            result["qualifying_advantage"] = (21 - result["qualifying_position"]) / 20.0

        # Estimated experience
        if "races_so_far" in result.columns:
            result["estimated_experience"] = np.log1p(result["races_so_far"].fillna(0))

        return result

    def _encode_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Encode categorical features using Label Encoding.

        Args:
            df: DataFrame with features

        Returns:
            DataFrame with encoded features
        """
        result = df.copy()

        # High-cardinality features: Label Encoding
        high_cardinality = ["circuit_name", "country", "event_name", "driver_code"]

        for col in high_cardinality:
            if col in result.columns:
                encoded_col = f"{col}_encoded"
                # Use deterministic hash (MD5) for reproducible encoding across sessions
                # Python's built-in hash() is NOT deterministic between runs
                result[encoded_col] = (
                    result[col]
                    .astype(str)
                    .apply(lambda x: int(hashlib.md5(x.encode()).hexdigest(), 16) % 1000)
                )

        # Low-cardinality features: One-Hot Encoding (we'll create binary columns)
        low_cardinality = [
            "constructor",
            "status",
            "experience_level",
            "rain_category",
            "qualifying_gap_category",
        ]

        for col in low_cardinality:
            if col in result.columns:
                # Create binary columns for each unique value
                unique_vals = result[col].astype(str).unique()
                for val in unique_vals:
                    encoded_col = f"{col}_{val}"
                    result[encoded_col] = (result[col].astype(str) == val).astype(int)

        return result

    def _prepare_final_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare final feature set matching the model's expected features.

        Args:
            df: DataFrame with all features

        Returns:
            DataFrame with features in the correct order and format
        """
        result = df.copy()

        # Apply transformations
        result = self._apply_transformations(result)

        # Create derived features
        result = self._create_derived_features(result)

        # Create advanced features
        result = self._create_advanced_features(result)

        # Encode categorical features
        result = self._encode_categorical_features(result)

        # Select only features that the model expects
        if self.feature_names:
            # Find columns that match feature names (exact or with suffix)
            available_features = []
            for feat_name in self.feature_names:
                if feat_name in result.columns:
                    available_features.append(feat_name)
                else:
                    # Try to find a matching column
                    matching = [
                        col
                        for col in result.columns
                        if col.startswith(feat_name) or feat_name in col
                    ]
                    if matching:
                        available_features.append(matching[0])
                    else:
                        # Feature not found, will be filled with 0
                        logger.warning(f"⚠️ Feature '{feat_name}' not found in data")
                        result[feat_name] = 0
                        available_features.append(feat_name)

            # Reorder and select features
            result = result[[col for col in available_features if col in result.columns]]

            # Add missing features with default values
            for feat_name in self.feature_names:
                if feat_name not in result.columns:
                    result[feat_name] = 0
                    logger.warning(f"⚠️ Missing feature '{feat_name}' filled with 0")

            # Ensure correct order
            result = result[self.feature_names]

        # Fill any remaining NaN values
        result = result.fillna(0)

        # Convert all columns to numeric (handle any remaining object/categorical columns)
        for col in result.columns:
            if result[col].dtype == "object" or pd.api.types.is_categorical_dtype(result[col]):
                # Try to convert to numeric
                try:
                    result[col] = pd.to_numeric(result[col], errors="coerce")
                except Exception:
                    # If conversion fails, use hash-based encoding
                    result[col] = result[col].astype(str).apply(lambda x: hash(x) % 1000)
                # Fill any NaN created by conversion
                result[col] = result[col].fillna(0)
            elif pd.api.types.is_datetime64_any_dtype(result[col]):
                # Convert datetime to numeric (timestamp)
                result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0)

        # Ensure all columns are numeric types
        result = result.astype(float, errors="ignore")

        return result

    def predict(
        self,
        race_session: Session,
        qualifying_session: Session | None = None,
    ) -> pd.DataFrame:
        """
        Make predictions for all drivers in a race.

        Args:
            race_session: FastF1 race session object
            qualifying_session: Optional qualifying session

        Returns:
            DataFrame with predictions (driver_code, winner_prob, predicted_position, predicted_points)
        """
        if self.classifier_model is None:
            logger.error("❌ Models not loaded. Call load_models() first.")
            raise ValueError("Models not loaded")

        logger.info(f"ℹ️ Making predictions for {race_session.event['EventName']}")

        # Prepare features
        driver_features = self.prepare_features_from_session(race_session, qualifying_session)

        # Prepare final feature set
        X = self._prepare_final_features(driver_features)

        # Make predictions
        predictions = driver_features[["driver_code", "driver_number", "constructor"]].copy()

        # Classification: Winner probability
        if self.classifier_model is not None:
            winner_proba = self.classifier_model.predict_proba(X)[:, 1]
            predictions["winner_probability"] = winner_proba
            predictions["predicted_winner"] = (winner_proba > 0.5).astype(int)
            logger.info("ℹ️ Winner predictions made")

        # Regression: Position
        if self.position_regressor is not None:
            predicted_positions = self.position_regressor.predict(X)
            # Clip to valid range [1, 20]
            predicted_positions = np.clip(predicted_positions, 1, 20)
            predictions["predicted_position"] = predicted_positions.round().astype(int)
            logger.info("ℹ️ Position predictions made")

        # Regression: Points
        if self.points_regressor is not None:
            predicted_points = self.points_regressor.predict(X)
            # Clip to valid range [0, 26] (max points in F1)
            predicted_points = np.clip(predicted_points, 0, 26)
            predictions["predicted_points"] = predicted_points.round(1)
            logger.info("ℹ️ Points predictions made")

        # Sort by predicted position
        if "predicted_position" in predictions.columns:
            predictions = predictions.sort_values("predicted_position")

        logger.info(f"✅ Predictions completed for {len(predictions)} drivers")
        return predictions


def create_prediction_engine(
    models_dir: str | None = None,
    load_historical: bool = True,
) -> F1PredictionEngine | None:
    """
    Factory function to create and initialize a prediction engine.

    Args:
        models_dir: Optional path to models directory
        load_historical: Whether to load historical data

    Returns:
        Initialized F1PredictionEngine or None if initialization failed
    """
    try:
        engine = F1PredictionEngine(models_dir=Path(models_dir) if models_dir else None)

        # Load models
        if not engine.load_models():
            logger.error("❌ Failed to load models")
            return None

        # Load historical data
        if load_historical:
            engine.load_historical_data()

        logger.info("✅ Prediction engine initialized successfully")
        return engine

    except Exception as e:
        logger.error(f"❌ Error creating prediction engine: {e}")
        return None
