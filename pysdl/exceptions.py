"""
Custom exceptions for the SDL framework.

This module defines all custom exception classes used throughout the SDL system.
All exceptions inherit from SdlError, which is the base exception for the framework.
"""

from __future__ import annotations


class SdlError(Exception):
    """Base exception for all SDL framework errors.

    All custom SDL exceptions inherit from this base class, making it easy to
    catch all SDL-related errors with a single except clause.

    Attributes:
        message: The error message describing what went wrong
    """

    def __init__(self, message: str) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
        """
        self.message = message
        super().__init__(self.message)


class ProcessNotFoundError(SdlError):
    """Exception raised when a process cannot be found.

    This exception is raised when attempting to send a signal to a process
    that doesn't exist in the process registry, or when trying to perform
    operations on a non-existent process.

    Attributes:
        pid: The process ID that could not be found
        message: The error message
    """

    def __init__(self, pid: str, message: str = "") -> None:
        """Initialize the exception.

        Args:
            pid: The process ID that was not found
            message: Optional additional context about the error
        """
        self.pid = pid
        if not message:
            message = f"Process not found: {pid}"
        super().__init__(message)


class SignalDeliveryError(SdlError):
    """Exception raised when a signal cannot be delivered.

    This exception is raised when there are issues delivering a signal,
    such as when the destination process doesn't exist or when the signal
    queue encounters an error.

    Attributes:
        signal: The signal that failed to deliver (if available)
        destination: The intended destination PID
        message: The error message
    """

    def __init__(self, destination: str, message: str = "", signal: str = "") -> None:
        """Initialize the exception.

        Args:
            destination: The destination PID where delivery failed
            message: Optional additional context about the error
            signal: Optional signal type that failed to deliver
        """
        self.destination = destination
        self.signal = signal
        if not message:
            if signal:
                message = (
                    f"Failed to deliver signal '{signal}' to process '{destination}'"
                )
            else:
                message = f"Failed to deliver signal to process '{destination}'"
        super().__init__(message)


class StateTransitionError(SdlError):
    """Exception raised when a state transition fails or is invalid.

    This exception is raised when attempting an invalid state transition,
    such as when no handler is defined for a signal in the current state,
    or when a transition violates state machine constraints.

    Attributes:
        current_state: The current state when the error occurred
        signal: The signal that triggered the invalid transition
        process: The process where the error occurred
        message: The error message
    """

    def __init__(
        self, current_state: str, signal: str, process: str = "", message: str = ""
    ) -> None:
        """Initialize the exception.

        Args:
            current_state: The current state when the error occurred
            signal: The signal that triggered the invalid transition
            process: Optional process identifier
            message: Optional additional context about the error
        """
        self.current_state = current_state
        self.signal = signal
        self.process = process
        if not message:
            if process:
                message = (
                    f"Invalid state transition in process '{process}': "
                    f"no handler for signal '{signal}' in state '{current_state}'"
                )
            else:
                message = (
                    f"Invalid state transition: "
                    f"no handler for signal '{signal}' in state '{current_state}'"
                )
        super().__init__(message)


class TimerError(SdlError):
    """Exception raised when timer operations fail.

    This exception is raised when there are issues with timer management,
    such as starting a timer with invalid parameters, or when timer
    expiration encounters errors.

    Attributes:
        timer: String representation of the timer
        message: The error message
    """

    def __init__(self, timer: str = "", message: str = "") -> None:
        """Initialize the exception.

        Args:
            timer: Optional string representation of the timer
            message: Error message describing the problem
        """
        self.timer = timer
        if not message:
            if timer:
                message = f"Timer error: {timer}"
            else:
                message = "Timer operation failed"
        super().__init__(message)


class InvalidStateError(SdlError):
    """Exception raised when encountering an invalid state.

    This exception is raised when a state is invalid, undefined, or
    doesn't meet the requirements for the current operation.

    Attributes:
        state: The invalid state
        message: The error message
    """

    def __init__(self, state: str, message: str = "") -> None:
        """Initialize the exception.

        Args:
            state: The invalid state
            message: Optional additional context about the error
        """
        self.state = state
        if not message:
            message = f"Invalid state: {state}"
        super().__init__(message)


class QueueError(SdlError):
    """Exception raised when queue operations fail.

    This exception is raised when there are issues with the signal queue,
    such as queue full conditions or other queue-related errors.

    Attributes:
        message: The error message
    """

    def __init__(self, message: str = "Queue operation failed") -> None:
        """Initialize the exception.

        Args:
            message: Error message describing the problem
        """
        super().__init__(message)


class ValidationError(SdlError):
    """Exception raised when input validation fails.

    This exception is raised when input parameters fail validation,
    such as invalid PIDs, signal types, or other parameter issues.

    Attributes:
        parameter: The parameter that failed validation
        message: The error message
    """

    def __init__(self, parameter: str, message: str = "") -> None:
        """Initialize the exception.

        Args:
            parameter: The parameter that failed validation
            message: Error message describing the validation failure
        """
        self.parameter = parameter
        if not message:
            message = f"Validation error: invalid {parameter}"
        super().__init__(message)
