"""State machine implementation for PySDL framework.

This module provides the finite state machine implementation used to define
process behavior based on state and signal combinations. Supports 4-level
priority wildcard matching for flexible handler resolution.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from pysdl.exceptions import ValidationError
from pysdl.signal import SdlSignal
from pysdl.state import SdlState, star
from pysdl.system_signals import SdlStarSignal


class SdlStateMachine:
    """Base SDL state machine class.

    Implements a finite state machine with state/signal-based handler routing.
    Supports wildcard matching for flexible handler definitions.

    Attributes:
        _state: Current state being configured (builder pattern).
        _event: Current event ID being configured (builder pattern).
        _states: Registry of all defined states.
        _events: Registry of all defined event IDs.
        _handlers: Nested mapping from (state, event_id) to handler functions.
    """

    _state: SdlState | None
    _event: int | None
    _states: dict[SdlState, None]
    _events: dict[int, None]
    _handlers: dict[SdlState, dict[int, Callable[..., Coroutine[Any, Any, None]]]]

    def __init__(self) -> None:
        self._state = None
        self._event = None
        self._states = {}
        self._events = {}
        self._handlers = {}

    def state(self, state: SdlState) -> SdlStateMachine:
        """Set the current state for defining transitions.

        Args:
            state: The state to set as current

        Returns:
            Self for method chaining

        Raises:
            ValidationError: If state is None or invalid type
        """
        if state is None:
            raise ValidationError("state", "State cannot be None")

        if not isinstance(state, SdlState):
            raise ValidationError(
                "state", f"Expected SdlState, got {type(state).__name__}"
            )

        self._state = state
        self._states[state] = None
        return self

    def event(self, event: type[SdlSignal]) -> SdlStateMachine:
        """Set the current event/signal for defining transitions.

        Args:
            event: The signal class to set as current event

        Returns:
            Self for method chaining

        Raises:
            ValidationError: If event is None or not a SdlSignal subclass
        """
        if event is None:
            raise ValidationError("event", "Event cannot be None")

        try:
            if not issubclass(event, SdlSignal):
                raise ValidationError(
                    "event", f"Expected SdlSignal subclass, got {event}"
                )
        except TypeError as exc:
            raise ValidationError(
                "event", f"Event must be a class, got {type(event)}"
            ) from exc

        self._event = event.id()
        self._events[self._event] = None
        return self

    def handler(
        self, handle: Callable[..., Coroutine[Any, Any, None]]
    ) -> SdlStateMachine:
        """Register a handler for the current state and event.

        If a handler already exists for this state/event combination, it will be
        replaced (overwritten) with the new handler.

        Args:
            handle: The async handler function to register

        Returns:
            Self for method chaining

        Raises:
            ValidationError: If handler is not callable or state/event not set
        """
        if not callable(handle):
            raise ValidationError("handler", "Handler must be callable")

        if self._state is None:
            raise ValidationError("state", "State must be set before adding handler")

        if self._event is None:
            raise ValidationError("event", "Event must be set before adding handler")

        if self._state not in self._handlers:
            self._handlers[self._state] = {}

        self._handlers[self._state][self._event] = handle
        return self

    def done(self) -> bool:
        """Complete state machine definition.

        Signals that all states, events, and handlers have been defined.
        This is part of the builder pattern API.

        Returns:
            True to indicate successful completion.
        """
        return True

    def find(
        self, state: SdlState, event: int
    ) -> Callable[..., Coroutine[Any, Any, None]] | None:
        """Find handler with 4-level priority wildcard matching.

        Priority order (highest to lowest):
        1. Exact match: (state, event)
        2. Star state: (star, event) - any state, specific signal
        3. Star signal: (state, SdlStarSignal.id()) - specific state, any signal
        4. Double star: (star, SdlStarSignal.id()) - any state, any signal

        Args:
            state: The state to lookup
            event: The event ID to lookup

        Returns:
            The handler function if found, None otherwise

        Raises:
            ValidationError: If state or event is None/invalid
        """
        if state is None:
            raise ValidationError("state", "Cannot find handler for None state")

        if event is None:
            raise ValidationError("event", "Cannot find handler for None event")

        # Priority 1: Exact match (state, event)
        if state in self._handlers:
            states = self._handlers[state]
            if event in states:
                return states[event]

        # Priority 2: Star state (star, event) - specific signal, any state
        if star in self._handlers:
            star_handlers = self._handlers[star]
            if event in star_handlers:
                return star_handlers[event]

        # Priority 3: Star signal (state, SdlStarSignal) - any signal, specific state
        star_id = SdlStarSignal.id()
        if state in self._handlers:
            states = self._handlers[state]
            if star_id in states:
                return states[star_id]

        # Priority 4: Double star (star, SdlStarSignal) - catch-all
        if star in self._handlers:
            star_handlers = self._handlers[star]
            if star_id in star_handlers:
                return star_handlers[star_id]

        return None
