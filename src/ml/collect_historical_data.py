"""Main script to collect historical F1 race data for ML model."""

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.f1_data.loaders import enable_cache
from src.logging_config import setup_logging
from src.ml.data_collection import (
    collect_race_data,
    get_season_schedule,
)
from src.ml.features import (
    add_feature_columns,
    calculate_historical_stats,
    prepare_ml_dataset,
)

logger = logging.getLogger(__name__)


def collect_season_data(
    year: int,
    start_round: int = 1,
    end_round: int | None = None,
    output_dir: str = "data/processed",
) -> pd.DataFrame:
    """
    Collect data for an entire season.

    Args:
        year: F1 season year
        start_round: First round to collect (default: 1)
        end_round: Last round to collect (None = all rounds)
        output_dir: Directory to save intermediate results

    Returns:
        DataFrame with all race data for the season
    """
    logger.info(f"ℹ️ Collecting data for season {year}")

    # Get schedule
    try:
        schedule = get_season_schedule(year)
    except Exception as e:
        logger.error(f"❌ Failed to get schedule for {year}: {e}")
        return pd.DataFrame()

    # Determine rounds to collect
    if end_round is None:
        end_round = int(schedule["RoundNumber"].max())

    all_race_data: list[pd.DataFrame] = []

    # Collect data for each round
    for round_num in range(start_round, end_round + 1):
        logger.info(f"ℹ️ Processing {year} Round {round_num}...")

        try:
            race_data = collect_race_data(year, round_num, load_telemetry=False)

            if race_data is not None and not race_data.empty:
                all_race_data.append(race_data)
                logger.info(
                    f"✅ Collected data for {year} Round {round_num}: {len(race_data)} drivers"
                )
            else:
                logger.warning(f"⚠️ No data collected for {year} Round {round_num}")

        except Exception as e:
            logger.error(f"❌ Error collecting data for {year} Round {round_num}: {e}")
            continue

    if not all_race_data:
        logger.warning(f"⚠️ No race data collected for {year}")
        return pd.DataFrame()

    # Combine all races
    season_df = pd.concat(all_race_data, ignore_index=True)
    logger.info(f"ℹ️ Collected {len(season_df)} driver-race entries for {year}")

    return season_df


def collect_multiple_seasons(
    years: list[int], output_file: str = "data/processed/historical_races.csv"
) -> pd.DataFrame:
    """
    Collect data for multiple seasons and combine into single dataset.

    Args:
        years: List of years to collect
        output_file: Path to save the final dataset

    Returns:
        Combined DataFrame with all seasons
    """
    logger.info(f"ℹ️ Collecting data for seasons: {years}")

    all_seasons: list[pd.DataFrame] = []

    for year in years:
        season_df = collect_season_data(year)

        if not season_df.empty:
            all_seasons.append(season_df)
        else:
            logger.warning(f"⚠️ No data collected for {year}")

    if not all_seasons:
        logger.error("❌ No data collected for any season")
        return pd.DataFrame()

    # Combine all seasons
    combined_df = pd.concat(all_seasons, ignore_index=True)
    logger.info(f"ℹ️ Combined dataset: {len(combined_df)} driver-race entries")

    # Sort by year and round for proper historical calculation
    combined_df = combined_df.sort_values(["year", "round_number"], ascending=True)

    # Calculate historical statistics
    logger.info("ℹ️ Calculating historical statistics...")
    combined_df = calculate_historical_stats_for_all(combined_df)

    # Add feature columns
    logger.info("ℹ️ Adding feature columns...")
    combined_df = add_feature_columns(combined_df)

    # Prepare final ML dataset
    logger.info("ℹ️ Preparing final ML dataset...")
    final_df = prepare_ml_dataset(combined_df)

    # Save to file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    final_df.to_csv(output_file, index=False)
    logger.info(f"✅ Saved dataset to {output_file}")
    logger.info(f"ℹ️ Dataset shape: {final_df.shape}")

    return final_df


def calculate_historical_stats_for_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate historical stats for all races in the dataset.

    Args:
        df: DataFrame with race data (must be sorted by year, round)

    Returns:
        DataFrame with historical stats added
    """
    result = df.copy()

    # Initialize historical columns
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
        result[col] = None

    # Group by year and round, process in order
    grouped = result.groupby(["year", "round_number"])

    total_races = len(grouped)
    current_race = 0

    for (year, round_num), race_df in grouped:
        current_race += 1
        if current_race % 5 == 0:
            logger.info(f"ℹ️ Processing race {current_race}/{total_races}: {year} Round {round_num}")

        # Calculate stats up to this race
        result = calculate_historical_stats(result, year, round_num)

    logger.info("✅ Historical statistics calculated for all races")
    return result


def main():
    """Main entry point for data collection script."""
    parser = argparse.ArgumentParser(description="Collect historical F1 race data for ML model")
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=[2020, 2021, 2022, 2023, 2024],
        help="Years to collect (default: 2020-2024)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/historical_races.csv",
        help="Output file path (default: data/processed/historical_races.csv)",
    )
    parser.add_argument(
        "--start-year", type=int, help="Start year (if collecting single year range)"
    )
    parser.add_argument("--end-year", type=int, help="End year (if collecting single year range)")

    args = parser.parse_args()

    # Setup logging
    setup_logging()
    logger.info("🚀 Starting historical data collection")

    # Enable FastF1 cache
    enable_cache()

    # Determine years to collect
    if args.start_year and args.end_year:
        years = list(range(args.start_year, args.end_year + 1))
    else:
        years = args.years

    logger.info(f"ℹ️ Will collect data for years: {years}")

    # Collect data
    try:
        dataset = collect_multiple_seasons(years, args.output)

        if dataset.empty:
            logger.error("❌ No data collected")
            sys.exit(1)

        logger.info("✅ Data collection completed successfully")
        logger.info(f"ℹ️ Final dataset: {len(dataset)} rows, {len(dataset.columns)} columns")
        logger.info(f"ℹ️ Years covered: {dataset['year'].min()} - {dataset['year'].max()}")
        logger.info(f"ℹ️ Races: {dataset.groupby(['year', 'round_number']).ngroups}")

    except KeyboardInterrupt:
        logger.warning("⚠️ Collection interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error during collection: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
