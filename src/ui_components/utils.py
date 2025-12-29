"""Utility functions for UI components."""



def format_wind_direction(degrees: float | None) -> str:
    """
    Format wind direction in degrees to compass direction.

    Args:
        degrees: Wind direction in degrees (0-360)

    Returns:
        Compass direction string (N, NE, E, etc.)
    """
    if degrees is None:
        return "N/A"
    deg_norm = degrees % 360
    dirs = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    idx = int((deg_norm / 22.5) + 0.5) % len(dirs)
    return dirs[idx]
