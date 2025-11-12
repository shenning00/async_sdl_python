"""Comprehensive tests for system_signals module.

This test module provides complete coverage for all system signal classes
including their __str__ methods which were previously untested.

Coverage focus:
- SdlStartSignal.__str__() (lines 63-65)
- SdlStoppingSignal.__str__() (lines 87-89)
- SdlStopSignal.__str__() (lines 100-102)
- SdlStarSignal.__str__() (lines 132-134)
"""

from pysdl.system_signals import (
    SdlProcessNotExistSignal,
    SdlStarSignal,
    SdlStartSignal,
    SdlStoppingSignal,
    SdlStopSignal,
)


class TestSdlStartSignal:
    """Test SdlStartSignal class."""

    def test_start_signal_creation(self):
        """Test creating a SdlStartSignal instance."""
        signal = SdlStartSignal.create()
        assert signal is not None
        assert isinstance(signal, SdlStartSignal)

    def test_start_signal_str_format(self):
        """Test __str__ method returns formatted string with brackets."""
        signal = SdlStartSignal.create()
        result = str(signal)

        # Should be wrapped in brackets: [SdlStartSignal(...)]
        assert result.startswith("[")
        assert result.endswith("]")
        assert "SdlStartSignal" in result

    def test_start_signal_str_contains_base_representation(self):
        """Test __str__ includes base class representation."""
        signal = SdlStartSignal.create()
        result = str(signal)

        # Should contain signal type name
        assert "SdlStartSignal" in result


class TestSdlStoppingSignal:
    """Test SdlStoppingSignal class."""

    def test_stopping_signal_creation(self):
        """Test creating a SdlStoppingSignal instance."""
        signal = SdlStoppingSignal.create()
        assert signal is not None
        assert isinstance(signal, SdlStoppingSignal)

    def test_stopping_signal_str_format(self):
        """Test __str__ method returns formatted string with brackets."""
        signal = SdlStoppingSignal.create()
        result = str(signal)

        # Should be wrapped in brackets: [SdlStoppingSignal(...)]
        assert result.startswith("[")
        assert result.endswith("]")
        assert "SdlStoppingSignal" in result

    def test_stopping_signal_str_contains_base_representation(self):
        """Test __str__ includes base class representation."""
        signal = SdlStoppingSignal.create()
        result = str(signal)

        # Should contain signal type name
        assert "SdlStoppingSignal" in result


class TestSdlStopSignal:
    """Test SdlStopSignal class (reserved for future use)."""

    def test_stop_signal_creation(self):
        """Test creating a SdlStopSignal instance."""
        signal = SdlStopSignal.create()
        assert signal is not None
        assert isinstance(signal, SdlStopSignal)

    def test_stop_signal_str_format(self):
        """Test __str__ method returns formatted string with brackets."""
        signal = SdlStopSignal.create()
        result = str(signal)

        # Should be wrapped in brackets: [SdlStopSignal(...)]
        assert result.startswith("[")
        assert result.endswith("]")
        assert "SdlStopSignal" in result

    def test_stop_signal_str_contains_base_representation(self):
        """Test __str__ includes base class representation."""
        signal = SdlStopSignal.create()
        result = str(signal)

        # Should contain signal type name
        assert "SdlStopSignal" in result


class TestSdlStarSignal:
    """Test SdlStarSignal class for wildcard signal handling."""

    def test_star_signal_creation(self):
        """Test creating a SdlStarSignal instance."""
        signal = SdlStarSignal.create()
        assert signal is not None
        assert isinstance(signal, SdlStarSignal)

    def test_star_signal_str_format(self):
        """Test __str__ method returns formatted string with brackets."""
        signal = SdlStarSignal.create()
        result = str(signal)

        # Should be wrapped in brackets: [SdlStarSignal(...)]
        assert result.startswith("[")
        assert result.endswith("]")
        assert "SdlStarSignal" in result

    def test_star_signal_str_contains_base_representation(self):
        """Test __str__ includes base class representation."""
        signal = SdlStarSignal.create()
        result = str(signal)

        # Should contain signal type name
        assert "SdlStarSignal" in result


