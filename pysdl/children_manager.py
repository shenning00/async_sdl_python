"""Child process management for PySDL framework.

This module provides the SdlChildrenManager class for managing parent-child
relationships between processes. It supports registering children with metadata,
filtering by attributes, and maintaining process hierarchies.

Example:
    Managing child processes::

        from pysdl.children_manager import SdlChildrenManager

        # Create manager
        manager = SdlChildrenManager()

        # Register child with metadata
        manager.register(child_process, role="worker", priority=1)

        # Find child by PID
        child = manager.get_by_pid(child_pid)

        # Find children by attributes
        workers = manager.get_child_list_with_keys(role="worker")
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pysdl.process import SdlProcess


class SdlChildrenManager:
    """Manages child processes with metadata-based filtering.

    Tracks child processes along with arbitrary metadata keys, enabling
    filtering and retrieval by PID or metadata attributes. Each child is
    stored as a dictionary with 'process', 'pid', and 'keys' fields.

    Attributes:
        _children: Internal list of child process dictionaries.
    """

    _children: list[dict[str, Any]]

    def __init__(self) -> None:
        """Initialize an empty children manager."""
        self._children = []

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate over all children.

        Yields:
            Child dictionaries containing 'process', 'pid', and 'keys'.
        """
        return iter(self._children)

    def register(self, child_process: SdlProcess, **kwargs: Any) -> SdlProcess:
        """Register a child process with optional metadata.

        Args:
            child_process: The child process to register.
            **kwargs: Arbitrary metadata keys to associate with the child.

        Returns:
            The registered child process.
        """
        self._children.append(
            {
                "process": child_process,
                "pid": child_process.pid(),
                "keys": kwargs,
            }
        )
        return child_process

    def set_keys_by_pid(self, pid: str, **kwargs: Any) -> bool:
        """Update metadata keys for a child identified by PID.

        Args:
            pid: Process ID of the child to update.
            **kwargs: Key-value pairs to add/update in the child's metadata.

        Returns:
            True if child was found and updated, False otherwise.
        """
        for index, child in enumerate(self._children):
            if child["pid"] == pid:
                self._children[index]["keys"].update(kwargs)
                return True
        return False

    def get_keys_by_pid(self, pid: str) -> dict[str, Any] | None:
        """Retrieve metadata keys for a child identified by PID.

        Args:
            pid: Process ID of the child.

        Returns:
            Dictionary of metadata keys, or None if child not found.
        """
        for child in self._children:
            if child["pid"] == pid:
                keys: dict[str, Any] = child["keys"]
                return keys
        return None

    def get_child_list(self) -> list[dict[str, Any]]:
        """Get a copy of all registered children.

        Returns:
            List of all child dictionaries (shallow copy).
        """
        return list(self._children)

    def add_to_front(self, child_process: SdlProcess, **kwargs: Any) -> None:
        """Register a child at the front of the list.

        Useful for priority ordering when iterating through children.

        Args:
            child_process: The child process to register.
            **kwargs: Arbitrary metadata keys to associate with the child.
        """
        self._children.insert(
            0,
            {
                "process": child_process,
                "pid": child_process.pid(),
                "keys": kwargs,
            },
        )

    def get_first_child_with_keys(self, **kwargs: Any) -> dict[str, Any] | None:
        """Find first child matching all specified metadata keys.

        Args:
            **kwargs: Key-value pairs that must all match the child's metadata.

        Returns:
            First matching child dictionary, or None if no match found.
        """
        for child in self._children:
            if self._check_keys_match(child, kwargs):
                return child
        return None

    def get_child_list_with_keys(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Find all children matching specified metadata keys.

        Args:
            **kwargs: Key-value pairs that must all match a child's metadata.

        Returns:
            List of all matching child dictionaries (may be empty).
        """
        return [
            child for child in self._children if self._check_keys_match(child, kwargs)
        ]

    def get_by_pid(self, pid: str) -> dict[str, Any] | None:
        """Retrieve a child by its process ID.

        Args:
            pid: Process ID to search for.

        Returns:
            Child dictionary if found, None otherwise.
        """
        for child in self._children:
            if child["pid"] == pid:
                return child
        return None

    def get_count(self) -> int:
        """Get the total number of registered children.

        Returns:
            Count of children.
        """
        return len(self._children)

    def unregister_by_keys(self, **kwargs: Any) -> None:
        """Unregister first child matching specified metadata keys.

        Args:
            **kwargs: Key-value pairs identifying the child to remove.
        """
        for index, child in enumerate(self._children):
            if self._check_keys_match(child, kwargs):
                del self._children[index]
                return

    def _check_keys_match(self, child: dict[str, Any], kwargs: dict[str, Any]) -> bool:
        """Check if a child's metadata matches all specified keys.

        Args:
            child: Child dictionary to check.
            kwargs: Key-value pairs to match against child's keys.

        Returns:
            True if all kwargs match the child's keys, False otherwise.
        """
        for key, value in kwargs.items():
            if key not in child["keys"] or child["keys"][key] != value:
                return False
        return True
