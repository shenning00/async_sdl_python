"""State management for PySDL framework.

This module defines the base state class and predefined states used in
state machines throughout the PySDL framework.
"""

from __future__ import annotations


class SdlState:
    """Base SDL state class.

    Represents a state in a finite state machine. States are used to define
    process behavior and transition logic based on incoming signals.

    Attributes:
        _name: Internal state identifier.
    """

    _name: str

    def __init__(self, name: str) -> None:
        """Initialize a state with a name.

        Args:
            name: The state identifier.
        """
        self._name = name

    def __str__(self) -> str:
        """Return string representation of the state.

        Returns:
            The state name.
        """
        return f"{self.name()}"

    def __format__(self, formatspec: str) -> str:
        """Format the state name.

        Args:
            formatspec: The format specification.

        Returns:
            Formatted state name.
        """
        return format(str(self.name()), formatspec)

    def id(self) -> str:
        """Get the state identifier.

        Returns:
            The state identifier string.
        """
        return self._name

    def name(self) -> str:
        """Get the state name.

        Returns:
            The state name string.
        """
        return self._name

    def _set_name(self, _name: str) -> None:
        """Set the state name (internal method).

        Args:
            _name: The new state name.

        Note:
            This is a private method used for internal state management.
        """
        self._name = _name


# Predefined states used throughout the framework
start = SdlState("start")
"""The initial state for all processes."""

wait = SdlState("wait")
"""A common waiting state for processes."""

star = SdlState("*")
"""Wildcard state for catch-all state machine handlers."""
