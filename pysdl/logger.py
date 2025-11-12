"""Logging utilities for PySDL framework.

This module provides the SdlLogger class for logging process lifecycle events,
signal deliveries, state transitions, and application-level messages.

The logger is configurable with support for different log levels, category-based
logging, and performance optimization through lazy evaluation.

Configuration can be done via:
    1. Direct API calls to SdlLogger.configure()
    2. Environment variables (SDL_LOG_LEVEL, SDL_LOG_CATEGORIES)

Example:
    Basic usage::

        from pysdl.logger import SdlLogger

        # Configure logging
        SdlLogger.configure(
            level="INFO",
            categories={"signals": True, "states": True, "processes": True}
        )

        # Log messages
        SdlLogger.info("Application starting")
        SdlLogger.warning("Configuration missing")
        SdlLogger.signal("SdlSig", signal, process)
        SdlLogger.state(process, old_state, new_state)

    Environment variable configuration::

        # Set log level
        export SDL_LOG_LEVEL=WARNING

        # Enable specific categories (comma-separated)
        export SDL_LOG_CATEGORIES=signals,states

        # Disable all logging
        export SDL_LOG_LEVEL=CRITICAL
"""

from __future__ import annotations

import logging
import os
import sys
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pysdl.process import SdlProcess
    from pysdl.signal import SdlSignal
    from pysdl.state import SdlState


class LogCategory(Enum):
    """Log categories for fine-grained control over logging output.

    Each category can be independently enabled or disabled to control
    which types of events are logged.
    """

    SIGNALS = "signals"  # Signal delivery and routing events
    STATES = "states"  # State transition events
    PROCESSES = "processes"  # Process lifecycle events (create, stop, etc.)
    TIMERS = "timers"  # Timer-related events
    SYSTEM = "system"  # System-level events
    APPLICATION = "application"  # Application-level messages


