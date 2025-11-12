"""Timer implementation for PySDL framework.

This module provides timer functionality for scheduling delayed signal delivery.
Timers inherit from SdlSignal and are delivered to processes when they expire.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pysdl.id_generator import SdlIdGenerator
from pysdl.signal import SdlSignal

T = TypeVar("T", bound="SdlTimer")


class SdlTimer(SdlSignal):
    """SDL timer class.

    Extends SdlSignal to provide timer functionality with expiration tracking.
    Timers are scheduled with the system and delivered as signals when they expire.

    Attributes:
        _id: Unique class-level timer ID (inherited from SdlSignal).
        _appcorr: Application correlator for distinguishing timer instances.
        _duration: Timer duration in milliseconds.
        _expiry: Expiry timestamp in milliseconds.
        data: Optional data payload carried by the timer signal.
    """

    _id: int | None = None
    _appcorr: int
    _duration: int
    _expiry: int

    @classmethod
    def id(cls) -> int:
        if cls._id is None:
            cls._id = SdlIdGenerator.next()
        return cls._id

    @classmethod
    def create(cls: type[T], _data: Any | None = None) -> T:
        signal = cls(_data)
        signal._id = signal.id()
        return signal

    def __init__(self, _data: Any | None = None) -> None:
        super().__init__()
        self._appcorr = 0
        self._duration = 0
        self._expiry = 0
        self.data = _data

    def __str__(self) -> str:
        base = super().__str__()
        return f"[{base} appcorr: {self._appcorr}]"

    def dumpdata(self) -> str:
        """Return pretty-printed timer data.

        Returns:
            String containing the application correlator value.
        """
        return f"appcorr: {self._appcorr}"

    def __eq__(self, rhs: object) -> bool:
        if not isinstance(rhs, SdlTimer):
            return NotImplemented
        return self._compare(rhs) == 0

    def __ne__(self, rhs: object) -> bool:
        if not isinstance(rhs, SdlTimer):
            return NotImplemented
        return self._compare(rhs) != 0

    def __lt__(self, rhs: SdlTimer) -> bool:
        return self._compare(rhs) < 0

    def __le__(self, rhs: SdlTimer) -> bool:
        return self._compare(rhs) <= 0

    def __gt__(self, rhs: SdlTimer) -> bool:
        return self._compare(rhs) > 0

    def __ge__(self, rhs: SdlTimer) -> bool:
        return self._compare(rhs) >= 0

    def appcorr(self) -> int:
        """Get the application correlator.

        Returns:
            The application correlator value.
        """
        return self._appcorr

    def set_appcorr(self, _appcorr: int) -> None:
        """Set the application correlator.

        Args:
            _appcorr: The application correlator value to set.
        """
        self._appcorr = _appcorr

    def start(self, msec: int) -> None:
        """Start the timer with specified duration.

        Args:
            msec: Duration in milliseconds.
        """
        self._duration = msec
        self._expiry = 0

    def expired(self) -> bool:
        """Check if the timer has expired.

        Returns:
            True if expired, False otherwise.
        """
        return self._expiry >= self._duration

    def expire(self, msec: int) -> None:
        """Update timer expiry with current time.

        Args:
            msec: Current time in milliseconds.
        """
        self._expiry = msec

    def _compare(self, rhs: SdlTimer) -> int:
        """Compare this timer with another for sorting.

        Args:
            rhs: The timer to compare with.

        Returns:
            -1 if self < rhs, 1 if self > rhs, 0 if equal.

        Note:
            Comparison is based on timer ID and application correlator.
        """
        if self.id() < rhs.id():
            return -1
        if self.id() > rhs.id():
            return 1
        if self.appcorr() < rhs.appcorr():
            return -1
        if self.appcorr() > rhs.appcorr():
            return -1
        return 0
