"""Test suite for SdlIdGenerator.

This module tests the ID generation functionality for signals, processes, and other SDL components.
"""

import pytest

from pysdl import SdlIdGenerator


class TestSdlIdGenerator:
    """Test cases for SdlIdGenerator class."""

    @pytest.fixture(autouse=True)
    def reset_id_generator(self) -> None:
        """Reset the ID generator state before each test.

        This ensures tests are isolated and don't depend on execution order.
        """
        SdlIdGenerator._id = 0

    def test_initial_id_is_zero(self) -> None:
        """Test that the initial ID is 0."""
        tid = SdlIdGenerator.id()
        assert tid == 0

    def test_next_increments_id(self) -> None:
        """Test that next() increments and returns the new ID."""
        tid = SdlIdGenerator.next()
        assert tid == 1

    def test_id_returns_current_after_next(self) -> None:
        """Test that id() returns the current ID after calling next()."""
        SdlIdGenerator.next()
        tid = SdlIdGenerator.id()
        assert tid == 1

    def test_multiple_next_calls(self) -> None:
        """Test multiple consecutive next() calls."""
        assert SdlIdGenerator.next() == 1
        assert SdlIdGenerator.next() == 2
        assert SdlIdGenerator.next() == 3
        assert SdlIdGenerator.id() == 3

    def test_id_does_not_increment(self) -> None:
        """Test that id() does not increment the counter."""
        SdlIdGenerator.next()  # Set to 1
        assert SdlIdGenerator.id() == 1
        assert SdlIdGenerator.id() == 1
        assert SdlIdGenerator.id() == 1

    def test_instantiation_allowed(self) -> None:
        """Test that the class can be instantiated without errors.

        While the class is designed to be used via static methods,
        instantiation should not raise an exception.
        """
        instance = SdlIdGenerator()
        assert instance is not None
