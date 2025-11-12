"""Test suite for SdlState class.

This module tests the SdlState class methods including string representation,
formatting, id/name retrieval, and name modification.
"""

from pysdl.state import SdlState, star, start, wait


class TestSdlState:
    """Test cases for SdlState class."""

    def test_state_creation(self) -> None:
        """Test basic state creation."""
        state = SdlState("test_state")
        assert state is not None
        assert isinstance(state, SdlState)

    def test_state_name(self) -> None:
        """Test state name() method returns the state name."""
        state = SdlState("my_state")
        assert state.name() == "my_state"

    def test_state_id(self) -> None:
        """Test state id() method returns the state name (id is same as name)."""
        state = SdlState("unique_state")
        assert state.id() == "unique_state"

    def test_state_id_equals_name(self) -> None:
        """Test that id() and name() return the same value."""
        state = SdlState("same_value")
        assert state.id() == state.name()

    def test_state_str(self) -> None:
        """Test __str__ method returns formatted state name."""
        state = SdlState("formatted_state")
        # The __str__ method calls self.name which returns self._name
        # But looking at line 17, it's f"{self.name}" which calls the name() method
        assert str(state) == "formatted_state"

    def test_state_format(self) -> None:
        """Test __format__ method for string formatting."""
        state = SdlState("format_test")
        # __format__ calls format(str(self.name()), formatspec)
        # "format_test" is 11 chars, so >20 means 9 spaces before it
        formatted = f"{state:>20}"
        assert formatted == "         format_test"

    def test_state_format_with_different_specs(self) -> None:
        """Test __format__ with various format specifications."""
        state = SdlState("abc")

        # Left align
        assert f"{state:<10}" == "abc       "

        # Right align
        assert f"{state:>10}" == "       abc"

        # Center
        assert f"{state:^10}" == "   abc    "

    def test_state_set_name(self) -> None:
        """Test _set_name() method changes the state name."""
        state = SdlState("original")
        assert state.name() == "original"

        state._set_name("modified")
        assert state.name() == "modified"
        assert state.id() == "modified"
        assert str(state) == "modified"

    def test_predefined_start_state(self) -> None:
        """Test predefined 'start' state."""
        assert start.name() == "start"
        assert isinstance(start, SdlState)

    def test_predefined_wait_state(self) -> None:
        """Test predefined 'wait' state."""
        assert wait.name() == "wait"
        assert isinstance(wait, SdlState)

    def test_predefined_star_state(self) -> None:
        """Test predefined '*' (star) state."""
        assert star.name() == "*"
        assert isinstance(star, SdlState)

    def test_state_str_in_fstring(self) -> None:
        """Test state string representation in f-strings."""
        state = SdlState("interpolate")
        message = f"Current state: {state}"
        assert message == "Current state: interpolate"

    def test_state_equality_by_name(self) -> None:
        """Test that states with same name are not necessarily equal (different objects)."""
        state1 = SdlState("same_name")
        state2 = SdlState("same_name")

        # They should have the same name
        assert state1.name() == state2.name()

        # But they are different objects
        assert state1 is not state2

    def test_state_with_empty_name(self) -> None:
        """Test creating a state with empty string name."""
        state = SdlState("")
        assert state.name() == ""
        assert state.id() == ""
        assert str(state) == ""

    def test_state_with_special_characters(self) -> None:
        """Test state names with special characters."""
        special_name = "state-with-dashes_and_underscores.123"
        state = SdlState(special_name)
        assert state.name() == special_name
        assert str(state) == special_name

    def test_state_name_immutability_via_public_api(self) -> None:
        """Test that state name should not be changed except via _set_name."""
        state = SdlState("immutable")
        original_name = state.name()

        # Only _set_name should change the name (it's a private method)
        state._set_name("mutable")
        assert state.name() != original_name
        assert state.name() == "mutable"
