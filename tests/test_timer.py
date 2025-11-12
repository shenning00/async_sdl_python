"""Test suite for SdlTimer.

This module tests timer creation, expiry calculation, timer cancellation, and multiple timers.
"""

from typing import Optional

import pytest

from pysdl.id_generator import SdlIdGenerator
from pysdl.timer import SdlTimer


class TestSdlTimer:
    """Test cases for SdlTimer class."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> None:
        """Reset state before each test."""
        SdlIdGenerator._id = 0

    def test_timer_creation(self) -> None:
        """Test basic timer creation."""
        timer = SdlTimer.create()
        assert timer is not None
        assert isinstance(timer, SdlTimer)

    def test_timer_inherits_from_signal(self) -> None:
        """Test that timer inherits from SdlSignal."""
        from pysdl.signal import SdlSignal

        timer = SdlTimer.create()
        assert isinstance(timer, SdlSignal)

    def test_timer_id_assignment(self) -> None:
        """Test that timers get unique IDs."""

        class Timer1(SdlTimer):
            _id: Optional[int] = None

        class Timer2(SdlTimer):
            _id: Optional[int] = None

        timer1 = Timer1.create()
        timer2 = Timer2.create()

        # Different timer types should have different IDs
        assert timer1.id() != timer2.id()

    def test_timer_initial_values(self) -> None:
        """Test timer initial values."""
        timer = SdlTimer.create()
        assert timer.appcorr() == 0
        assert timer._duration == 0
        assert timer._expiry == 0
        assert timer.data is None

    def test_timer_with_data(self) -> None:
        """Test timer creation with data."""
        test_data = {"timeout_type": "shutdown"}
        timer = SdlTimer.create(test_data)
        assert timer.data == test_data

    def test_timer_set_appcorr(self) -> None:
        """Test setting timer application correlator."""
        timer = SdlTimer.create()
        timer.set_appcorr(42)
        assert timer.appcorr() == 42

    def test_timer_start(self) -> None:
        """Test starting a timer."""
        timer = SdlTimer.create()
        timer.start(5000)  # 5 seconds in ms
        assert timer._duration == 5000
        assert timer._expiry == 0

    def test_timer_expired_before_time(self) -> None:
        """Test timer not expired before expiry time."""
        timer = SdlTimer.create()
        timer.start(5000)  # Duration: 5000ms
        timer.expire(3000)  # Current time: 3000ms
        assert timer.expired() is False

    def test_timer_expired_at_expiry_time(self) -> None:
        """Test timer expired at exactly expiry time."""
        timer = SdlTimer.create()
        timer.start(5000)  # Duration: 5000ms
        timer.expire(5000)  # Current time: 5000ms
        assert timer.expired() is True

    def test_timer_expired_after_expiry_time(self) -> None:
        """Test timer expired after expiry time."""
        timer = SdlTimer.create()
        timer.start(5000)  # Duration: 5000ms
        timer.expire(6000)  # Current time: 6000ms
        assert timer.expired() is True

    def test_timer_not_expired_initially(self) -> None:
        """Test timer is not expired after being started but before time passes."""
        timer = SdlTimer.create()
        timer.start(5000)  # Start with 5000ms duration
        # At this point, _duration=5000 and _expiry=0, so 0 >= 5000 is False
        assert timer.expired() is False

    def test_timer_expire_updates_expiry(self) -> None:
        """Test that expire() updates the expiry time."""
        timer = SdlTimer.create()
        timer.start(5000)
        timer.expire(3000)
        assert timer._expiry == 3000

    def test_timer_str_representation(self) -> None:
        """Test timer string representation includes appcorr."""
        timer = SdlTimer.create()
        timer.set_appcorr(123)
        str_repr = str(timer)
        assert "appcorr: 123" in str_repr

    def test_timer_dumpdata(self) -> None:
        """Test timer dumpdata method."""
        timer = SdlTimer.create()
        timer.set_appcorr(456)
        assert timer.dumpdata() == "appcorr: 456"

    def test_timer_src_dst_handling(self) -> None:
        """Test timer source and destination handling."""
        timer = SdlTimer.create()
        timer.set_src("Process(0.0)")
        timer.set_dst("Process(0.0)")
        assert timer.src() == "Process(0.0)"
        assert timer.dst() == "Process(0.0)"

    def test_timer_equality_same_id_same_appcorr(self) -> None:
        """Test timer equality with same ID and appcorr."""

        class TestTimer(SdlTimer):
            pass

        timer1 = TestTimer.create()
        timer2 = TestTimer.create()
        timer1.set_appcorr(10)
        timer2.set_appcorr(10)

        assert timer1 == timer2

    def test_timer_inequality_different_id(self) -> None:
        """Test timer inequality with different IDs."""

        class Timer1(SdlTimer):
            _id: Optional[int] = None

        class Timer2(SdlTimer):
            _id: Optional[int] = None

        timer1 = Timer1.create()
        timer2 = Timer2.create()

        assert timer1 != timer2

    def test_timer_inequality_different_appcorr(self) -> None:
        """Test timer inequality with different appcorr."""

        class TestTimer(SdlTimer):
            pass

        timer1 = TestTimer.create()
        timer2 = TestTimer.create()
        timer1.set_appcorr(10)
        timer2.set_appcorr(20)

        # Note: Based on the _compare implementation, different appcorr
        # should make them not equal
        assert timer1 != timer2

    def test_timer_less_than_by_id(self) -> None:
        """Test timer comparison by ID."""

        class Timer1(SdlTimer):
            _id: Optional[int] = None

        class Timer2(SdlTimer):
            _id: Optional[int] = None

        timer1 = Timer1.create()
        timer2 = Timer2.create()

        # Timer1 should have lower ID (created first)
        assert timer1 < timer2

    def test_timer_greater_than_by_id(self) -> None:
        """Test timer greater than comparison by ID."""

        class Timer1(SdlTimer):
            _id: Optional[int] = None

        class Timer2(SdlTimer):
            _id: Optional[int] = None

        timer1 = Timer1.create()
        timer2 = Timer2.create()

        # Timer2 should have higher ID (created second)
        assert timer2 > timer1

    def test_timer_less_than_equal(self) -> None:
        """Test timer less than or equal comparison."""

        class TestTimer(SdlTimer):
            pass

        timer1 = TestTimer.create()
        timer2 = TestTimer.create()
        timer1.set_appcorr(10)
        timer2.set_appcorr(10)

        assert timer1 <= timer2

    def test_timer_greater_than_equal(self) -> None:
        """Test timer greater than or equal comparison."""

        class TestTimer(SdlTimer):
            pass

        timer1 = TestTimer.create()
        timer2 = TestTimer.create()
        timer1.set_appcorr(10)
        timer2.set_appcorr(10)

        assert timer1 >= timer2

    def test_timer_restart(self) -> None:
        """Test restarting a timer resets expiry."""
        timer = SdlTimer.create()
        timer.start(5000)
        timer.expire(3000)
        assert timer._expiry == 3000

        # Restart the timer
        timer.start(10000)
        assert timer._duration == 10000
        assert timer._expiry == 0  # Expiry should be reset

    def test_multiple_timers_independent(self) -> None:
        """Test that multiple timers are independent."""
        timer1 = SdlTimer.create()
        timer2 = SdlTimer.create()

        timer1.start(5000)
        timer2.start(10000)

        timer1.expire(6000)
        timer2.expire(8000)

        assert timer1.expired() is True
        assert timer2.expired() is False

    def test_timer_with_zero_duration(self) -> None:
        """Test timer with zero duration expires immediately."""
        timer = SdlTimer.create()
        timer.start(0)
        timer.expire(0)
        assert timer.expired() is True

    def test_timer_with_large_duration(self) -> None:
        """Test timer with large duration."""
        timer = SdlTimer.create()
        large_duration = 1000000000  # Very large number
        timer.start(large_duration)
        timer.expire(500000000)
        assert timer.expired() is False
        timer.expire(large_duration)
        assert timer.expired() is True

    def test_timer_equality_with_non_timer_returns_not_implemented(self) -> None:
        """Test timer equality comparison with non-SdlTimer types returns NotImplemented."""
        timer = SdlTimer.create()

        # Test with various non-SdlTimer types
        assert timer.__eq__(42) is NotImplemented
        assert timer.__eq__("string") is NotImplemented
        assert timer.__eq__(None) is NotImplemented
        assert timer.__eq__([1, 2, 3]) is NotImplemented
        assert timer.__eq__({"key": "value"}) is NotImplemented

    def test_timer_inequality_with_non_timer_returns_not_implemented(self) -> None:
        """Test timer inequality comparison with non-SdlTimer types returns NotImplemented."""
        timer = SdlTimer.create()

        # Test with various non-SdlTimer types
        assert timer.__ne__(42) is NotImplemented
        assert timer.__ne__("string") is NotImplemented
        assert timer.__ne__(None) is NotImplemented
        assert timer.__ne__([1, 2, 3]) is NotImplemented
        assert timer.__ne__({"key": "value"}) is NotImplemented
