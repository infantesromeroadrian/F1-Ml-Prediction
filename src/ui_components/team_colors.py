"""
Official F1 2024 Team Colors - Broadcast Style.

These are the vibrant, saturated colors used in official F1 broadcasts,
optimized for visual clarity and brand recognition.
"""

from typing import Dict, Tuple

# RGB colors (0-255 range)
TeamColor = Tuple[int, int, int]

# Official F1 2024 Team Colors (Broadcast Standard)
TEAM_COLORS_2024: Dict[str, TeamColor] = {
    # Red Bull Racing - Electric Blue
    "Red Bull Racing": (54, 113, 198),  # #3671C6
    # Mercedes-AMG Petronas - Silver Arrows
    "Mercedes": (39, 244, 210),  # #27F4D2 (Teal/Turquoise)
    # Ferrari - Rosso Corsa
    "Ferrari": (232, 0, 32),  # #E80020
    # McLaren - Papaya Orange
    "McLaren": (255, 135, 0),  # #FF8700
    # Aston Martin - British Racing Green
    "Aston Martin": (34, 153, 113),  # #229971
    # Alpine - French Blue/Pink
    "Alpine": (255, 135, 188),  # #FF87BC (Pink accent)
    # Williams - Electric Blue
    "Williams": (100, 196, 255),  # #64C4FF
    # Alfa Romeo (Stake) - Red/White
    "Alfa Romeo": (176, 15, 46),  # #B00F2E
    "Kick Sauber": (176, 15, 46),  # Same as Alfa Romeo
    # Haas F1 - White/Red/Blue
    "Haas F1 Team": (185, 185, 185),  # #B9B9B9 (Light Gray)
    # AlphaTauri/RB - Navy Blue
    "AlphaTauri": (70, 155, 255),  # #469BFF
    "RB": (70, 155, 255),  # Racing Bulls (formerly AlphaTauri)
    # Fallback - White
    "Default": (255, 255, 255),
}

# Driver-specific overrides (for special cases)
DRIVER_COLOR_OVERRIDES: Dict[str, TeamColor] = {
    # Examples:
    # "VER": (255, 204, 0),  # Gold for champion
    # "HAM": (200, 200, 200),  # Silver for 7-time champion
}

# Color brightness multipliers for different states
COLOR_STATES = {
    "normal": 1.0,
    "highlighted": 1.3,  # Brighter when highlighted
    "dimmed": 0.6,  # Darker when out of focus
    "flash": 1.5,  # Very bright for overtake flash
}


def get_team_color(team_name: str, state: str = "normal") -> TeamColor:
    """
    Get team color with optional state modifier.

    Args:
        team_name: Team name (e.g., "Red Bull Racing")
        state: Color state - "normal", "highlighted", "dimmed", "flash"

    Returns:
        RGB tuple (0-255 range)
    """
    # Get base color
    base_color = TEAM_COLORS_2024.get(team_name, TEAM_COLORS_2024["Default"])

    # Apply state multiplier
    multiplier = COLOR_STATES.get(state, 1.0)

    adjusted = tuple(min(255, int(c * multiplier)) for c in base_color)
    return adjusted


def get_driver_color(driver_code: str, team_name: str, state: str = "normal") -> TeamColor:
    """
    Get driver color with optional override.

    Args:
        driver_code: 3-letter driver code (e.g., "VER")
        team_name: Team name
        state: Color state

    Returns:
        RGB tuple (0-255 range)
    """
    # Check for driver-specific override
    if driver_code in DRIVER_COLOR_OVERRIDES:
        base_color = DRIVER_COLOR_OVERRIDES[driver_code]
    else:
        base_color = TEAM_COLORS_2024.get(team_name, TEAM_COLORS_2024["Default"])

    # Apply state multiplier
    multiplier = COLOR_STATES.get(state, 1.0)
    adjusted = tuple(min(255, int(c * multiplier)) for c in base_color)
    return adjusted


# Tire compound colors (official F1)
TIRE_COLORS = {
    "SOFT": (255, 45, 45),  # Red
    "MEDIUM": (255, 223, 0),  # Yellow
    "HARD": (245, 245, 245),  # White
    "INTERMEDIATE": (0, 170, 75),  # Green
    "WET": (0, 130, 255),  # Blue
    "UNKNOWN": (128, 128, 128),  # Gray
}

# DRS indicator colors
DRS_COLORS = {
    "available": (0, 255, 100),  # Bright green
    "active": (0, 255, 100),  # Bright green (same)
    "not_available": (80, 80, 80),  # Dark gray
}

# Timing colors (for sector times)
SECTOR_COLORS = {
    "personal_best": (200, 100, 255),  # Purple
    "overall_best": (0, 255, 0),  # Green
    "slower": (255, 255, 0),  # Yellow
    "normal": (255, 255, 255),  # White
}

# Track status colors
TRACK_STATUS_COLORS = {
    "1": (0, 255, 0),  # Green flag - Full green
    "2": (255, 255, 0),  # Yellow flag - Yellow
    "3": (255, 255, 0),  # Yellow flag
    "4": (255, 140, 0),  # Safety Car - Orange
    "5": (255, 0, 0),  # Red flag - Red
    "6": (230, 230, 230),  # Virtual Safety Car - Light gray
    "7": (200, 200, 200),  # VSC Ending - Gray
}
