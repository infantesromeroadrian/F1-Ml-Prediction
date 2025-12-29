"""Tests for ML data validation module."""

import pandas as pd
import pytest

from src.ml.validation import (
    FORBIDDEN_FEATURES_AT_PREDICTION,
    VALID_FEATURES_AT_PREDICTION,
    DataLeakageError,
    DataQualityError,
    validate_feature_ranges,
    validate_ml_data,
    validate_no_leakage,
    validate_required_features,
    validate_temporal_consistency,
)


class TestValidateNoLeakage:
    """Test data leakage detection."""

    def test_clean_features_pass(self):
        """Valid features should pass validation."""
        df = pd.DataFrame(
            {
                "grid_position": [1, 2, 3],
                "wins_so_far": [10, 5, 2],
                "driver_code": ["VER", "HAM", "LEC"],
            }
        )
        # Should not raise
        validate_no_leakage(df, strict=True)

    def test_forbidden_features_fail_strict(self):
        """Forbidden features should raise error in strict mode."""
        df = pd.DataFrame(
            {
                "grid_position": [1, 2, 3],
                "race_position": [1, 2, 3],  # ❌ FORBIDDEN - future info
            }
        )
        with pytest.raises(DataLeakageError) as exc_info:
            validate_no_leakage(df, strict=True)

        assert "race_position" in str(exc_info.value)
        assert "DATA LEAKAGE DETECTED" in str(exc_info.value)

    def test_multiple_forbidden_features(self):
        """Multiple forbidden features should all be reported."""
        df = pd.DataFrame(
            {
                "grid_position": [1, 2],
                "race_position": [1, 2],  # ❌ FORBIDDEN
                "points": [25, 18],  # ❌ FORBIDDEN
                "fastest_lap_time": [90.1, 90.5],  # ❌ FORBIDDEN
            }
        )
        with pytest.raises(DataLeakageError) as exc_info:
            validate_no_leakage(df, strict=True)

        error_msg = str(exc_info.value)
        assert "race_position" in error_msg
        assert "points" in error_msg
        assert "fastest_lap_time" in error_msg

    def test_forbidden_features_warn_non_strict(self, caplog):
        """In non-strict mode, should warn instead of raising."""
        df = pd.DataFrame(
            {
                "grid_position": [1, 2],
                "race_position": [1, 2],  # ❌ FORBIDDEN
            }
        )
        # Should not raise in non-strict mode
        validate_no_leakage(df, strict=False)

        # But should log warning
        assert "DATA LEAKAGE DETECTED" in caplog.text

    def test_all_valid_features_documented(self):
        """All features in VALID_FEATURES_AT_PREDICTION should pass."""
        # Create DataFrame with all valid features
        data = {feat: [1.0, 2.0, 3.0] for feat in VALID_FEATURES_AT_PREDICTION}
        df = pd.DataFrame(data)

        # Should not raise
        validate_no_leakage(df, strict=True)

    def test_mixed_valid_and_invalid(self):
        """Mixed features should fail even with valid ones present."""
        df = pd.DataFrame(
            {
                "grid_position": [1, 2],  # ✅ Valid
                "wins_so_far": [10, 5],  # ✅ Valid
                "race_position": [1, 2],  # ❌ Forbidden
            }
        )
        with pytest.raises(DataLeakageError):
            validate_no_leakage(df, strict=True)


class TestValidateTemporalConsistency:
    """Test temporal consistency validation."""

    def test_past_data_only_passes(self):
        """Data from the past should pass."""
        df = pd.DataFrame(
            {
                "year": [2023, 2023, 2024],
                "round_number": [1, 2, 1],
                "grid_position": [1, 2, 3],
            }
        )
        # Predicting 2024 Round 5 - all data is from past
        validate_temporal_consistency(df, current_year=2024, current_round=5)

    def test_future_year_fails(self):
        """Data from future years should fail."""
        df = pd.DataFrame(
            {
                "year": [2023, 2024, 2025],  # ❌ 2025 is in the future
                "round_number": [1, 1, 1],
                "grid_position": [1, 2, 3],
            }
        )
        with pytest.raises(DataQualityError) as exc_info:
            validate_temporal_consistency(df, current_year=2024, current_round=5)

        assert "TEMPORAL INCONSISTENCY DETECTED" in str(exc_info.value)
        assert "2025" in str(exc_info.value)

    def test_future_round_same_year_fails(self):
        """Data from future rounds in same year should fail."""
        df = pd.DataFrame(
            {
                "year": [2024, 2024, 2024],
                "round_number": [1, 2, 6],  # ❌ Round 6 is >= current round 5
                "grid_position": [1, 2, 3],
            }
        )
        with pytest.raises(DataQualityError):
            validate_temporal_consistency(df, current_year=2024, current_round=5)

    def test_current_round_excluded(self):
        """Current round itself should be excluded (not in training data)."""
        df = pd.DataFrame(
            {
                "year": [2024, 2024],
                "round_number": [5, 5],  # Current round
                "grid_position": [1, 2],
            }
        )
        # Current round IS the race we're predicting - should fail
        with pytest.raises(DataQualityError):
            validate_temporal_consistency(df, current_year=2024, current_round=5)

    def test_missing_columns_warns(self, caplog):
        """Missing year/round columns should warn but not fail."""
        df = pd.DataFrame({"grid_position": [1, 2, 3]})

        # Should not raise
        validate_temporal_consistency(df, current_year=2024, current_round=5)

        # Should warn
        assert "Cannot validate temporal consistency" in caplog.text


