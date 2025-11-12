"""Test suite for SdlSignal.

This module tests signal creation, source/destination handling, and signal routing.
"""

from typing import Optional

import pytest

from pysdl.id_generator import SdlIdGenerator
from pysdl.signal import SdlSignal


class TestSdlSignal:
    """Test cases for SdlSignal class."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> None:
        """Reset state before each test."""
        SdlIdGenerator._id = 0

    def test_signal_creation(self) -> None:
        """Test basic signal creation."""
        signal = SdlSignal.create()
        assert signal is not None
        assert isinstance(signal, SdlSignal)

    def test_signal_id_assignment(self) -> None:
        """Test that signals get unique IDs."""

        class TestSignal1(SdlSignal):
            _id: Optional[int] = None

        class TestSignal2(SdlSignal):
            _id: Optional[int] = None

        signal1 = TestSignal1.create()
        signal2 = TestSignal2.create()

        # Different signal types should have different IDs
        assert signal1.id() != signal2.id()

    def test_signal_class_id_is_cached(self) -> None:
        """Test that signal class ID is cached and consistent."""

        class TestSignal(SdlSignal):
            pass

        signal1 = TestSignal.create()
        signal2 = TestSignal.create()

        # Same signal type should have same ID
        assert signal1.id() == signal2.id()

    def test_signal_name(self) -> None:
        """Test signal name matches class name."""

        class MyCustomSignal(SdlSignal):
            pass

        signal = MyCustomSignal.create()
        assert signal.name() == "MyCustomSignal"

    def test_signal_set_name(self) -> None:
        """Test setting custom signal name."""
        signal = SdlSignal.create()
        signal.set_name("CustomName")
        assert signal.name() == "CustomName"

    def test_signal_src_dst_initial_none(self) -> None:
        """Test that src and dst are initially None."""
        signal = SdlSignal.create()
        assert signal.src() is None
        assert signal.dst() is None

    def test_signal_set_src(self) -> None:
        """Test setting signal source."""
        signal = SdlSignal.create()
        signal.set_src("TestProcess(0.0)")
        assert signal.src() == "TestProcess(0.0)"

    def test_signal_set_dst(self) -> None:
        """Test setting signal destination."""
        signal = SdlSignal.create()
        signal.set_dst("TargetProcess(1.0)")
        assert signal.dst() == "TargetProcess(1.0)"

    def test_signal_with_data(self) -> None:
        """Test signal creation with data payload."""
        test_data = {"key": "value", "count": 42}
        signal = SdlSignal.create(test_data)
        assert signal.data == test_data
        assert signal.data["key"] == "value"
        assert signal.data["count"] == 42

    def test_signal_without_data(self) -> None:
        """Test signal creation without data."""
        signal = SdlSignal.create()
        assert signal.data is None

    def test_signal_str_representation(self) -> None:
        """Test signal string representation."""

        class TestSignal(SdlSignal):
            pass

        signal = TestSignal.create()
        signal.set_src("Source(0.0)")
        signal.set_dst("Dest(1.0)")

        str_repr = str(signal)
        assert "TestSignal" in str_repr
        assert "Source(0.0)" in str_repr
        assert "Dest(1.0)" in str_repr

    def test_signal_dumpdata_default(self) -> None:
        """Test default dumpdata implementation."""
        signal = SdlSignal.create()
        assert signal.dumpdata() is None

    def test_custom_signal_with_dumpdata(self) -> None:
        """Test custom signal with overridden dumpdata."""

        class CustomSignal(SdlSignal):
            def dumpdata(self) -> str:
                return f"Custom data: {self.data}"

        signal = CustomSignal.create("test_value")
        assert signal.dumpdata() == "Custom data: test_value"

    def test_multiple_signal_types_unique_ids(self) -> None:
        """Test that multiple signal types get unique IDs."""

        class SignalA(SdlSignal):
            _id: Optional[int] = None

        class SignalB(SdlSignal):
            _id: Optional[int] = None

        class SignalC(SdlSignal):
            _id: Optional[int] = None

        sig_a = SignalA.create()
        sig_b = SignalB.create()
        sig_c = SignalC.create()

        ids = {sig_a.id(), sig_b.id(), sig_c.id()}
        assert len(ids) == 3  # All IDs should be unique

    def test_signal_data_types(self) -> None:
        """Test signals with various data types."""
        # String data
        sig1 = SdlSignal.create("string_data")
        assert sig1.data == "string_data"

        # Integer data
        sig2 = SdlSignal.create(42)
        assert sig2.data == 42

        # List data
        sig3 = SdlSignal.create([1, 2, 3])
        assert sig3.data == [1, 2, 3]

        # Dict data
        sig4 = SdlSignal.create({"a": 1, "b": 2})
        assert sig4.data == {"a": 1, "b": 2}
