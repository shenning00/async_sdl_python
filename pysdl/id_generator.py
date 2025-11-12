"""Unique ID generation for PySDL framework.

This module provides the SdlIdGenerator class for generating unique integer
identifiers used by signals and processes. IDs are sequential starting from 0
and are unique within a single execution session.

Example:
    Generating unique IDs::

        from pysdl.id_generator import SdlIdGenerator

        id1 = SdlIdGenerator.next()  # Returns 1
        id2 = SdlIdGenerator.next()  # Returns 2
"""

from __future__ import annotations


class SdlIdGenerator:
    """Generator for unique sequential integer IDs.

    Provides class methods to generate unique IDs for signals and process
    classes. IDs are sequential integers starting from 0. Each call to next()
    increments the counter and returns a new unique ID.

    This class should not be instantiated; use the class methods directly.

    Attributes:
        _id: Internal counter for ID generation (class variable).
    """

    _id: int = 0

    @classmethod
    def id(cls) -> int:
        """Get the current ID without incrementing.

        Returns:
            The current ID value.

        Example:
            >>> current = SdlIdGenerator.id()
            >>> print(current)
            0
        """
        return cls._id

    @classmethod
    def next(cls) -> int:
        """Generate and return the next unique ID.

        Increments the internal counter and returns the new value.
        IDs are sequential starting from 1.

        Returns:
            A unique integer ID.

        Example:
            >>> id1 = SdlIdGenerator.next()  # Returns 1
            >>> id2 = SdlIdGenerator.next()  # Returns 2
            >>> id3 = SdlIdGenerator.next()  # Returns 3
        """
        cls._id += 1
        return cls._id
