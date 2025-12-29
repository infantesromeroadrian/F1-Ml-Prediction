"""Telemetry processing functions for F1 data."""

import logging
import sys
from datetime import timedelta
from multiprocessing import Pool, cpu_count
from typing import Any

import numpy as np
import pandas as pd
from fastf1.core import Session
from src.f1_data.cache import load_cached_data, save_cached_data
from src.f1_data.loaders import get_driver_colors
from src.utils.time import parse_time_string
from src.utils.tyres import get_tyre_compound_int

logger = logging.getLogger(__name__)

# Constants
FPS = 25
DT = 1.0 / FPS


def _process_single_driver(args: tuple[int, Session, str]) -> dict[str, Any] | None:
    """
    Process telemetry data for a single driver.

    Must be top-level function for multiprocessing.

    Args:
        args: Tuple of (driver_no, session, driver_code)

    Returns:
        Dictionary with driver telemetry data or None if no data
    """
    driver_no, session, driver_code = args

    logger.info(f"ℹ️ Processing telemetry for driver: {driver_code}")

    try:
        laps_driver = session.laps.pick_drivers(driver_no)
        if laps_driver.empty:
            logger.warning(f"⚠️ No laps found for driver {driver_code}")
            return None

        driver_max_lap = int(laps_driver.LapNumber.max()) if not laps_driver.empty else 0

        t_all: list[np.ndarray] = []
        x_all: list[np.ndarray] = []
        y_all: list[np.ndarray] = []
        race_dist_all: list[np.ndarray] = []
        rel_dist_all: list[np.ndarray] = []
        lap_numbers: list[np.ndarray] = []
        tyre_compounds: list[np.ndarray] = []
        speed_all: list[np.ndarray] = []
        gear_all: list[np.ndarray] = []
        drs_all: list[np.ndarray] = []
        throttle_all: list[np.ndarray] = []
        brake_all: list[np.ndarray] = []

        total_dist_so_far = 0.0

        # Iterate laps in order
        for _, lap in laps_driver.iterlaps():
            lap_tel = lap.get_telemetry()
            lap_number = lap.LapNumber
            tyre_compound_as_int = get_tyre_compound_int(lap.Compound)

            if lap_tel.empty:
                continue

            t_lap = lap_tel["SessionTime"].dt.total_seconds().to_numpy()
            x_lap = lap_tel["X"].to_numpy()
            y_lap = lap_tel["Y"].to_numpy()
            d_lap = lap_tel["Distance"].to_numpy()
            rd_lap = lap_tel["RelativeDistance"].to_numpy()
            speed_kph_lap = lap_tel["Speed"].to_numpy()
            gear_lap = lap_tel["nGear"].to_numpy()
            drs_lap = lap_tel["DRS"].to_numpy()
            throttle_lap = lap_tel["Throttle"].to_numpy()
            brake_lap = lap_tel["Brake"].to_numpy().astype(float)

            # Race distance = distance before this lap + distance within this lap
            race_d_lap = total_dist_so_far + d_lap

            t_all.append(t_lap)
            x_all.append(x_lap)
            y_all.append(y_lap)
            race_dist_all.append(race_d_lap)
            rel_dist_all.append(rd_lap)
            lap_numbers.append(np.full_like(t_lap, lap_number, dtype=np.float64))
            tyre_compounds.append(np.full_like(t_lap, tyre_compound_as_int, dtype=np.float64))
            speed_all.append(speed_kph_lap)
            gear_all.append(gear_lap)
            drs_all.append(drs_lap)
            throttle_all.append(throttle_lap)
            brake_all.append(brake_lap)

        if not t_all:
            logger.warning(f"⚠️ No telemetry data collected for driver {driver_code}")
            return None

        # Concatenate all arrays
        all_arrays = [
            t_all,
            x_all,
            y_all,
            race_dist_all,
            rel_dist_all,
            lap_numbers,
            tyre_compounds,
            speed_all,
            gear_all,
            drs_all,
        ]

        concatenated = [np.concatenate(arr) for arr in all_arrays]
        (
            t_all,
            x_all,
            y_all,
            race_dist_all,
            rel_dist_all,
            lap_numbers,
            tyre_compounds,
            speed_all,
            gear_all,
            drs_all,
        ) = concatenated

        # Sort all arrays by time
        order = np.argsort(t_all)
        all_data = [
            t_all,
            x_all,
            y_all,
            race_dist_all,
            rel_dist_all,
            lap_numbers,
            tyre_compounds,
            speed_all,
            gear_all,
            drs_all,
        ]

        sorted_data = [arr[order] for arr in all_data]
        (
            t_all,
            x_all,
            y_all,
            race_dist_all,
            rel_dist_all,
            lap_numbers,
            tyre_compounds,
            speed_all,
            gear_all,
            drs_all,
        ) = sorted_data

        throttle_all = np.concatenate(throttle_all)[order]
        brake_all = np.concatenate(brake_all)[order]

        logger.info(f"ℹ️ Completed telemetry processing for driver: {driver_code}")

        return {
            "code": driver_code,
            "data": {
                "t": t_all,
                "x": x_all,
                "y": y_all,
                "dist": race_dist_all,
                "rel_dist": rel_dist_all,
                "lap": lap_numbers,
                "tyre": tyre_compounds,
                "speed": speed_all,
                "gear": gear_all,
                "drs": drs_all,
                "throttle": throttle_all,
                "brake": brake_all,
            },
            "t_min": float(t_all.min()),
            "t_max": float(t_all.max()),
            "max_lap": driver_max_lap,
        }
    except Exception as e:
        logger.error(f"❌ Error processing driver {driver_code}: {e}")
        return None


