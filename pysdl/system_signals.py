"""Built-in system signals for PySDL framework.

This module defines system-level signals used for process lifecycle management.
These signals are automatically generated and delivered by the PySDL framework
at specific lifecycle points.

System Signals:
    SdlStartSignal: Sent to a process immediately after registration
    SdlStoppingSignal: Sent when a process initiates graceful shutdown
    SdlStopSignal: Reserved for immediate stop (currently unused)
    SdlStarSignal: Wildcard signal for catch-all handlers (currently unused)
    SdlProcessNotExistSignal: Sent when a signal is sent to a non-existent process

Example:
    Handling system signals::

        from pysdl import SdlProcess, SdlStartSignal, SdlStoppingSignal, start

        class MyProcess(SdlProcess):
            def _init_state_machine(self):
                # Handle start signal
                self._event(start, SdlStartSignal, self.start_handler)

                # Handle stopping signal
                self._event(self.state_running, SdlStoppingSignal, self.stopping_handler)

                self._done()

            async def start_handler(self, signal):
                # Initialize process
                await self.next_state(self.state_running)

            async def stopping_handler(self, signal):
                # Clean up resources
                self.stop_process()
"""

from __future__ import annotations

from pysdl.signal import SdlSignal


class SdlStartSignal(SdlSignal):
    """Signal sent to process immediately after registration.

    The SdlStartSignal is automatically sent to a process after it is
    registered with the system via the create() factory method. This signal
    triggers the initial behavior of the process.

    Every process must handle this signal in the 'start' state to initialize
    properly.

    Example:
        >>> def _init_state_machine(self):
        ...     self._event(start, SdlStartSignal, self.start_handler)
        ...     self._done()
        ...
        >>> async def start_handler(self, signal):
        ...     # Initialize process state
        ...     await self.next_state(self.state_idle)
    """

    def __str__(self) -> str:
        base = super().__str__()
        return f"[{base}]"


class SdlStoppingSignal(SdlSignal):
    """Signal sent when process initiates graceful shutdown.

    The SdlStoppingSignal is sent to a process when stop() is called,
    allowing the process to perform cleanup before terminating. The handler
    should call stop_process() to complete the shutdown.

    Example:
        >>> def _init_state_machine(self):
        ...     self._event(self.state_running, SdlStoppingSignal, self.stopping_handler)
        ...     self._done()
        ...
        >>> async def stopping_handler(self, signal):
        ...     # Clean up resources
        ...     if hasattr(self, 'connection'):
        ...         self.connection.close()
        ...     self.stop_process()
    """

    def __str__(self) -> str:
        base = super().__str__()
        return f"[{base}]"


class SdlStopSignal(SdlSignal):
    """Reserved for immediate process stop (currently unused).

    This signal is defined but not currently used by the framework.
    It is reserved for future implementation of immediate (non-graceful)
    process termination.
    """

    def __str__(self) -> str:
        base = super().__str__()
        return f"[{base}]"


class SdlStarSignal(SdlSignal):
    """Wildcard signal for catch-all handlers.

    Use with state machine to handle any signal in a specific state.
    The framework uses 4-level priority matching to find handlers:
    1. Exact match (state, signal)
    2. Star state (any state, specific signal)
    3. Star signal (specific state, any signal) - this signal
    4. Double star (any state, any signal)

    Examples:
        Handle any signal in a specific state::

            self._event(self.state_active, SdlStarSignal, self.handle_any_signal)

        Ultimate catch-all with star state::

            from pysdl.state import star
            self._event(star, SdlStarSignal, self.handle_everything)

        Graceful fallback for unhandled signals::

            async def handle_any_signal(self, signal):
                # Log unexpected signals without crashing
                logger.info(f"Unhandled signal {signal.name()} in state_active")
    """

    def __str__(self) -> str:
        base = super().__str__()
        return f"[{base}]"


class SdlProcessNotExistSignal(SdlSignal):
    """Signal sent when attempting to deliver to a non-existent process.

    This error signal is automatically generated when a signal cannot be
    delivered because the destination process does not exist in the registry.
    It is sent back to the source process to allow it to handle the error.

    The signal contains information about the failed delivery in its data.

    Attributes:
        _error_data: Dictionary containing error information with keys:
            - original_signal: Type name of the signal that failed to deliver
            - destination: PID that could not be found
            - source: PID that sent the original signal

    Example:
        >>> def _init_state_machine(self):
        ...     self._event(self.state_running, SdlProcessNotExistSignal, self.handle_error)
        ...     self._done()
        ...
        >>> async def handle_error(self, signal):
        ...     # Handle the failed delivery
        ...     failed_dest = signal.get_data('destination')
        ...     print(f"Process {failed_dest} does not exist")
    """

    _error_data: dict[str, str]

    def __init__(
        self, original_signal: str = "", destination: str = "", source: str = ""
    ):
        """Initialize the error signal.

        Args:
            original_signal: Type name of the signal that failed
            destination: PID that could not be found
            source: PID that sent the original signal
        """
        super().__init__()
        self._error_data = {
            "original_signal": original_signal,
            "destination": destination,
            "source": source,
        }

    def get_data(self, key: str) -> str:
        """Get error data by key.

        Args:
            key: The data key to retrieve

        Returns:
            The data value or empty string if not found
        """
        return self._error_data.get(key, "")

    def __str__(self) -> str:
        base = super().__str__()
        dest = self._error_data.get("destination", "unknown")
        sig = self._error_data.get("original_signal", "unknown")
        return f"[{base} dest={dest} signal={sig}]"
