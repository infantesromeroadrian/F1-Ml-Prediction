"""Tests for enhanced feature engineering."""

import numpy as np
import pandas as pd
import pytest

from src.ml.features import add_enhanced_features, add_feature_columns


class TestEnhancedFeatures:
    """Test suite for add_enhanced_features()."""

    @pytest.fixture
    def base_dataframe(self):
        """Create a sample dataframe with base features."""
        return pd.DataFrame(
            {
                # Identifiers
                "year": [2023, 2023, 2023],
                "round_number": [1, 1, 1],
                "circuit_name": ["Monaco", "Monaco", "Monaco"],
                "country": ["Monaco", "Monaco", "Monaco"],
                "event_name": ["Monaco GP", "Monaco GP", "Monaco GP"],
                "driver_code": ["VER", "HAM", "LEC"],
                "constructor": ["Red Bull", "Mercedes", "Ferrari"],
                # Pre-race features
                "grid_position": [1, 2, 3],
                "qualifying_position": [1, 2, 3],
                "qualifying_best_time": [78.0, 78.2, 78.5],
                "qualifying_time_from_pole": [0.0, 0.2, 0.5],
                # Historical features
                "wins_so_far": [5, 3, 1],
                "points_so_far": [150, 100, 80],
                "podiums_so_far": [8, 6, 4],
                "races_so_far": [10, 10, 10],
                "avg_position_so_far": [2.0, 3.5, 5.0],
                "avg_position_last_5": [1.5, 3.0, 4.5],
                "points_per_race": [15.0, 10.0, 8.0],
                "win_rate": [0.5, 0.3, 0.1],
                "podium_rate": [0.8, 0.6, 0.4],
                # Constructor features
                "constructor_points_so_far": [300, 200, 150],
                "constructor_wins_so_far": [8, 5, 2],
                # Circuit features
                "circuit_wins_history": [2, 1, 0],
                "circuit_races_history": [5, 5, 5],
                "circuit_avg_position": [2.0, 3.0, 5.0],
                # Weather (optional)
                "avg_air_temp": [25.0, 25.0, 25.0],
                "avg_track_temp": [35.0, 35.0, 35.0],
            }
        )

    def test_add_enhanced_features_base(self, base_dataframe):
        """Test that enhanced features are added without errors."""
        result = add_enhanced_features(base_dataframe)

        # Should have more columns than input
        assert len(result.columns) > len(base_dataframe.columns)

        # Original data should be preserved
        assert all(col in result.columns for col in base_dataframe.columns)

    def test_log_transformations(self, base_dataframe):
        """Test log-transformed features."""
        result = add_enhanced_features(base_dataframe)

        # Check log features exist
        log_features = [
            "wins_so_far_log",
            "win_rate_log",
            "points_so_far_log",
            "podiums_so_far_log",
            "points_per_race_log",
            "podium_rate_log",
            "constructor_wins_so_far_log",
            "constructor_points_so_far_log",
            "circuit_wins_history_log",
        ]

        for feature in log_features:
            assert feature in result.columns, f"Missing {feature}"

        # Verify log transformation is correct
        assert result["wins_so_far_log"].iloc[0] == pytest.approx(np.log1p(5))
        assert result["points_so_far_log"].iloc[1] == pytest.approx(np.log1p(100))

    def test_normalized_features(self, base_dataframe):
        """Test normalized features (0-1 scale)."""
        result = add_enhanced_features(base_dataframe)

        # Grid position normalized
        assert "grid_position_normalized" in result.columns
        assert result["grid_position_normalized"].min() >= 0
        assert result["grid_position_normalized"].max() <= 1

        # Constructor points normalized
        assert "constructor_points_normalized" in result.columns
        assert result["constructor_points_normalized"].min() >= 0
        assert result["constructor_points_normalized"].max() <= 1

    def test_difference_features(self, base_dataframe):
        """Test difference features."""
        result = add_enhanced_features(base_dataframe)

        # Grid-qualifying diff (should be 0 for all in this test case)
        assert "grid_qualifying_diff" in result.columns
        assert all(result["grid_qualifying_diff"] == 0)

        # Temperature diff
        assert "temp_track_air_diff" in result.columns
        assert all(result["temp_track_air_diff"] == 10.0)  # 35 - 25

    def test_momentum_features(self, base_dataframe):
        """Test momentum features."""
        result = add_enhanced_features(base_dataframe)

        assert "momentum_position" in result.columns

        # VER: improving (1.5 - 2.0 = -0.5, negative = better)
        # HAM: improving (3.0 - 3.5 = -0.5)
        # LEC: improving (4.5 - 5.0 = -0.5)
        assert all(result["momentum_position"] == -0.5)

    def test_categorical_encodings(self, base_dataframe):
        """Test categorical variable encodings."""
        result = add_enhanced_features(base_dataframe)

        categorical_features = [
            "circuit_name_encoded",
            "country_encoded",
            "event_name_encoded",
            "driver_code_encoded",
        ]

        for feature in categorical_features:
            assert feature in result.columns, f"Missing {feature}"
            # Encodings should be integers
            assert result[feature].dtype in [np.int64, np.int32, int]

        # All drivers at same circuit should have same circuit encoding
        assert len(result["circuit_name_encoded"].unique()) == 1

        # Different drivers should have different encodings
        assert len(result["driver_code_encoded"].unique()) == 3

    def test_interaction_features(self, base_dataframe):
        """Test interaction features."""
        result = add_enhanced_features(base_dataframe)

        interaction_features = [
            "grid_qualifying_interaction",
            "historical_grid_interaction",
            "win_rate_constructor_interaction",
            "points_recent_form_interaction",
            "qualifying_gap_grid_interaction",
        ]

        for feature in interaction_features:
            assert feature in result.columns, f"Missing {feature}"

    def test_composite_features(self, base_dataframe):
        """Test composite domain features."""
        result = add_enhanced_features(base_dataframe)

        composite_features = [
            "win_podium_ratio",
            "momentum_score",
            "position_consistency",
            "performance_index",
            "grid_advantage",
            "qualifying_advantage",
            "estimated_experience",
        ]

        for feature in composite_features:
            assert feature in result.columns, f"Missing {feature}"

        # Grid advantage: 21 - grid_position
        assert result["grid_advantage"].iloc[0] == 20  # 21 - 1
        assert result["grid_advantage"].iloc[1] == 19  # 21 - 2
        assert result["grid_advantage"].iloc[2] == 18  # 21 - 3

    def test_add_feature_columns_with_enhanced(self, base_dataframe):
        """Test add_feature_columns with enhanced=True."""
        result = add_feature_columns(base_dataframe, enhanced=True)

        # Should have enhanced features
        assert "wins_so_far_log" in result.columns
        assert "momentum_score" in result.columns
        assert "grid_advantage" in result.columns

    def test_add_feature_columns_without_enhanced(self, base_dataframe):
        """Test add_feature_columns with enhanced=False."""
        result = add_feature_columns(base_dataframe, enhanced=False)

        # Should NOT have enhanced features
        assert "wins_so_far_log" not in result.columns
        assert "momentum_score" not in result.columns

        # But should have base derived features
        assert "points_per_race" in result.columns
        assert "win_rate" in result.columns

    def test_handles_missing_columns_gracefully(self):
        """Test that function handles missing columns without crashing."""
        minimal_df = pd.DataFrame(
            {
                "year": [2023],
                "round_number": [1],
                "grid_position": [1],
            }
        )

        # Should not crash
        result = add_enhanced_features(minimal_df)

        # Should still add some features that don't depend on missing cols
        assert "grid_advantage" in result.columns

    def test_deterministic_categorical_encoding(self, base_dataframe):
        """Test that categorical encoding is deterministic."""
        result1 = add_enhanced_features(base_dataframe.copy())
        result2 = add_enhanced_features(base_dataframe.copy())

        # Same input should produce same encodings
        pd.testing.assert_series_equal(
            result1["driver_code_encoded"], result2["driver_code_encoded"]
        )

        pd.testing.assert_series_equal(
            result1["circuit_name_encoded"], result2["circuit_name_encoded"]
        )

    def test_no_infinite_values(self, base_dataframe):
        """Test that no infinite values are created."""
        result = add_enhanced_features(base_dataframe)

        # Check numeric columns for inf values
        numeric_cols = result.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            assert not np.isinf(result[col]).any(), f"Infinite values in {col}"

    def test_feature_count(self, base_dataframe):
        """Test that expected number of features are added."""
        result = add_enhanced_features(base_dataframe)

        # Original had 28 columns
        # Should add approximately 29 new features
        # (9 log + 2 norm + 2 diff + 1 momentum + 4 categorical + 5 interaction + 6 composite)
        expected_min_features = len(base_dataframe.columns) + 25

        assert len(result.columns) >= expected_min_features, (
            f"Expected at least {expected_min_features} columns, got {len(result.columns)}"
        )