def _resample_weather_data(
    weather_df: pd.DataFrame, timeline: np.ndarray, global_t_min: float
) -> dict[str, np.ndarray] | None:
    """
    Resample weather data onto timeline.

    Args:
        weather_df: Weather DataFrame from session
        timeline: Target timeline array
        global_t_min: Minimum time for shifting

    Returns:
        Dictionary with resampled weather data or None
    """
    try:
        weather_times = weather_df["Time"].dt.total_seconds().to_numpy() - global_t_min
        if len(weather_times) == 0:
            return None

        order = np.argsort(weather_times)
        weather_times = weather_times[order]

        def _maybe_get(name: str) -> np.ndarray | None:
            """Get weather column if it exists."""
            return weather_df[name].to_numpy()[order] if name in weather_df else None

        def _resample(series: np.ndarray | None) -> np.ndarray | None:
            """Resample series onto timeline."""
            if series is None:
                return None
            return np.interp(timeline, weather_times, series)

        track_temp = _resample(_maybe_get("TrackTemp"))
        air_temp = _resample(_maybe_get("AirTemp"))
        humidity = _resample(_maybe_get("Humidity"))
        wind_speed = _resample(_maybe_get("WindSpeed"))
        wind_direction = _resample(_maybe_get("WindDirection"))
        rainfall_raw = _maybe_get("Rainfall")
        rainfall = _resample(rainfall_raw.astype(float)) if rainfall_raw is not None else None

        return {
            "track_temp": track_temp,
            "air_temp": air_temp,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "rainfall": rainfall,
        }
    except Exception as e:
        logger.warning(f"⚠️ Weather data could not be processed: {e}")
        return None


def _format_track_statuses(track_status: pd.DataFrame, global_t_min: float) -> list[dict[str, Any]]:
    """
    Format track status data for timeline.

    Args:
        track_status: Track status DataFrame
        global_t_min: Minimum time for shifting

    Returns:
        List of formatted track status dictionaries
    """
    formatted_statuses: list[dict[str, Any]] = []

    for status in track_status.to_dict("records"):
        seconds = timedelta.total_seconds(status["Time"])
        start_time = seconds - global_t_min
        end_time = None

        # Set end time of previous status
        if formatted_statuses:
            formatted_statuses[-1]["end_time"] = start_time

        formatted_statuses.append(
            {
                "status": status["Status"],
                "start_time": start_time,
                "end_time": end_time,
            }
        )

    return formatted_statuses


