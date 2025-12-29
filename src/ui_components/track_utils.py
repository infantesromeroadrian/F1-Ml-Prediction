"""Track utility functions for building track geometry and DRS zones."""

from typing import Any

import numpy as np
from pandas import DataFrame


def plotDRSzones(example_lap: DataFrame) -> list[dict[str, dict[str, Any]]]:
    """
    Identify and extract DRS zones from an example lap's telemetry.

    Args:
        example_lap: DataFrame with telemetry data including 'X', 'Y', 'DRS' columns

    Returns:
        List of DRS zone dictionaries with start and end points
    """
    x_val = example_lap["X"]
    y_val = example_lap["Y"]
    drs_zones: list[dict[str, dict[str, Any]]] = []
    drs_start: int | None = None

    for i, val in enumerate(example_lap["DRS"]):
        if val in [10, 12, 14]:
            if drs_start is None:
                drs_start = i
        elif drs_start is not None:
            drs_end = i - 1
            zone = {
                "start": {
                    "x": x_val.iloc[drs_start],
                    "y": y_val.iloc[drs_start],
                    "index": drs_start,
                },
                "end": {"x": x_val.iloc[drs_end], "y": y_val.iloc[drs_end], "index": drs_end},
            }
            drs_zones.append(zone)
            drs_start = None

    # Handle case where DRS zone extends to end of lap
    if drs_start is not None:
        drs_end = len(example_lap["DRS"]) - 1
        zone = {
            "start": {"x": x_val.iloc[drs_start], "y": y_val.iloc[drs_start], "index": drs_start},
            "end": {"x": x_val.iloc[drs_end], "y": y_val.iloc[drs_end], "index": drs_end},
        }
        drs_zones.append(zone)

    return drs_zones


def build_track_from_example_lap(
    example_lap: DataFrame, track_width: int = 200
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    float,
    float,
    float,
    float,
    list[dict[str, dict[str, Any]]],
]:
    """
    Build track geometry from an example lap's telemetry.

    Args:
        example_lap: DataFrame with telemetry data including 'X', 'Y', 'DRS' columns
        track_width: Width of the track in meters

    Returns:
        Tuple containing:
        - plot_x_ref: Reference X coordinates
        - plot_y_ref: Reference Y coordinates
        - x_inner: Inner boundary X coordinates
        - y_inner: Inner boundary Y coordinates
        - x_outer: Outer boundary X coordinates
        - y_outer: Outer boundary Y coordinates
        - x_min: Minimum X coordinate
        - x_max: Maximum X coordinate
        - y_min: Minimum Y coordinate
        - y_max: Maximum Y coordinate
        - drs_zones: List of DRS zone dictionaries
    """
    drs_zones = plotDRSzones(example_lap)
    plot_x_ref = example_lap["X"]
    plot_y_ref = example_lap["Y"]

    # Compute tangents
    dx = np.gradient(plot_x_ref)
    dy = np.gradient(plot_y_ref)

    norm = np.sqrt(dx**2 + dy**2)
    norm[norm == 0] = 1.0
    dx /= norm
    dy /= norm

    nx = -dy
    ny = dx

    x_outer = plot_x_ref + nx * (track_width / 2)
    y_outer = plot_y_ref + ny * (track_width / 2)
    x_inner = plot_x_ref - nx * (track_width / 2)
    y_inner = plot_y_ref - ny * (track_width / 2)

    # World bounds
    x_min = float(min(plot_x_ref.min(), x_inner.min(), x_outer.min()))
    x_max = float(max(plot_x_ref.max(), x_inner.max(), x_outer.max()))
    y_min = float(min(plot_y_ref.min(), y_inner.min(), y_outer.min()))
    y_max = float(max(plot_y_ref.max(), y_inner.max(), y_outer.max()))

    return (
        plot_x_ref,
        plot_y_ref,
        x_inner,
        y_inner,
        x_outer,
        y_outer,
        x_min,
        x_max,
        y_min,
        y_max,
        drs_zones,
    )