class TestValidateFeatureRanges:
    """Test feature range validation."""

    def test_valid_ranges_pass(self):
        """Features within valid ranges should pass."""
        df = pd.DataFrame(
            {
                "grid_position": [1, 10, 20],  # Valid: 1-20
                "qualifying_position": [1, 5, 15],  # Valid: 1-20
                "avg_air_temp": [20, 25, 30],  # Valid: -10 to 60
                "win_rate": [0.0, 0.5, 1.0],  # Valid: 0-1
            }
        )
        validate_feature_ranges(df)

    def test_grid_position_out_of_range(self):
        """Grid position outside 1-20 should fail."""
        df = pd.DataFrame({"grid_position": [0, 1, 21]})  # ❌ 0 and 21 invalid

        with pytest.raises(DataQualityError) as exc_info:
            validate_feature_ranges(df)

        assert "grid_position" in str(exc_info.value)
        assert "out of range [1, 20]" in str(exc_info.value)

    def test_temperature_out_of_range(self):
        """Unrealistic temperatures should fail."""
        df = pd.DataFrame({"avg_air_temp": [-20, 20, 70]})  # ❌ -20 and 70 invalid

        with pytest.raises(DataQualityError) as exc_info:
            validate_feature_ranges(df)

        assert "avg_air_temp" in str(exc_info.value)
        assert "out of range [-10, 60]" in str(exc_info.value)

    def test_win_rate_out_of_range(self):
        """Win rate outside 0-1 should fail."""
        df = pd.DataFrame({"win_rate": [-0.1, 0.5, 1.5]})  # ❌ -0.1 and 1.5 invalid

        with pytest.raises(DataQualityError) as exc_info:
            validate_feature_ranges(df)

        assert "win_rate" in str(exc_info.value)
        assert "out of range [0, 1]" in str(exc_info.value)

    def test_multiple_range_violations(self):
        """Multiple range violations should all be reported."""
        df = pd.DataFrame(
            {
                "grid_position": [0, 25],  # ❌ Both invalid
                "win_rate": [-0.5, 2.0],  # ❌ Both invalid
            }
        )

        with pytest.raises(DataQualityError) as exc_info:
            validate_feature_ranges(df)

        error_msg = str(exc_info.value)
        assert "grid_position" in error_msg
        assert "win_rate" in error_msg
        assert "2 problems" in error_msg.lower()

    def test_missing_columns_ignored(self):
        """Validation should skip columns that don't exist."""
        df = pd.DataFrame({"some_other_feature": [1, 2, 3]})

        # Should not raise (no validated columns present)
        validate_feature_ranges(df)


class TestValidateRequiredFeatures:
    """Test required features validation."""

    def test_all_required_present(self):
        """All required features present should pass."""
        df = pd.DataFrame(
            {
                "grid_position": [1, 2],
                "wins_so_far": [10, 5],
                "driver_code": ["VER", "HAM"],
            }
        )
        required = ["grid_position", "wins_so_far", "driver_code"]

        validate_required_features(df, required)

    def test_missing_required_fails(self):
        """Missing required features should fail."""
        df = pd.DataFrame(
            {
                "grid_position": [1, 2],
                "wins_so_far": [10, 5],
                # Missing driver_code
            }
        )
        required = ["grid_position", "wins_so_far", "driver_code"]

        with pytest.raises(DataQualityError) as exc_info:
            validate_required_features(df, required)

        assert "driver_code" in str(exc_info.value)
        assert "MISSING REQUIRED FEATURES" in str(exc_info.value)

    def test_multiple_missing_features(self):
        """Multiple missing features should all be reported."""
        df = pd.DataFrame({"grid_position": [1, 2]})
        required = ["grid_position", "wins_so_far", "driver_code", "constructor"]

        with pytest.raises(DataQualityError) as exc_info:
            validate_required_features(df, required)

        error_msg = str(exc_info.value)
        assert "wins_so_far" in error_msg
        assert "driver_code" in error_msg
        assert "constructor" in error_msg