def get_race_telemetry(session: Session, session_type: str = "R") -> dict[str, Any]:
    """
    Get race telemetry data with caching support.

    Args:
        session: FastF1 session object
        session_type: Session type ('R'=Race, 'S'=Sprint)

    Returns:
        Dictionary with frames, driver_colors, track_statuses, total_laps

    Raises:
        ValueError: If no valid telemetry data found
    """
    event_name = str(session).replace(" ", "_")
    cache_suffix = "sprint" if session_type == "S" else "race"
    cache_path = f"computed_data/{event_name}_{cache_suffix}_telemetry.pkl"

    # Try to load from cache
    cached_data = load_cached_data(cache_path, refresh="--refresh-data" in sys.argv)
    if cached_data:
        logger.info(f"ℹ️ Loaded precomputed {cache_suffix} telemetry data from cache")
        return cached_data

    logger.info(f"ℹ️ Computing {cache_suffix} telemetry data...")

    drivers = session.drivers
    driver_codes = {num: session.get_driver(num)["Abbreviation"] for num in drivers}

    driver_data: dict[str, dict[str, np.ndarray]] = {}
    global_t_min: float | None = None
    global_t_max: float | None = None
    max_lap_number = 0

    # Process all drivers in parallel
    logger.info(f"ℹ️ Processing {len(drivers)} drivers in parallel...")
    driver_args = [(driver_no, session, driver_codes[driver_no]) for driver_no in drivers]
    num_processes = min(cpu_count(), len(drivers))

    try:
        with Pool(processes=num_processes) as pool:
            results = pool.map(_process_single_driver, driver_args)
    except Exception as e:
        logger.error(f"❌ Error in parallel processing: {e}")
        raise

    # Process results
    for result in results:
        if result is None:
            continue

        code = result["code"]
        driver_data[code] = result["data"]

        t_min = result["t_min"]
        t_max = result["t_max"]
        max_lap_number = max(max_lap_number, result["max_lap"])

        global_t_min = t_min if global_t_min is None else min(global_t_min, t_min)
        global_t_max = t_max if global_t_max is None else max(global_t_max, t_max)

    # Validate time bounds
    if global_t_min is None or global_t_max is None:
        error_msg = "No valid telemetry data found for any driver"
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)

    # Create timeline
    timeline = np.arange(global_t_min, global_t_max, DT) - global_t_min

    # Resample each driver's telemetry onto common timeline
    resampled_data: dict[str, dict[str, np.ndarray]] = {}

    for code, data in driver_data.items():
        t = data["t"] - global_t_min
        order = np.argsort(t)
        t_sorted = t[order]

        arrays_to_resample = [
            data["x"][order],
            data["y"][order],
            data["dist"][order],
            data["rel_dist"][order],
            data["lap"][order],
            data["tyre"][order],
            data["speed"][order],
            data["gear"][order],
            data["drs"][order],
            data["throttle"][order],
            data["brake"][order],
        ]

        resampled = [np.interp(timeline, t_sorted, arr) for arr in arrays_to_resample]
        (
            x_res,
            y_res,
            dist_res,
            rel_dist_res,
            lap_res,
            tyre_res,
            speed_res,
            gear_res,
            drs_res,
            throttle_res,
            brake_res,
        ) = resampled

        resampled_data[code] = {
            "t": timeline,
            "x": x_res,
            "y": y_res,
            "dist": dist_res,
            "rel_dist": rel_dist_res,
            "lap": lap_res,
            "tyre": tyre_res,
            "speed": speed_res,
            "gear": gear_res,
            "drs": drs_res,
            "throttle": throttle_res,
            "brake": brake_res,
        }

    # Format track statuses
    track_status = session.track_status
    formatted_track_statuses = _format_track_statuses(track_status, global_t_min)

    # Resample weather data
    weather_df = getattr(session, "weather_data", None)
    weather_resampled = None
    if weather_df is not None and not weather_df.empty:
        weather_resampled = _resample_weather_data(weather_df, timeline, global_t_min)

    # Build frames
    frames: list[dict[str, Any]] = []
    num_frames = len(timeline)
    driver_codes_list = list(resampled_data.keys())
    driver_arrays = {code: resampled_data[code] for code in driver_codes_list}

    for i in range(num_frames):
        t = timeline[i]
        snapshot: list[dict[str, Any]] = []

        for code in driver_codes_list:
            d = driver_arrays[code]
            snapshot.append(
                {
                    "code": code,
                    "dist": float(d["dist"][i]),
                    "x": float(d["x"][i]),
                    "y": float(d["y"][i]),
                    "lap": int(round(d["lap"][i])),
                    "rel_dist": float(d["rel_dist"][i]),
                    "tyre": float(d["tyre"][i]),
                    "speed": float(d["speed"][i]),
                    "gear": int(d["gear"][i]),
                    "drs": int(d["drs"][i]),
                    "throttle": float(d["throttle"][i]),
                    "brake": float(d["brake"][i]),
                }
            )

        if not snapshot:
            continue

        # Sort by race distance to get positions
        snapshot.sort(key=lambda r: r["dist"], reverse=True)
        leader = snapshot[0]
        leader_lap = leader["lap"]

        # Build frame data
        frame_data: dict[str, dict[str, Any]] = {}
        for idx, car in enumerate(snapshot):
            code = car["code"]
            frame_data[code] = {
                "x": car["x"],
                "y": car["y"],
                "dist": car["dist"],
                "lap": car["lap"],
                "rel_dist": round(car["rel_dist"], 4),
                "tyre": car["tyre"],
                "position": idx + 1,
                "speed": car["speed"],
                "gear": car["gear"],
                "drs": car["drs"],
                "throttle": car["throttle"],
                "brake": car["brake"],
            }

        # Add weather snapshot if available
        weather_snapshot: dict[str, Any] = {}
        if weather_resampled:
            try:
                wt = weather_resampled
                rain_val = wt["rainfall"][i] if wt.get("rainfall") is not None else 0.0
                weather_snapshot = {
                    "track_temp": float(wt["track_temp"][i])
                    if wt.get("track_temp") is not None
                    else None,
                    "air_temp": float(wt["air_temp"][i])
                    if wt.get("air_temp") is not None
                    else None,
                    "humidity": float(wt["humidity"][i])
                    if wt.get("humidity") is not None
                    else None,
                    "wind_speed": float(wt["wind_speed"][i])
                    if wt.get("wind_speed") is not None
                    else None,
                    "wind_direction": float(wt["wind_direction"][i])
                    if wt.get("wind_direction") is not None
                    else None,
                    "rain_state": "RAINING" if rain_val and rain_val >= 0.5 else "DRY",
                }
            except Exception as e:
                logger.warning(f"⚠️ Failed to attach weather data to frame {i}: {e}")

        frame_payload: dict[str, Any] = {
            "t": round(t, 3),
            "lap": leader_lap,
            "drivers": frame_data,
        }
        if weather_snapshot:
            frame_payload["weather"] = weather_snapshot

        frames.append(frame_payload)

    logger.info(f"ℹ️ Completed telemetry extraction: {num_frames} frames")

    # Prepare result
    result = {
        "frames": frames,
        "driver_colors": get_driver_colors(session),
        "track_statuses": formatted_track_statuses,
        "total_laps": int(max_lap_number),
    }

    # Save to cache
    try:
        save_cached_data(result, cache_path)
        logger.info("ℹ️ Saved telemetry data to cache")
    except Exception as e:
        logger.warning(f"⚠️ Failed to save cache: {e}")

    return result


