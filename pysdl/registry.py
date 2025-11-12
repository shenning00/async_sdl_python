"""Name-based process registry for PySDL framework.

This module provides the SdlRegistry class for registering and looking up
processes by symbolic names rather than PIDs. This is useful for well-known
services that other processes need to locate.

Example:
    Registering and looking up processes::

        from pysdl.registry import SdlRegistry

        # Register a service
        SdlRegistry.register("database", db_process.pid())

        # Look up the service
        db_pid = SdlRegistry.whereis("database")
        if db_pid:
            await self.output(query, db_pid)
"""

from __future__ import annotations

from typing import Any


class SdlRegistry:
    """Singleton registry for mapping names to process IDs.

    Provides a global name-to-PID mapping for locating well-known services
    and processes by symbolic name. The registry is implemented as a singleton
    to ensure all processes share the same registry.

    Typical use cases:
        - Registering singleton services (database, logger, config)
        - Looking up well-known processes by name
        - Service discovery

    Class Attributes:
        _instance: Singleton instance (private class variable).
        _registry: Internal name-to-value mapping (private class variable).

    Note:
        This class uses instance methods but maintains singleton state through
        class variables. The __new__ pattern ensures only one instance exists.
        For consistency with logger/id_generator patterns in this codebase,
        consider using class methods instead of instance methods.
    """

    # Class variables (use single underscore for consistency with logger/id_generator)
    _instance: SdlRegistry | None = None
    _registry: dict[str, Any] = {}

    def __new__(cls) -> SdlRegistry:
        """Create or return the singleton instance.

        Returns:
            The singleton SdlRegistry instance.
        """
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def add(self, key: str, value: Any) -> None:
        """Add or update a key-value pair in the registry.

        Args:
            key: The name to register.
            value: The value to associate with the name (typically a PID).

        Example:
            >>> registry = SdlRegistry()
            >>> registry.add("database", "DbProcess(1.0)")
        """
        self._registry[key] = value

    def get(self, key: str) -> Any:
        """Retrieve a value from the registry.

        Args:
            key: The name to look up.

        Returns:
            The value associated with the key.

        Raises:
            KeyError: If the key is not found in the registry.

        Example:
            >>> registry = SdlRegistry()
            >>> registry.add("database", "DbProcess(1.0)")
            >>> pid = registry.get("database")
        """
        return self._registry[key]