class TestValidateMLDataIntegration:
    """Test main validation function that runs all checks."""

    def test_clean_data_passes_all_checks(self):
        """Clean data should pass all validation checks."""
        df = pd.DataFrame(
            {
                "year": [2023, 2023],
                "round_number": [1, 2],
                "grid_position": [1, 2],
                "wins_so_far": [10, 5],
                "driver_code": ["VER", "HAM"],
                "win_rate": [0.5, 0.3],
            }
        )

        # Should not raise
        validate_ml_data(
            df,
            current_year=2024,
            current_round=5,
            required_features=["grid_position", "wins_so_far"],
            strict=True,
        )

    def test_leakage_detected_in_integration(self):
        """Leakage should be caught by integration function."""
        df = pd.DataFrame(
            {
                "year": [2023, 2023],
                "round_number": [1, 2],
                "grid_position": [1, 2],
                "race_position": [1, 2],  # ❌ FORBIDDEN
            }
        )

        with pytest.raises(DataLeakageError):
            validate_ml_data(df, strict=True)

    def test_temporal_inconsistency_detected(self):
        """Temporal issues should be caught by integration function."""
        df = pd.DataFrame(
            {
                "year": [2024, 2024],
                "round_number": [6, 7],  # ❌ Future rounds
                "grid_position": [1, 2],
            }
        )

        with pytest.raises(DataQualityError):
            validate_ml_data(df, current_year=2024, current_round=5, strict=True)

    def test_range_violations_detected(self):
        """Range violations should be caught by integration function."""
        df = pd.DataFrame(
            {
                "year": [2023, 2023],
                "round_number": [1, 2],
                "grid_position": [0, 25],  # ❌ Out of range
            }
        )

        with pytest.raises(DataQualityError):
            validate_ml_data(df, current_year=2024, current_round=5, strict=True)

    def test_non_strict_mode_continues_on_errors(self, caplog):
        """Non-strict mode should warn but not raise."""
        df = pd.DataFrame(
            {
                "year": [2023, 2023],
                "round_number": [1, 2],
                "grid_position": [0, 25],  # ❌ Out of range
                "race_position": [1, 2],  # ❌ FORBIDDEN
            }
        )

        # Should not raise in non-strict mode
        validate_ml_data(df, current_year=2024, current_round=5, strict=False)

        # But should log warnings
        assert "DATA LEAKAGE DETECTED" in caplog.text or "DATA QUALITY" in caplog.text

    def test_without_temporal_validation(self):
        """Temporal validation should be skipped if year/round not provided."""
        df = pd.DataFrame(
            {
                "grid_position": [1, 2],
                "wins_so_far": [10, 5],
            }
        )

        # Should not raise even without temporal info
        validate_ml_data(df, strict=True)


class TestForbiddenFeaturesCompleteness:
    """Meta-tests to ensure our feature lists are comprehensive."""

    def test_no_overlap_between_valid_and_forbidden(self):
        """Valid and forbidden features should not overlap."""
        valid_set = set(VALID_FEATURES_AT_PREDICTION)
        forbidden_set = set(FORBIDDEN_FEATURES_AT_PREDICTION)

        overlap = valid_set & forbidden_set

        assert len(overlap) == 0, f"Features in both lists: {overlap}"

    def test_forbidden_features_are_result_related(self):
        """All forbidden features should be race result related."""
        result_keywords = [
            "position",
            "points",
            "dnf",
            "winner",
            "fastest",
            "race_time",
            "retired",
            "laps_completed",
            "podium",
            "finished",
            "classified",
        ]

        for feature in FORBIDDEN_FEATURES_AT_PREDICTION:
            # Each forbidden feature should contain at least one result keyword
            contains_keyword = any(keyword in feature.lower() for keyword in result_keywords)
            assert contains_keyword, f"Feature '{feature}' doesn't seem result-related"

    def test_valid_features_dont_contain_result_keywords(self):
        """Valid features should NOT contain race result keywords."""
        # These keywords indicate race RESULTS (forbidden)
        result_keywords = [
            "race_position",
            "final_position",
            "race_time",
            "fastest_lap_rank",
            "time_retired",
            "laps_completed",
        ]

        for feature in VALID_FEATURES_AT_PREDICTION:
            # Valid features should NOT contain these exact result keywords
            contains_result = any(keyword in feature.lower() for keyword in result_keywords)
            assert not contains_result, f"Feature '{feature}' contains race result keyword"