def get_qualifying_results(session: Session) -> list[dict[str, Any]]:
    """
    Extract qualifying results from session.

    Args:
        session: FastF1 session object

    Returns:
        List of dictionaries with driver codes, positions, and Q1/Q2/Q3 times
    """
    try:
        results = session.results
        qualifying_data: list[dict[str, Any]] = []

        for _, row in results.iterrows():
            driver_code = row["Abbreviation"]
            position = int(row["Position"])
            q1_time = row["Q1"]
            q2_time = row["Q2"]
            q3_time = row["Q3"]

            def convert_time_to_seconds(time_val: Any) -> str | None:
                """Convert pandas Timedelta to seconds string."""
                if pd.isna(time_val):
                    return None
                return str(time_val.total_seconds())

            qualifying_data.append(
                {
                    "code": driver_code,
                    "position": position,
                    "color": get_driver_colors(session).get(driver_code, (128, 128, 128)),
                    "Q1": convert_time_to_seconds(q1_time),
                    "Q2": convert_time_to_seconds(q2_time),
                    "Q3": convert_time_to_seconds(q3_time),
                }
            )

        logger.info(f"ℹ️ Extracted qualifying results for {len(qualifying_data)} drivers")
        return qualifying_data
    except Exception as e:
        logger.error(f"❌ Error extracting qualifying results: {e}")
        raise


