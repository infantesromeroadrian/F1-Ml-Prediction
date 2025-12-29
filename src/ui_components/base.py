"""Base component class for UI components."""

from typing import Protocol


class BaseComponent(Protocol):
    """Base interface for all UI components."""

    def on_resize(self, window) -> None:
        """Handle window resize event."""
        pass

    def draw(self, window) -> None:
        """Draw the component."""
        pass

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int) -> bool:
        """Handle mouse press event. Returns True if event was handled."""
        return False
