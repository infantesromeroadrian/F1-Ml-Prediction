"""
F1 data loading and processing module.

This module provides backward compatibility by re-exporting functions
from the modular structure in src/f1_data/.
"""

# Re-export from modular structure for backward compatibility
from src.f1_data.loaders import (
    enable_cache,
    get_circuit_rotation,
    get_driver_colors,
    list_rounds,
    list_sprints,
    load_session,
)
from src.f1_data.processors import (
    _process_quali_driver,
    _process_single_driver,
    get_driver_quali_telemetry,
    get_quali_telemetry,
    get_qualifying_results,
    get_race_telemetry,
)

# Constants
FPS = 25
DT = 1.0 / FPS

__all__ = [
    "DT",
    "FPS",
    "_process_quali_driver",
    "_process_single_driver",
    "enable_cache",
    "get_circuit_rotation",
    "get_driver_colors",
    "get_driver_quali_telemetry",
    "get_quali_telemetry",
    "get_qualifying_results",
    "get_race_telemetry",
    "list_rounds",
    "list_sprints",
    "load_session",
]