class SdlLogger:
    """Central logging facility for PySDL framework.

    Provides static methods for logging various types of events in the
    PySDL system including process creation, state transitions, signal
    deliveries, and custom application messages.

    The logger supports:
    - Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Category-based logging to enable/disable specific event types
    - Lazy evaluation to minimize performance impact when logging is disabled
    - Environment variable configuration for easy deployment settings

    All methods are static and thread-safe. The logger is preconfigured
    with sensible defaults but can be customized via configure() method
    or environment variables.

    Attributes:
        _logger: Internal Python logger instance.
        _configured: Whether the logger has been explicitly configured.
        _enabled_categories: Set of enabled log categories.
        _min_level: Minimum log level to output.
    """

    # Initialize logging infrastructure
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(message)s {%(filename)s:%(lineno)d} ",
        level=logging.DEBUG,
    )

    _logger: logging.Logger = logging.getLogger("pysdl")
    _configured: bool = False
    _enabled_categories: dict[LogCategory, bool] = {
        LogCategory.SIGNALS: True,
        LogCategory.STATES: True,
        LogCategory.PROCESSES: True,
        LogCategory.TIMERS: True,
        LogCategory.SYSTEM: True,
        LogCategory.APPLICATION: True,
    }
    _min_level: int = logging.DEBUG

    @classmethod
    def configure(
        cls,
        level: str | None = None,
        categories: dict[str, bool] | None = None,
        reset: bool = False,
    ) -> None:
        """Configure the logger with desired settings.

        This method allows fine-grained control over logging behavior including
        log level and which categories of events to log.

        Args:
            level: Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                If None, uses current level or environment variable SDL_LOG_LEVEL.
            categories: Dictionary mapping category names to enabled status.
                Category names: "signals", "states", "processes", "timers",
                "system", "application".
                If None, all categories remain at current settings.
            reset: If True, reset to default configuration before applying settings.

        Example:
            >>> # Set log level to INFO and enable only signal and state logging
            >>> SdlLogger.configure(
            ...     level="INFO",
            ...     categories={"signals": True, "states": True, "processes": False}
            ... )

            >>> # Disable all logging by setting high threshold
            >>> SdlLogger.configure(level="CRITICAL")

            >>> # Reset to defaults
            >>> SdlLogger.configure(reset=True)

        Environment Variables:
            SDL_LOG_LEVEL: Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            SDL_LOG_CATEGORIES: Comma-separated list of categories to enable
                (e.g., "signals,states"). If set, unlisted categories are disabled.
        """
        if reset:
            # Reset to defaults
            cls._enabled_categories = {
                LogCategory.SIGNALS: True,
                LogCategory.STATES: True,
                LogCategory.PROCESSES: True,
                LogCategory.TIMERS: True,
                LogCategory.SYSTEM: True,
                LogCategory.APPLICATION: True,
            }
            cls._min_level = logging.DEBUG
            cls._logger.setLevel(logging.DEBUG)

        # Apply environment variable configuration first
        env_level = os.getenv("SDL_LOG_LEVEL")
        if env_level:
            level = env_level

        env_categories = os.getenv("SDL_LOG_CATEGORIES")
        if env_categories and not categories:
            # Parse comma-separated list
            category_list = [c.strip().lower() for c in env_categories.split(",")]
            categories = {}
            # Disable all categories first
            for cat in LogCategory:
                categories[cat.value] = False
            # Enable only specified categories
            for cat_name in category_list:
                categories[cat_name] = True

        # Set log level
        if level:
            level_upper = level.upper()
            if hasattr(logging, level_upper):
                cls._min_level = getattr(logging, level_upper)
                cls._logger.setLevel(cls._min_level)
            else:
                cls._logger.warning(f"Invalid log level: {level}. Using current level.")

        # Set category configuration
        if categories:
            for category_name, enabled in categories.items():
                try:
                    category = LogCategory(category_name.lower())
                    cls._enabled_categories[category] = enabled
                except ValueError:
                    cls._logger.warning(f"Invalid log category: {category_name}")

        cls._configured = True

    @classmethod
    def is_enabled(cls, category: LogCategory, level: int = logging.DEBUG) -> bool:
        """Check if logging is enabled for a given category and level.

        This method provides fast checking to avoid expensive log formatting
        operations when logging is disabled.

        Args:
            category: The log category to check.
            level: The log level to check (default: DEBUG).

        Returns:
            True if logging is enabled for this category and level, False otherwise.

        Example:
            >>> if SdlLogger.is_enabled(LogCategory.SIGNALS):
            ...     # Perform expensive formatting only if needed
            ...     expensive_data = format_complex_object()
            ...     SdlLogger.debug(expensive_data)
        """
        # Auto-configure from environment on first use if not explicitly configured
        if not cls._configured:
            cls.configure()

        return cls._enabled_categories.get(
            category, False
        ) and cls._logger.isEnabledFor(level)

    @classmethod
    def get_configuration(cls) -> dict[str, Any]:
        """Get current logger configuration.

        Returns:
            Dictionary containing current log level and enabled categories.

        Example:
            >>> config = SdlLogger.get_configuration()
            >>> print(f"Log level: {config['level']}")
            >>> print(f"Enabled categories: {config['categories']}")
        """
        return {
            "level": logging.getLevelName(cls._min_level),
            "categories": {
                cat.value: enabled for cat, enabled in cls._enabled_categories.items()
            },
        }

    @classmethod
    def info(cls, msg: str) -> None:
        """Log an informational message.

        Args:
            msg: Message to log.

        Example:
            >>> SdlLogger.info("System initialized successfully")
        """
        if cls._logger.isEnabledFor(logging.INFO):
            cls._logger.info(msg)

    @classmethod
    def debug(cls, msg: str) -> None:
        """Log a debug message.

        Args:
            msg: Debug message to log.

        Example:
            >>> SdlLogger.debug("Processing signal queue")
        """
        if cls._logger.isEnabledFor(logging.DEBUG):
            cls._logger.debug(msg)

    @classmethod
    def warning(cls, msg: str) -> None:
        """Log a warning message.

        Args:
            msg: Warning message to log.

        Example:
            >>> SdlLogger.warning("No handler found for signal")
        """
        if cls._logger.isEnabledFor(logging.WARNING):
            cls._logger.warning(msg)

    @classmethod
    def error(cls, msg: str) -> None:
        """Log an error message.

        Args:
            msg: Error message to log.

        Example:
            >>> SdlLogger.error("Failed to process signal")
        """
        if cls._logger.isEnabledFor(logging.ERROR):
            cls._logger.error(msg)

    @classmethod
    def signal(cls, sig_type: str, signal: SdlSignal, process: SdlProcess) -> None:
        """Log a signal event.

        Logs signal delivery or non-delivery events in a formatted table
        including signal type, process state, source, and destination.

        This method uses lazy evaluation - if signal logging is disabled,
        no formatting operations are performed.

        Args:
            sig_type: Type of signal event ("SdlSig" for delivery,
                "SdlSig-NA" for non-delivery).
            signal: The signal being logged.
            process: The target process.

        Example:
            >>> SdlLogger.signal("SdlSig", my_signal, target_process)
        """
        if not cls.is_enabled(LogCategory.SIGNALS):
            return

        # Lazy evaluation: only format if logging is enabled
        signame_num = f"{signal.name()}({signal.id()})"
        cls.debug(
            f"|{sig_type:<10} |{signame_num:<42} |{process.current_state():<40} |{signal.dst():<40} |{signal.src():<40} |{signal.dumpdata()}"
        )

    @classmethod
    def event(cls, event: str, process: SdlProcess, dst: str, src: str) -> None:
        """Log a process event.

        Logs generic process events like creation or stopping.

        This method uses lazy evaluation - if process logging is disabled,
        no formatting operations are performed.

        Args:
            event: Event type name.
            process: The process involved in the event.
            dst: Destination PID.
            src: Source PID.

        Example:
            >>> SdlLogger.event("Stopped", process, process.pid(), parent_pid)
        """
        if not cls.is_enabled(LogCategory.PROCESSES):
            return

        cls.debug(
            f"|{event:<10} |{'':<42} |{process.current_state():<40} |{dst:<40} |{src:<40}"
        )

    @classmethod
    def app(cls, process: SdlProcess, msg: str) -> None:
        """Log an application-level message for a process.

        This method uses lazy evaluation - if application logging is disabled,
        no formatting operations are performed.

        Args:
            process: The process logging the message.
            msg: Application message to log.

        Example:
            >>> SdlLogger.app(self, "Work item processed successfully")
        """
        if not cls.is_enabled(LogCategory.APPLICATION):
            return

        cls.debug(
            f"|{'SdlApp':<10} |{'app':<42} |{process.current_state():<40} |{process.name():<40} |{msg}"
        )

    @classmethod
    def create(cls, process: SdlProcess, parent_pid: str | None) -> None:
        """Log process creation.

        This method uses lazy evaluation - if process logging is disabled,
        no formatting operations are performed.

        Args:
            process: The newly created process.
            parent_pid: PID of the parent process, or None for root processes.

        Example:
            >>> SdlLogger.create(new_process, parent_process.pid())
        """
        if not cls.is_enabled(LogCategory.PROCESSES):
            return

        parent_str = parent_pid if parent_pid is not None else "None"
        cls.debug(
            f"|{'Created':<10} |{'create':<42} |{process.pid():<40} |{parent_str:<40} |"
        )

    @classmethod
    def state(
        cls, process: SdlProcess, current_state: SdlState, new_state: SdlState
    ) -> None:
        """Log a state transition.

        This method uses lazy evaluation - if state logging is disabled,
        no formatting operations are performed.

        Args:
            process: The process changing states.
            current_state: The previous state.
            new_state: The new state being transitioned to.

        Example:
            >>> SdlLogger.state(self, self.state_idle, self.state_active)
        """
        if not cls.is_enabled(LogCategory.STATES):
            return

        cls.debug(
            f"|{'SdlState':<10} |{'newstate':<42} |{new_state:<40} |{current_state:<40} |{process.pid():<40}"
        )
