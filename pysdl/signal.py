"""signal.py."""

from __future__ import annotations

from typing import Any, TypeVar

from pysdl.id_generator import SdlIdGenerator

T = TypeVar("T", bound="SdlSignal")


class SdlSignal:
    """Base SDL signal class.

    Provides the foundation for all SDL signals with unique IDs, routing
    information (source/destination), and optional data payload.

    Signals are created using the create() class method and are used to
    communicate between processes in the SDL system.

    Class Attributes:
        _id: Unique ID for this signal class (shared across instances).

    Note:
        The 'data' attribute provides direct access to _data for backward
        compatibility. New code should prefer property-based access patterns.
    """

    # Class variable (shared across all instances of this signal type)
    _id: int | None = None

    @classmethod
    def id(cls) -> int:
        """Get the unique ID for this signal class.

        Returns:
            The unique integer ID for this signal class.

        Note:
            The ID is assigned lazily on first access and cached for all
            instances of this signal class.
        """
        if cls._id is None:
            cls._id = SdlIdGenerator.next()
        return cls._id

    @classmethod
    def create(cls: type[T], _data: Any | None = None) -> T:
        """Create a new signal instance.

        Args:
            _data: Optional data payload for the signal.

        Returns:
            A new signal instance with the class ID assigned.

        Example:
            >>> signal = SdlSignal.create({"key": "value"})
            >>> print(signal.data)
            {'key': 'value'}
        """
        signal = cls(_data)
        signal._id = signal.id()
        return signal

    def __init__(self, _data: Any | None = None) -> None:
        """Initialize a signal instance.

        Args:
            _data: Optional data payload for the signal.

        Note:
            Instance variables initialized here:
            - _name: Signal class name
            - _src: Source process ID (set when sending)
            - _dst: Destination process ID (set when sending)
            - _data: Data payload
        """
        self._name: str = self.__class__.__name__
        self._src: str | None = None
        self._dst: str | None = None
        self._data: Any | None = _data

    @property
    def data(self) -> Any | None:
        """Get the signal's data payload.

        Returns:
            The data payload or None.
        """
        return self._data

    @data.setter
    def data(self, value: Any | None) -> None:
        """Set the signal's data payload.

        Args:
            value: The data payload to set.
        """
        self._data = value

    def __str__(self) -> str:
        """Return string representation of the signal.

        Returns:
            String containing signal name, ID, source, and destination.
        """
        return f"name: {self.name()} id: {self.id()} [src: {self.src()}] [dst: {self.dst()}]"

    def dumpdata(self) -> str | None:
        """Return pretty-printed data payload.

        Override this method in subclasses to provide custom formatting
        of the data payload for logging purposes.

        Returns:
            String representation of data, or None for no output.

        Example:
            >>> class MySignal(SdlSignal):
            ...     def dumpdata(self) -> str:
            ...         return f"Count: {self.data}"
        """
        return None

    def name(self) -> str:
        """Get the signal name.

        Returns:
            The signal class name.
        """
        return self._name

    def set_name(self, _name: str) -> None:
        """Set the signal name.

        Args:
            _name: The new signal name.

        Note:
            Typically not needed as name defaults to class name.
        """
        self._name = _name

    def src(self) -> str | None:
        """Get the source process ID.

        Returns:
            The source PID or None if not set.
        """
        return self._src

    def set_src(self, _src: str) -> None:
        """Set the source process ID.

        Args:
            _src: The source process ID.

        Note:
            This is typically set automatically by the system when
            sending signals via process.output().
        """
        self._src = _src

    def dst(self) -> str | None:
        """Get the destination process ID.

        Returns:
            The destination PID or None if not set.
        """
        return self._dst

    def set_dst(self, _dst: str) -> None:
        """Set the destination process ID.

        Args:
            _dst: The destination process ID.

        Note:
            This is typically set automatically by the system when
            sending signals via process.output().
        """
        self._dst = _dst