def get_driver_quali_telemetry(
    session: Session, driver_code: str, quali_segment: str
) -> dict[str, Any]:
    """
    Get qualifying telemetry for a specific driver and segment.

    Args:
        session: FastF1 session object
        driver_code: Driver abbreviation code
        quali_segment: Qualifying segment ('Q1', 'Q2', or 'Q3')

    Returns:
        Dictionary with frames, track_statuses, drs_zones, max_speed, min_speed

    Raises:
        ValueError: If segment is invalid or no data found
    """
    try:
        # Split Q1/Q2/Q3 sections
        q1, q2, q3 = session.laps.split_qualifying_sessions()

        segments = {"Q1": q1, "Q2": q2, "Q3": q3}

        if quali_segment not in segments:
            raise ValueError("quali_segment must be 'Q1', 'Q2', or 'Q3'")

        segment_laps = segments[quali_segment]
        if segment_laps is None:
            raise ValueError(f"{quali_segment} does not exist for this session.")

        # Filter laps for the driver
        driver_laps = segment_laps.pick_drivers(driver_code)
        if driver_laps.empty:
            raise ValueError(f"No laps found for driver '{driver_code}' in {quali_segment}")

        # Pick fastest lap
        fastest_lap = driver_laps.pick_fastest()
        if fastest_lap is None:
            raise ValueError(f"No valid laps for driver '{driver_code}' in {quali_segment}")

        telemetry = fastest_lap.get_telemetry()

        # Guard: if telemetry has no time data, return empty
        if telemetry is None or telemetry.empty or "Time" not in telemetry or len(telemetry) == 0:
            logger.warning(f"⚠️ No telemetry data for {driver_code} in {quali_segment}")
            return {"frames": [], "track_statuses": []}

        global_t_min = float(telemetry["Time"].dt.total_seconds().min())
        global_t_max = float(telemetry["Time"].dt.total_seconds().max())
        max_speed = float(telemetry["Speed"].max())
        min_speed = float(telemetry["Speed"].min())

        lap_drs_zones: list[dict[str, Any]] = []

        # Build arrays directly from dataframes
        t_arr = telemetry["Time"].dt.total_seconds().to_numpy()
        x_arr = telemetry["X"].to_numpy()
        y_arr = telemetry["Y"].to_numpy()
        dist_arr = telemetry["Distance"].to_numpy()
        rel_dist_arr = telemetry["RelativeDistance"].to_numpy()
        speed_arr = telemetry["Speed"].to_numpy()
        gear_arr = telemetry["nGear"].to_numpy()
        throttle_arr = telemetry["Throttle"].to_numpy()
        brake_arr = telemetry["Brake"].to_numpy()
        drs_arr = telemetry["DRS"].to_numpy()

        # Recompute time bounds
        global_t_min = float(t_arr.min())
        global_t_max = float(t_arr.max())

        # Create timeline
        timeline = np.arange(global_t_min, global_t_max + DT / 2, DT) - global_t_min

        if t_arr.size == 0:
            return {"frames": [], "track_statuses": []}

        # Shift telemetry times
        t_rel = t_arr - global_t_min

        # Sort & deduplicate
        order = np.argsort(t_rel)
        t_sorted = t_rel[order]
        t_sorted_unique, unique_idx = np.unique(t_sorted, return_index=True)
        idx_map = order[unique_idx]

        x_sorted = x_arr[idx_map]
        y_sorted = y_arr[idx_map]
        dist_sorted = dist_arr[idx_map]
        rel_dist_sorted = rel_dist_arr[idx_map]
        speed_sorted = speed_arr[idx_map]
        gear_sorted = gear_arr[idx_map]
        throttle_sorted = throttle_arr[idx_map]
        brake_sorted = brake_arr[idx_map]
        drs_sorted = drs_arr[idx_map]

        # Continuous interpolation
        x_resampled = np.interp(timeline, t_sorted_unique, x_sorted)
        y_resampled = np.interp(timeline, t_sorted_unique, y_sorted)
        dist_resampled = np.interp(timeline, t_sorted_unique, dist_sorted)
        rel_dist_resampled = np.interp(timeline, t_sorted_unique, rel_dist_sorted)
        speed_resampled = np.round(np.interp(timeline, t_sorted_unique, speed_sorted), 1)
        throttle_resampled = np.round(np.interp(timeline, t_sorted_unique, throttle_sorted), 1)
        brake_resampled = np.round(np.interp(timeline, t_sorted_unique, brake_sorted), 1)
        drs_resampled = np.interp(timeline, t_sorted_unique, drs_sorted)

        # Scale brake to 0-100
        brake_resampled = brake_resampled * 100.0

        # Forward-fill for discrete fields (gear)
        idxs = np.searchsorted(t_sorted_unique, timeline, side="right") - 1
        idxs = np.clip(idxs, 0, len(t_sorted_unique) - 1)
        gear_resampled = gear_sorted[idxs].astype(int)

        resampled_data = {
            "t": timeline,
            "x": x_resampled,
            "y": y_resampled,
            "dist": dist_resampled,
            "rel_dist": rel_dist_resampled,
            "speed": speed_resampled,
            "gear": gear_resampled,
            "throttle": throttle_resampled,
            "brake": brake_resampled,
            "drs": drs_resampled,
        }

        # Format track statuses
        track_status = session.track_status
        formatted_track_statuses = _format_track_statuses(track_status, global_t_min)

        # Resample weather data
        weather_df = getattr(session, "weather_data", None)
        weather_resampled = None
        if weather_df is not None and not weather_df.empty:
            weather_resampled = _resample_weather_data(weather_df, timeline, global_t_min)

        # Build frames
        frames: list[dict[str, Any]] = []
        num_frames = len(timeline)

        for i in range(num_frames):
            t = timeline[i]

            # Weather snapshot
            weather_snapshot: dict[str, Any] = {}
            if weather_resampled:
                try:
                    wt = weather_resampled
                    rain_val = wt["rainfall"][i] if wt.get("rainfall") is not None else 0.0
                    weather_snapshot = {
                        "track_temp": float(wt["track_temp"][i])
                        if wt.get("track_temp") is not None
                        else None,
                        "air_temp": float(wt["air_temp"][i])
                        if wt.get("air_temp") is not None
                        else None,
                        "humidity": float(wt["humidity"][i])
                        if wt.get("humidity") is not None
                        else None,
                        "wind_speed": float(wt["wind_speed"][i])
                        if wt.get("wind_speed") is not None
                        else None,
                        "wind_direction": float(wt["wind_direction"][i])
                        if wt.get("wind_direction") is not None
                        else None,
                        "rain_state": "RAINING" if rain_val and rain_val >= 0.5 else "DRY",
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Failed to attach weather data to frame {i}: {e}")

            # Detect DRS zone changes
            if i > 0:
                drs_prev = resampled_data["drs"][i - 1]
                drs_curr = resampled_data["drs"][i]

                if (drs_curr >= 10) and (drs_prev < 10):
                    # DRS activated
                    lap_drs_zones.append(
                        {
                            "zone_start": float(resampled_data["dist"][i]),
                            "zone_end": None,
                        }
                    )
                elif (drs_curr < 10) and (drs_prev >= 10):
                    # DRS deactivated
                    if lap_drs_zones and lap_drs_zones[-1]["zone_end"] is None:
                        lap_drs_zones[-1]["zone_end"] = float(resampled_data["dist"][i])

            frame_payload: dict[str, Any] = {
                "t": round(t, 3),
                "telemetry": {
                    "x": float(resampled_data["x"][i]),
                    "y": float(resampled_data["y"][i]),
                    "dist": float(resampled_data["dist"][i]),
                    "rel_dist": float(resampled_data["rel_dist"][i]),
                    "speed": float(resampled_data["speed"][i]),
                    "gear": int(resampled_data["gear"][i]),
                    "throttle": float(resampled_data["throttle"][i]),
                    "brake": float(resampled_data["brake"][i]),
                    "drs": int(resampled_data["drs"][i]),
                },
            }
            if weather_snapshot:
                frame_payload["weather"] = weather_snapshot

            frames.append(frame_payload)

        # Set final frame time to exact lap time
        frames[-1]["t"] = round(parse_time_string(str(fastest_lap["LapTime"])), 3)

        logger.info(
            f"ℹ️ Processed qualifying telemetry for {driver_code} {quali_segment}: {num_frames} frames"
        )

        return {
            "frames": frames,
            "track_statuses": formatted_track_statuses,
            "drs_zones": lap_drs_zones,
            "max_speed": max_speed,
            "min_speed": min_speed,
        }
    except Exception as e:
        logger.error(
            f"❌ Error processing qualifying telemetry for {driver_code} {quali_segment}: {e}"
        )
        raise


def _process_quali_driver(args: tuple[Session, str]) -> dict[str, Any]:
    """
    Process qualifying telemetry for a single driver.

    Must be top-level function for multiprocessing.

    Args:
        args: Tuple of (session, driver_code)

    Returns:
        Dictionary with driver telemetry data for all segments
    """
    session, driver_code = args

    logger.info(f"ℹ️ Processing qualifying telemetry for driver: {driver_code}")

    driver_telemetry_data: dict[str, dict[str, Any]] = {}
    max_speed = 0.0
    min_speed = 0.0

    for segment in ["Q1", "Q2", "Q3"]:
        try:
            segment_telemetry = get_driver_quali_telemetry(session, driver_code, segment)
            driver_telemetry_data[segment] = segment_telemetry

            # Update global max/min speed
            max_speed = max(max_speed, segment_telemetry["max_speed"])
            if segment_telemetry["min_speed"] < min_speed or min_speed == 0.0:
                min_speed = segment_telemetry["min_speed"]
        except ValueError as e:
            logger.debug(f"🐞 {driver_code} {segment}: {e}")
            driver_telemetry_data[segment] = {"frames": [], "track_statuses": []}

    logger.info(f"ℹ️ Finished processing qualifying telemetry for driver: {driver_code}")

    return {
        "driver_code": driver_code,
        "driver_telemetry_data": driver_telemetry_data,
        "max_speed": max_speed,
        "min_speed": min_speed,
    }


def get_quali_telemetry(session: Session, session_type: str = "Q") -> dict[str, Any]:
    """
    Get qualifying telemetry for all drivers with caching support.

    Args:
        session: FastF1 session object
        session_type: Session type ('Q'=Qualifying, 'SQ'=Sprint Qualifying)

    Returns:
        Dictionary with results, telemetry, max_speed, min_speed
    """
    event_name = str(session).replace(" ", "_")
    cache_suffix = "sprintquali" if session_type == "SQ" else "quali"
    cache_path = f"computed_data/{event_name}_{cache_suffix}_telemetry.pkl"

    # Try to load from cache
    cached_data = load_cached_data(cache_path, refresh="--refresh-data" in sys.argv)
    if cached_data:
        logger.info(f"ℹ️ Loaded precomputed {cache_suffix} telemetry data from cache")
        return cached_data

    logger.info(f"ℹ️ Computing {cache_suffix} telemetry data...")

    qualifying_results = get_qualifying_results(session)

    driver_codes = {num: session.get_driver(num)["Abbreviation"] for num in session.drivers}

    telemetry_data: dict[str, dict[str, dict[str, Any]]] = {}
    max_speed = 0.0
    min_speed = 0.0

    driver_args = [(session, driver_codes[driver_no]) for driver_no in session.drivers]

    logger.info(f"ℹ️ Processing {len(session.drivers)} drivers in parallel...")
    num_processes = min(cpu_count(), len(session.drivers))

    try:
        with Pool(processes=num_processes) as pool:
            results = pool.map(_process_quali_driver, driver_args)
    except Exception as e:
        logger.error(f"❌ Error in parallel processing: {e}")
        raise

    for result in results:
        driver_code = result["driver_code"]
        telemetry_data[driver_code] = result["driver_telemetry_data"]

        max_speed = max(max_speed, result["max_speed"])
        if result["min_speed"] < min_speed or min_speed == 0.0:
            min_speed = result["min_speed"]

    # Prepare result
    result_data = {
        "results": qualifying_results,
        "telemetry": telemetry_data,
        "max_speed": max_speed,
        "min_speed": min_speed,
    }

    # Save to cache
    try:
        save_cached_data(result_data, cache_path)
        logger.info("ℹ️ Saved qualifying telemetry data to cache")
    except Exception as e:
        logger.warning(f"⚠️ Failed to save cache: {e}")

    return result_data
