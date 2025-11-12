"""Test suite for SdlStateMachine.

This module tests FSM creation, event registration, handler lookup, and state transitions.
"""

from typing import Optional

import pytest

from pysdl.exceptions import ValidationError
from pysdl.id_generator import SdlIdGenerator
from pysdl.signal import SdlSignal
from pysdl.state import SdlState
from pysdl.state_machine import SdlStateMachine


class TestSdlStateMachine:
    """Test cases for SdlStateMachine class."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> None:
        """Reset state before each test."""
        SdlIdGenerator._id = 0

    @pytest.fixture
    def fsm(self) -> SdlStateMachine:
        """Create a fresh state machine for each test."""
        return SdlStateMachine()

    async def dummy_handler(self, signal: SdlSignal) -> None:
        """Dummy async handler for testing."""

    def test_fsm_creation(self, fsm: SdlStateMachine) -> None:
        """Test basic state machine creation."""
        assert fsm is not None
        assert isinstance(fsm, SdlStateMachine)

    def test_fsm_initial_state_none(self, fsm: SdlStateMachine) -> None:
        """Test that initial state is None."""
        assert fsm._state is None

    def test_fsm_initial_event_none(self, fsm: SdlStateMachine) -> None:
        """Test that initial event is None."""
        assert fsm._event is None

    def test_fsm_set_state(self, fsm: SdlStateMachine) -> None:
        """Test setting a state."""
        state = SdlState("test_state")
        result = fsm.state(state)
        assert fsm._state == state
        assert result is fsm  # Should return self for chaining

    def test_fsm_set_state_rejects_none(self, fsm: SdlStateMachine) -> None:
        """Test that setting None as state raises ValidationError."""
        with pytest.raises(ValidationError, match="State cannot be None"):
            fsm.state(None)  # type: ignore

    def test_fsm_set_state_rejects_non_state(self, fsm: SdlStateMachine) -> None:
        """Test that setting non-SdlState raises ValidationError."""
        with pytest.raises(ValidationError, match="Expected SdlState"):
            fsm.state("not_a_state")  # type: ignore

    def test_fsm_set_event(self, fsm: SdlStateMachine) -> None:
        """Test setting an event."""

        class TestSignal(SdlSignal):
            pass

        result = fsm.event(TestSignal)
        assert fsm._event == TestSignal.id()
        assert result is fsm  # Should return self for chaining

    def test_fsm_set_event_rejects_none(self, fsm: SdlStateMachine) -> None:
        """Test that setting None as event raises ValidationError."""
        with pytest.raises(ValidationError, match="Event cannot be None"):
            fsm.event(None)  # type: ignore

    def test_fsm_set_event_rejects_non_signal(self, fsm: SdlStateMachine) -> None:
        """Test that setting non-SdlSignal raises ValidationError."""
        with pytest.raises(ValidationError, match="Event must be a class"):
            fsm.event("not_a_signal")  # type: ignore

    def test_fsm_set_event_rejects_non_signal_class(self, fsm: SdlStateMachine) -> None:
        """Test that setting a class that is not a SdlSignal subclass raises ValidationError."""

        class NotASignal:
            pass

        with pytest.raises(ValidationError, match="Expected SdlSignal subclass"):
            fsm.event(NotASignal)  # type: ignore

    def test_fsm_set_handler(self, fsm: SdlStateMachine) -> None:
        """Test setting a handler."""
        state = SdlState("test_state")

        class TestSignal(SdlSignal):
            pass

        result = fsm.state(state).event(TestSignal).handler(self.dummy_handler)
        assert result is fsm  # Should return self for chaining
        assert state in fsm._handlers
        assert TestSignal.id() in fsm._handlers[state]

    def test_fsm_set_handler_requires_state(self, fsm: SdlStateMachine) -> None:
        """Test that setting handler without state raises ValidationError."""

        class TestSignal(SdlSignal):
            pass

        with pytest.raises(
            ValidationError, match="State must be set before adding handler"
        ):
            fsm.event(TestSignal).handler(self.dummy_handler)

    def test_fsm_set_handler_requires_event(self, fsm: SdlStateMachine) -> None:
        """Test that setting handler without event raises ValidationError."""
        state = SdlState("test_state")
        with pytest.raises(
            ValidationError, match="Event must be set before adding handler"
        ):
            fsm.state(state).handler(self.dummy_handler)

    def test_fsm_set_handler_rejects_non_callable(self, fsm: SdlStateMachine) -> None:
        """Test that setting non-callable handler raises ValidationError."""
        state = SdlState("test_state")

        class TestSignal(SdlSignal):
            pass

        with pytest.raises(ValidationError, match="Handler must be callable"):
            fsm.state(state).event(TestSignal).handler("not_callable")  # type: ignore

    def test_fsm_done(self, fsm: SdlStateMachine) -> None:
        """Test done() method."""
        assert fsm.done() is True

    def test_fsm_find_existing_handler(self, fsm: SdlStateMachine) -> None:
        """Test finding an existing handler."""
        state = SdlState("test_state")

        class TestSignal(SdlSignal):
            pass

        fsm.state(state).event(TestSignal).handler(self.dummy_handler)

        found = fsm.find(state, TestSignal.id())
        assert found == self.dummy_handler

    def test_fsm_find_rejects_none_state(self, fsm: SdlStateMachine) -> None:
        """Test finding handler with None state raises ValidationError."""

        class TestSignal(SdlSignal):
            pass

        with pytest.raises(ValidationError, match="Cannot find handler for None state"):
            fsm.find(None, TestSignal.id())  # type: ignore

    def test_fsm_find_rejects_none_event(self, fsm: SdlStateMachine) -> None:
        """Test finding handler with None event raises ValidationError."""
        state = SdlState("test_state")

        with pytest.raises(ValidationError, match="Cannot find handler for None event"):
            fsm.find(state, None)  # type: ignore

    def test_fsm_find_nonexistent_handler(self, fsm: SdlStateMachine) -> None:
        """Test finding a non-existent handler returns None."""
        state = SdlState("test_state")

        class TestSignal(SdlSignal):
            pass

        found = fsm.find(state, TestSignal.id())
        assert found is None

    def test_fsm_find_wrong_state(self, fsm: SdlStateMachine) -> None:
        """Test finding handler with wrong state returns None."""
        state1 = SdlState("state1")
        state2 = SdlState("state2")

        class TestSignal(SdlSignal):
            pass

        fsm.state(state1).event(TestSignal).handler(self.dummy_handler)

        found = fsm.find(state2, TestSignal.id())
        assert found is None

    def test_fsm_find_wrong_event(self, fsm: SdlStateMachine) -> None:
        """Test finding handler with wrong event returns None."""
        state = SdlState("test_state")

        class Signal1(SdlSignal):
            _id: Optional[int] = None

        class Signal2(SdlSignal):
            _id: Optional[int] = None

        fsm.state(state).event(Signal1).handler(self.dummy_handler)

        # Signal2 should not find the handler registered for Signal1
        found = fsm.find(state, Signal2.id())
        assert found is None

    def test_fsm_multiple_states(self, fsm: SdlStateMachine) -> None:
        """Test registering handlers for multiple states."""
        state1 = SdlState("state1")
        state2 = SdlState("state2")

        class TestSignal(SdlSignal):
            pass

        async def handler1(signal: SdlSignal) -> None:
            pass

        async def handler2(signal: SdlSignal) -> None:
            pass

        fsm.state(state1).event(TestSignal).handler(handler1)
        fsm.state(state2).event(TestSignal).handler(handler2)

        found1 = fsm.find(state1, TestSignal.id())
        found2 = fsm.find(state2, TestSignal.id())

        assert found1 is handler1
        assert found2 is handler2

    def test_fsm_multiple_events(self, fsm: SdlStateMachine) -> None:
        """Test registering handlers for multiple events in same state."""
        state = SdlState("test_state")

        class Signal1(SdlSignal):
            _id: Optional[int] = None

        class Signal2(SdlSignal):
            _id: Optional[int] = None

        async def handler1(signal: SdlSignal) -> None:
            pass

        async def handler2(signal: SdlSignal) -> None:
            pass

        fsm.state(state).event(Signal1).handler(handler1)
        fsm.state(state).event(Signal2).handler(handler2)

        found1 = fsm.find(state, Signal1.id())
        found2 = fsm.find(state, Signal2.id())

        assert found1 is handler1
        assert found2 is handler2

    def test_fsm_chaining(self, fsm: SdlStateMachine) -> None:
        """Test method chaining for FSM definition."""
        state1 = SdlState("state1")
        state2 = SdlState("state2")

        class Signal1(SdlSignal):
            _id: Optional[int] = None

        class Signal2(SdlSignal):
            _id: Optional[int] = None

        async def handler1(signal: SdlSignal) -> None:
            pass

        async def handler2(signal: SdlSignal) -> None:
            pass

        # Test chaining multiple handler registrations
        fsm.state(state1).event(Signal1).handler(handler1)
        fsm.state(state1).event(Signal2).handler(handler2)
        fsm.state(state2).event(Signal1).handler(handler1)

        assert fsm.find(state1, Signal1.id()) is handler1
        assert fsm.find(state1, Signal2.id()) is handler2
        assert fsm.find(state2, Signal1.id()) is handler1

    def test_fsm_handler_overwrite(self, fsm: SdlStateMachine) -> None:
        """Test that re-registering same state/event overwrites handler."""
        state = SdlState("test_state")

        class TestSignal(SdlSignal):
            pass

        async def handler1(signal: SdlSignal) -> None:
            pass

        async def handler2(signal: SdlSignal) -> None:
            pass

        fsm.state(state).event(TestSignal).handler(handler1)
        fsm.state(state).event(TestSignal).handler(handler2)

        found = fsm.find(state, TestSignal.id())
        assert found is handler2  # Should be the last one registered

    def test_fsm_tracks_states(self, fsm: SdlStateMachine) -> None:
        """Test that FSM tracks all registered states."""
        state1 = SdlState("state1")
        state2 = SdlState("state2")

        class TestSignal(SdlSignal):
            pass

        fsm.state(state1).event(TestSignal).handler(self.dummy_handler)
        fsm.state(state2).event(TestSignal).handler(self.dummy_handler)

        assert state1 in fsm._states
        assert state2 in fsm._states

    def test_fsm_tracks_events(self, fsm: SdlStateMachine) -> None:
        """Test that FSM tracks all registered events."""
        state = SdlState("test_state")

        class Signal1(SdlSignal):
            _id: Optional[int] = None

        class Signal2(SdlSignal):
            _id: Optional[int] = None

        fsm.state(state).event(Signal1).handler(self.dummy_handler)
        fsm.state(state).event(Signal2).handler(self.dummy_handler)

        assert Signal1.id() in fsm._events
        assert Signal2.id() in fsm._events