class TestSdlProcessNotExistSignal:
    """Test SdlProcessNotExistSignal error signal.

    Note: Basic functionality is covered in test_error_handling.py.
    This class adds comprehensive tests for edge cases and str representation.
    """

    def test_process_not_exist_signal_creation_with_all_params(self):
        """Test creating signal with all parameters."""
        signal = SdlProcessNotExistSignal(
            original_signal="TestSignal",
            destination="Process(1.0)",
            source="Sender(2.0)",
        )

        assert signal.get_data("original_signal") == "TestSignal"
        assert signal.get_data("destination") == "Process(1.0)"
        assert signal.get_data("source") == "Sender(2.0)"

    def test_process_not_exist_signal_creation_empty(self):
        """Test creating signal with default empty parameters."""
        signal = SdlProcessNotExistSignal()

        assert signal.get_data("original_signal") == ""
        assert signal.get_data("destination") == ""
        assert signal.get_data("source") == ""

    def test_process_not_exist_signal_str_format(self):
        """Test __str__ method includes all relevant information."""
        signal = SdlProcessNotExistSignal(
            original_signal="CustomSignal",
            destination="Target(5.0)",
            source="Origin(3.0)",
        )

        result = str(signal)

        # Should be wrapped in brackets
        assert result.startswith("[")
        assert result.endswith("]")

        # Should contain destination and signal info
        assert "dest=Target(5.0)" in result
        assert "signal=CustomSignal" in result

    def test_process_not_exist_signal_str_with_empty_data(self):
        """Test __str__ with empty string data values."""
        signal = SdlProcessNotExistSignal()
        result = str(signal)

        # Default empty strings are stored, so should show empty values
        # (get() with default "unknown" only applies if key is missing)
        assert "dest=" in result
        assert "signal=" in result

    def test_process_not_exist_signal_str_partial_data(self):
        """Test __str__ with partial data."""
        signal = SdlProcessNotExistSignal(
            destination="Partial(1.0)", original_signal=""
        )
        result = str(signal)

        # Should show known destination and empty signal (empty string was provided)
        assert "dest=Partial(1.0)" in result
        assert "signal=" in result

    def test_get_data_with_various_keys(self):
        """Test get_data method with different keys."""
        signal = SdlProcessNotExistSignal(
            original_signal="Signal1", destination="Dest1", source="Source1"
        )

        # Valid keys
        assert signal.get_data("original_signal") == "Signal1"
        assert signal.get_data("destination") == "Dest1"
        assert signal.get_data("source") == "Source1"

        # Invalid key returns empty string
        assert signal.get_data("invalid_key") == ""
        assert signal.get_data("") == ""


class TestSystemSignalsComparison:
    """Test comparison and behavior across all system signals."""

    def test_all_system_signals_are_distinct_types(self):
        """Test that all system signal classes are distinct types."""
        start_sig = SdlStartSignal.create()
        stopping_sig = SdlStoppingSignal.create()
        stop_sig = SdlStopSignal.create()
        star_sig = SdlStarSignal.create()
        not_exist_sig = SdlProcessNotExistSignal()

        # Each should be instance of only its own type
        assert type(start_sig) is not type(stopping_sig)
        assert type(start_sig) is not type(stop_sig)
        assert type(start_sig) is not type(star_sig)
        assert type(start_sig) is not type(not_exist_sig)

    def test_str_methods_are_all_implemented(self):
        """Test that all signal classes have working __str__ methods."""
        signals = [
            SdlStartSignal.create(),
            SdlStoppingSignal.create(),
            SdlStopSignal.create(),
            SdlStarSignal.create(),
            SdlProcessNotExistSignal(),
        ]

        for signal in signals:
            result = str(signal)
            # All should return non-empty strings
            assert result
            assert len(result) > 0
            # All should be wrapped in brackets
            assert result.startswith("[")
            assert result.endswith("]")
