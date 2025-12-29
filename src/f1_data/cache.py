"""Cache management for F1 data."""

import logging
import os
import pickle
import sys
from typing import Any

logger = logging.getLogger(__name__)


def ensure_cache_dir(cache_dir: str = "computed_data") -> None:
    """
    Ensure cache directory exists.

    Args:
        cache_dir: Path to cache directory
    """
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        logger.info(f"ℹ️ Created cache directory: {cache_dir}")


def load_cached_data(cache_path: str, refresh: bool = False) -> dict[str, Any] | None:
    """
    Load cached data from pickle file.

    Args:
        cache_path: Path to cache file
        refresh: If True, skip loading cache

    Returns:
        Cached data dictionary or None if not found/refresh requested
    """
    if refresh or "--refresh-data" in sys.argv:
        logger.debug(f"🐞 Cache refresh requested, skipping load from {cache_path}")
        return None

    try:
        with open(cache_path, "rb") as f:
            data = pickle.load(f)
            logger.info(f"ℹ️ Loaded cached data from {cache_path}")
            return data
    except FileNotFoundError:
        logger.debug(f"🐞 Cache file not found: {cache_path}")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Failed to load cache from {cache_path}: {e}")
        return None


def save_cached_data(data: dict[str, Any], cache_path: str) -> None:
    """
    Save data to cache file.

    Args:
        data: Data dictionary to cache
        cache_path: Path to cache file
    """
    try:
        ensure_cache_dir(os.path.dirname(cache_path))
        with open(cache_path, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"ℹ️ Saved data to cache: {cache_path}")
    except Exception as e:
        logger.error(f"❌ Failed to save cache to {cache_path}: {e}")
        raise
