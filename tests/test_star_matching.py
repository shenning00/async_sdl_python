"""Test star state and star signal wildcard matching.

This module tests Priority 2 matching - star state handlers that match
specific signals from any state.
"""

import pytest

from pysdl.id_generator import SdlIdGenerator
from pysdl.process import SdlProcess
from pysdl.signal import SdlSignal
from pysdl.state import SdlState, star, start
from pysdl.system import SdlSystem
from pysdl.system_signals import SdlStarSignal, SdlStartSignal
from pysdl.timer import SdlTimer


# Test signals
class TestSignalA(SdlSignal):
    """Test signal A."""


class TestSignalB(SdlSignal):
    """Test signal B."""


class EmergencyStopSignal(SdlSignal):
    """Emergency stop signal for testing global handlers."""


# Test process with star state handler
class ProcessWithStarState(SdlProcess):
    """Process that handles emergency stop from any state."""

    state_idle = SdlState("idle")
    state_working = SdlState("working")
    state_cleanup = SdlState("cleanup")

    def __init__(self, parent_pid, config_data=None, system=None):
        super().__init__(parent_pid, config_data, system)
        self.emergency_stop_called = False
        self.current_signal = None

    def _init_state_machine(self):
        # Star state handler - works from ANY state
        self._event(star, EmergencyStopSignal, self.handle_emergency_stop)

        # State-specific handlers
        self._event(self.state_idle, TestSignalA, self.handle_signal_a)
        self._event(self.state_working, TestSignalB, self.handle_signal_b)

        self._done()

    async def start_StartTransition(self, signal):
        await self.next_state(self.state_idle)

    async def handle_emergency_stop(self, signal):
        """Global emergency stop handler."""
        self.emergency_stop_called = True
        self.current_signal = signal
        self._system.stop()

    async def handle_signal_a(self, signal):
        """Handle signal A in idle state."""
        await self.next_state(self.state_working)

    async def handle_signal_b(self, signal):
        """Handle signal B in working state."""
        await self.next_state(self.state_cleanup)


@pytest.fixture
def sdl_system():
    """Provide a fresh SdlSystem instance for each test."""
    return SdlSystem()


class TestStarStateMatching:
    """Test cases for star state (Priority 2) wildcard matching."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> None:
        """Reset state before each test."""
        SdlIdGenerator._id = 0
        # Reset Signal and Timer class IDs to prevent cross-test contamination
        SdlSignal._id = None
        SdlTimer._id = None
        # Also reset test signal IDs to prevent collision
        TestSignalA._id = None
        TestSignalB._id = None
        EmergencyStopSignal._id = None
        SdlStarSignal._id = None

    @pytest.mark.asyncio
    async def test_star_state_handler_works_from_any_state(self, sdl_system):
        """Test that star state handler matches signal from any state."""
        process = await ProcessWithStarState.create(None, system=sdl_system)

        # Move to idle state (manually, since start signal isn't processed yet)
        await process.next_state(ProcessWithStarState.state_idle)
        assert process.current_state() == ProcessWithStarState.state_idle

        # Emergency stop should work from idle state
        signal = EmergencyStopSignal.create()
        handler = process.lookup_transition(signal)
        assert handler is not None
        assert handler == process.handle_emergency_stop

        # Move to working state
        await process.next_state(ProcessWithStarState.state_working)

        # Emergency stop should still work from working state
        signal = EmergencyStopSignal.create()
        handler = process.lookup_transition(signal)
        assert handler is not None
        assert handler == process.handle_emergency_stop

    @pytest.mark.asyncio
    async def test_star_state_lower_priority_than_exact_match(self, sdl_system):
        """Test that exact match takes priority over star state."""

        class ProcessWithBothHandlers(SdlProcess):
            state_active = SdlState("active")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.star_handler_called = False
                self.exact_handler_called = False

            def _init_state_machine(self):
                # Star state handler (Priority 2)
                self._event(star, TestSignalA, self.star_handler)

                # Exact match handler (Priority 1 - higher!)
                self._event(self.state_active, TestSignalA, self.exact_handler)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_active)

            async def star_handler(self, signal):
                self.star_handler_called = True

            async def exact_handler(self, signal):
                self.exact_handler_called = True

        process = await ProcessWithBothHandlers.create(None, system=sdl_system)

        # Manually transition to active state
        await process.next_state(ProcessWithBothHandlers.state_active)

        # Should find exact match, not star state handler
        signal = TestSignalA.create()
        handler = process.lookup_transition(signal)
        assert handler == process.exact_handler  # Exact match wins!

    @pytest.mark.asyncio
    async def test_star_state_consistent_across_states(self, sdl_system):
        """Test that star state handler is consistent across all states."""
        process = await ProcessWithStarState.create(None, system=sdl_system)
        await process._register()

        states = [
            ProcessWithStarState.state_idle,
            ProcessWithStarState.state_working,
            ProcessWithStarState.state_cleanup,
        ]

        # Test emergency stop from each state
        for state in states:
            await process.next_state(state)
            signal = EmergencyStopSignal.create()
            handler = process.lookup_transition(signal)
            assert handler == process.handle_emergency_stop

    @pytest.mark.asyncio
    async def test_star_state_matches_only_specific_signal(self, sdl_system):
        """Test that star state matches only the specific signal, not all signals."""
        process = await ProcessWithStarState.create(None, system=sdl_system)
        await process._register()

        # Emergency stop should match
        emergency_signal = EmergencyStopSignal.create()
        handler = process.lookup_transition(emergency_signal)
        assert handler == process.handle_emergency_stop

        # Other signals should not match via star state
        other_signal = TestSignalB.create()
        handler = process.lookup_transition(other_signal)
        assert handler is None  # No handler for TestSignalB in idle state

    @pytest.mark.asyncio
    async def test_multiple_star_state_handlers(self, sdl_system):
        """Test that multiple star state handlers can coexist."""

        class ProcessWithMultipleStarHandlers(SdlProcess):
            state_running = SdlState("running")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.signal_a_count = 0
                self.signal_b_count = 0

            def _init_state_machine(self):
                # Multiple star state handlers
                self._event(star, TestSignalA, self.handle_a)
                self._event(star, TestSignalB, self.handle_b)
                self._event(star, EmergencyStopSignal, self.handle_emergency)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_running)

            async def handle_a(self, signal):
                self.signal_a_count += 1

            async def handle_b(self, signal):
                self.signal_b_count += 1

            async def handle_emergency(self, signal):
                self._system.stop()

        process = await ProcessWithMultipleStarHandlers.create(None, system=sdl_system)
        await process._register()

        # All three should match via star state
        assert process.lookup_transition(TestSignalA.create()) == process.handle_a
        assert process.lookup_transition(TestSignalB.create()) == process.handle_b
        assert (
            process.lookup_transition(EmergencyStopSignal.create())
            == process.handle_emergency
        )

    @pytest.mark.asyncio
    async def test_star_state_handler_execution(self, sdl_system):
        """Test that star state handler actually executes correctly."""
        process = await ProcessWithStarState.create(None, system=sdl_system)
        await process._register()

        # Verify handler not called initially
        assert process.emergency_stop_called is False
        assert process.current_signal is None

        # Send emergency stop signal
        signal = EmergencyStopSignal.create()
        handler = process.lookup_transition(signal)
        assert handler is not None

        # Execute the handler
        await handler(signal)

        # Verify handler was called with correct signal
        assert process.emergency_stop_called is True
        assert process.current_signal == signal

    @pytest.mark.asyncio
    async def test_star_state_without_state_specific_handler(self, sdl_system):
        """Test star state handler when no state-specific handler exists."""

        class ProcessOnlyStarHandlers(SdlProcess):
            state_a = SdlState("a")
            state_b = SdlState("b")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.handler_called = False

            def _init_state_machine(self):
                # Only star state handlers, no state-specific ones
                self._event(star, TestSignalA, self.handle_global_a)
                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_a)

            async def handle_global_a(self, signal):
                self.handler_called = True

        process = await ProcessOnlyStarHandlers.create(None, system=sdl_system)
        await process._register()

        # Should find star state handler from any state
        await process.next_state(process.state_a)
        assert (
            process.lookup_transition(TestSignalA.create()) == process.handle_global_a
        )

        await process.next_state(process.state_b)
        assert (
            process.lookup_transition(TestSignalA.create()) == process.handle_global_a
        )

    @pytest.mark.asyncio
    async def test_star_state_preserves_current_state(self, sdl_system):
        """Test that star state handler can access and preserve current state."""

        class ProcessWithStateTracking(SdlProcess):
            state_alpha = SdlState("alpha")
            state_beta = SdlState("beta")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.handler_called_from_state = None

            def _init_state_machine(self):
                self._event(star, EmergencyStopSignal, self.handle_emergency_with_state)
                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_alpha)

            async def handle_emergency_with_state(self, signal):
                # Record which state we were in when handler was called
                self.handler_called_from_state = self.current_state()

        process = await ProcessWithStateTracking.create(None, system=sdl_system)
        await process._register()

        # Test from alpha state
        await process.next_state(process.state_alpha)
        assert process.current_state() == process.state_alpha

        signal = EmergencyStopSignal.create()
        handler = process.lookup_transition(signal)
        await handler(signal)

        assert process.handler_called_from_state == process.state_alpha

        # Test from beta state
        await process.next_state(process.state_beta)
        assert process.current_state() == process.state_beta

        signal = EmergencyStopSignal.create()
        handler = process.lookup_transition(signal)
        await handler(signal)

        assert process.handler_called_from_state == process.state_beta

    @pytest.mark.asyncio
    async def test_star_state_with_start_state(self, sdl_system):
        """Test that star state handler works even before entering first state."""

        class ProcessStarFromStart(SdlProcess):
            state_main = SdlState("main")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.handler_called_before_first_state = False

            def _init_state_machine(self):
                self._event(star, EmergencyStopSignal, self.handle_emergency)
                self._done()

            async def start_StartTransition(self, signal):
                # Before transitioning, check if emergency handler works
                # (This simulates handler being available even at start state)
                await self.next_state(self.state_main)

            async def handle_emergency(self, signal):
                self.handler_called_before_first_state = True

        process = await ProcessStarFromStart.create(None, system=sdl_system)

        # Even before _register (which triggers start transition)
        # the star handler should be findable
        signal = EmergencyStopSignal.create()
        handler = process.lookup_transition(signal)
        assert handler == process.handle_emergency

        await process._register()

        # And still works after registration
        handler = process.lookup_transition(signal)
        assert handler == process.handle_emergency


# Test process with star signal handler
class ProcessWithStarSignal(SdlProcess):
    """Process that handles any signal in specific state using star signal."""

    state_idle = SdlState("idle")
    state_buffering = SdlState("buffering")
    state_ready = SdlState("ready")

    def __init__(self, parent_pid, config_data=None, system=None):
        super().__init__(parent_pid, config_data, system)
        self.buffered_signals = []
        self.ready_signals = []

    def _init_state_machine(self):
        # Star signal handler - catch ANY signal in buffering state
        self._event(self.state_buffering, SdlStarSignal, self.buffer_signal)

        # Regular handlers for specific signals in ready state
        self._event(self.state_ready, TestSignalA, self.handle_signal_a)
        self._event(self.state_ready, TestSignalB, self.handle_signal_b)

        self._done()

    async def start_StartTransition(self, signal):
        await self.next_state(self.state_idle)

    async def buffer_signal(self, signal):
        """Buffer any signal received while in buffering state."""
        self.buffered_signals.append(signal)

    async def handle_signal_a(self, signal):
        """Handle signal A in ready state."""
        self.ready_signals.append(signal)

    async def handle_signal_b(self, signal):
        """Handle signal B in ready state."""
        self.ready_signals.append(signal)


class TestStarSignalMatching:
    """Test cases for star signal (Priority 3) wildcard matching."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> None:
        """Reset state before each test."""
        SdlIdGenerator._id = 0
        # Reset Signal and Timer class IDs to prevent cross-test contamination
        SdlSignal._id = None
        SdlTimer._id = None
        # Also reset test signal IDs to prevent collision
        TestSignalA._id = None
        TestSignalB._id = None
        EmergencyStopSignal._id = None
        SdlStarSignal._id = None

    @pytest.mark.asyncio
    async def test_star_signal_catches_any_signal_type(self, sdl_system):
        """Test that star signal handler matches any signal type in specific state."""
        process = await ProcessWithStarSignal.create(None, system=sdl_system)
        await process.next_state(ProcessWithStarSignal.state_buffering)

        # All different signal types should match star signal handler
        signal_a = TestSignalA.create()
        signal_b = TestSignalB.create()
        emergency = EmergencyStopSignal.create()

        # All should find the buffer_signal handler
        assert process.lookup_transition(signal_a) == process.buffer_signal
        assert process.lookup_transition(signal_b) == process.buffer_signal
        assert process.lookup_transition(emergency) == process.buffer_signal

    @pytest.mark.asyncio
    async def test_star_signal_only_matches_in_specific_state(self, sdl_system):
        """Test that star signal handler only matches in registered state."""
        process = await ProcessWithStarSignal.create(None, system=sdl_system)

        # In idle state - no star signal handler
        await process.next_state(ProcessWithStarSignal.state_idle)
        signal = TestSignalA.create()
        handler = process.lookup_transition(signal)
        assert handler is None  # No handler in idle state

        # In buffering state - star signal matches
        await process.next_state(ProcessWithStarSignal.state_buffering)
        handler = process.lookup_transition(signal)
        assert handler == process.buffer_signal  # Star signal matches!

        # In ready state - exact match takes precedence
        await process.next_state(ProcessWithStarSignal.state_ready)
        handler = process.lookup_transition(signal)
        assert handler == process.handle_signal_a  # Exact match, not star signal

    @pytest.mark.asyncio
    async def test_exact_match_higher_priority_than_star_signal(self, sdl_system):
        """Test that exact match takes priority over star signal."""

        class ProcessWithBoth(SdlProcess):
            state_active = SdlState("active")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.star_called = False
                self.exact_called = False

            def _init_state_machine(self):
                # Star signal handler (Priority 3)
                self._event(self.state_active, SdlStarSignal, self.star_handler)

                # Exact match handler (Priority 1 - higher!)
                self._event(self.state_active, TestSignalA, self.exact_handler)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_active)

            async def star_handler(self, signal):
                self.star_called = True

            async def exact_handler(self, signal):
                self.exact_called = True

        process = await ProcessWithBoth.create(None, system=sdl_system)
        await process.next_state(ProcessWithBoth.state_active)

        # TestSignalA should match exact handler, not star signal
        signal_a = TestSignalA.create()
        handler = process.lookup_transition(signal_a)
        assert handler == process.exact_handler

        # Other signals should match star signal handler
        signal_b = TestSignalB.create()
        handler = process.lookup_transition(signal_b)
        assert handler == process.star_handler

    @pytest.mark.asyncio
    async def test_star_state_higher_priority_than_star_signal(self, sdl_system):
        """Test that star state (Priority 2) beats star signal (Priority 3)."""

        class ProcessWithBothWildcards(SdlProcess):
            state_active = SdlState("active")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.star_state_called = False
                self.star_signal_called = False

            def _init_state_machine(self):
                # Star state handler (Priority 2)
                self._event(star, TestSignalA, self.star_state_handler)

                # Star signal handler (Priority 3 - lower!)
                self._event(self.state_active, SdlStarSignal, self.star_signal_handler)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_active)

            async def star_state_handler(self, signal):
                self.star_state_called = True

            async def star_signal_handler(self, signal):
                self.star_signal_called = True

        process = await ProcessWithBothWildcards.create(None, system=sdl_system)
        await process.next_state(ProcessWithBothWildcards.state_active)

        # TestSignalA should match star state (Priority 2), not star signal (Priority 3)
        signal_a = TestSignalA.create()
        handler = process.lookup_transition(signal_a)
        assert handler == process.star_state_handler

        # Other signals should match star signal (Priority 3)
        signal_b = TestSignalB.create()
        handler = process.lookup_transition(signal_b)
        assert handler == process.star_signal_handler

    @pytest.mark.asyncio
    async def test_star_signal_handler_execution(self, sdl_system):
        """Test that star signal handler actually executes correctly."""
        process = await ProcessWithStarSignal.create(None, system=sdl_system)
        await process.next_state(ProcessWithStarSignal.state_buffering)

        # Send multiple different signal types
        signals = [
            TestSignalA.create(),
            TestSignalB.create(),
            EmergencyStopSignal.create(),
        ]

        # All should be buffered
        for signal in signals:
            handler = process.lookup_transition(signal)
            assert handler == process.buffer_signal
            await handler(signal)

        # Verify all signals were buffered
        assert len(process.buffered_signals) == 3
        assert isinstance(process.buffered_signals[0], TestSignalA)
        assert isinstance(process.buffered_signals[1], TestSignalB)
        assert isinstance(process.buffered_signals[2], EmergencyStopSignal)

    @pytest.mark.asyncio
    async def test_multiple_states_with_star_signal(self, sdl_system):
        """Test that different states can have different star signal handlers."""

        class ProcessWithMultipleStarSignals(SdlProcess):
            state_buffering = SdlState("buffering")
            state_logging = SdlState("logging")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.buffered = []
                self.logged = []

            def _init_state_machine(self):
                # Different star signal handlers for different states
                self._event(self.state_buffering, SdlStarSignal, self.buffer_it)
                self._event(self.state_logging, SdlStarSignal, self.log_it)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_buffering)

            async def buffer_it(self, signal):
                self.buffered.append(signal)

            async def log_it(self, signal):
                self.logged.append(signal)

        process = await ProcessWithMultipleStarSignals.create(None, system=sdl_system)

        # In buffering state
        await process.next_state(ProcessWithMultipleStarSignals.state_buffering)
        handler = process.lookup_transition(TestSignalA.create())
        assert handler == process.buffer_it

        # In logging state
        await process.next_state(ProcessWithMultipleStarSignals.state_logging)
        handler = process.lookup_transition(TestSignalA.create())
        assert handler == process.log_it

    @pytest.mark.asyncio
    async def test_star_signal_vs_no_handler(self, sdl_system):
        """Test star signal provides fallback when no exact handler exists."""
        process = await ProcessWithStarSignal.create(None, system=sdl_system)

        # State without star signal - no handler found
        await process.next_state(ProcessWithStarSignal.state_idle)
        unknown_signal = EmergencyStopSignal.create()
        handler = process.lookup_transition(unknown_signal)
        assert handler is None

        # State with star signal - handler found
        await process.next_state(ProcessWithStarSignal.state_buffering)
        handler = process.lookup_transition(unknown_signal)
        assert handler == process.buffer_signal


class TestPriorityAndDoubleStar:
    """Test cases for priority ordering and double star (Priority 4) wildcard matching."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> None:
        """Reset state before each test."""
        SdlIdGenerator._id = 0
        # Reset Signal and Timer class IDs to prevent cross-test contamination
        SdlSignal._id = None
        SdlTimer._id = None
        # Also reset test signal IDs to prevent collision
        TestSignalA._id = None
        TestSignalB._id = None
        EmergencyStopSignal._id = None
        SdlStarSignal._id = None

    @pytest.mark.asyncio
    async def test_all_four_priority_levels(self, sdl_system):
        """Test that all 4 priority levels work correctly in order."""

        class ComprehensiveProcess(SdlProcess):
            state_active = SdlState("active")
            state_other = SdlState("other")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.priority_1_called = False
                self.priority_2_called = False
                self.priority_3_called = False
                self.priority_4_called = False

            def _init_state_machine(self):
                # Priority 1: Exact match (state, signal)
                self._event(self.state_active, TestSignalA, self.priority_1_handler)

                # Priority 2: Star state + specific signal
                self._event(star, TestSignalB, self.priority_2_handler)

                # Priority 3: Specific state + star signal
                self._event(self.state_active, SdlStarSignal, self.priority_3_handler)

                # Priority 4: Double star (star state + star signal)
                self._event(star, SdlStarSignal, self.priority_4_handler)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_active)

            async def priority_1_handler(self, signal):
                self.priority_1_called = True

            async def priority_2_handler(self, signal):
                self.priority_2_called = True

            async def priority_3_handler(self, signal):
                self.priority_3_called = True

            async def priority_4_handler(self, signal):
                self.priority_4_called = True

        process = await ComprehensiveProcess.create(None, system=sdl_system)
        await process.next_state(ComprehensiveProcess.state_active)

        # TestSignalA in state_active: Priority 1 (exact match)
        assert (
            process.lookup_transition(TestSignalA.create())
            == process.priority_1_handler
        )

        # TestSignalB in state_active: Priority 2 (star state)
        assert (
            process.lookup_transition(TestSignalB.create())
            == process.priority_2_handler
        )

        # EmergencyStopSignal in state_active: Priority 3 (star signal)
        assert (
            process.lookup_transition(EmergencyStopSignal.create())
            == process.priority_3_handler
        )

        # Move to other state
        await process.next_state(ComprehensiveProcess.state_other)

        # TestSignalB in state_other: Priority 2 (star state still works)
        assert (
            process.lookup_transition(TestSignalB.create())
            == process.priority_2_handler
        )

        # EmergencyStopSignal in state_other: Priority 4 (double star - fallback)
        assert (
            process.lookup_transition(EmergencyStopSignal.create())
            == process.priority_4_handler
        )

    @pytest.mark.asyncio
    async def test_priority_cascade(self, sdl_system):
        """Test that lower priorities are only used when higher ones don't match."""

        class CascadeProcess(SdlProcess):
            state_one = SdlState("one")
            state_two = SdlState("two")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.calls = []

            def _init_state_machine(self):
                # Only Priority 3 and 4 handlers
                self._event(self.state_one, SdlStarSignal, self.priority_3_handler)
                self._event(star, SdlStarSignal, self.priority_4_handler)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_one)

            async def priority_3_handler(self, signal):
                self.calls.append("priority_3")

            async def priority_4_handler(self, signal):
                self.calls.append("priority_4")

        process = await CascadeProcess.create(None, system=sdl_system)
        await process.next_state(CascadeProcess.state_one)

        # In state_one: Priority 3 matches (state + star signal)
        assert (
            process.lookup_transition(TestSignalA.create())
            == process.priority_3_handler
        )

        # In state_two: Priority 4 matches (double star fallback)
        await process.next_state(CascadeProcess.state_two)
        assert (
            process.lookup_transition(TestSignalA.create())
            == process.priority_4_handler
        )

    @pytest.mark.asyncio
    async def test_double_star_catch_all(self, sdl_system):
        """Test that double star (star + SdlStarSignal) catches everything."""

        class CatchAllProcess(SdlProcess):
            state_one = SdlState("one")
            state_two = SdlState("two")
            state_three = SdlState("three")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.caught_signals = []

            def _init_state_machine(self):
                # Only double star handler
                self._event(star, SdlStarSignal, self.catch_everything)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_one)

            async def catch_everything(self, signal):
                self.caught_signals.append(signal)

        process = await CatchAllProcess.create(None, system=sdl_system)

        # Test across all states
        states = [
            CatchAllProcess.state_one,
            CatchAllProcess.state_two,
            CatchAllProcess.state_three,
        ]

        signals = [
            TestSignalA.create(),
            TestSignalB.create(),
            EmergencyStopSignal.create(),
        ]

        for state in states:
            await process.next_state(state)
            for signal in signals:
                handler = process.lookup_transition(signal)
                assert handler == process.catch_everything

    @pytest.mark.asyncio
    async def test_double_star_lowest_priority(self, sdl_system):
        """Test that double star is only used when no higher priority matches."""

        class PriorityTestProcess(SdlProcess):
            state_active = SdlState("active")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)

            def _init_state_machine(self):
                # All 4 priorities for TestSignalA in state_active
                self._event(
                    self.state_active, TestSignalA, self.priority_1
                )  # Priority 1
                self._event(
                    star, TestSignalA, self.priority_2
                )  # Priority 2 (won't be used)
                self._event(
                    self.state_active, SdlStarSignal, self.priority_3
                )  # Priority 3 (won't be used)
                self._event(
                    star, SdlStarSignal, self.priority_4
                )  # Priority 4 (won't be used)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_active)

            async def priority_1(self, signal):
                pass

            async def priority_2(self, signal):
                pass

            async def priority_3(self, signal):
                pass

            async def priority_4(self, signal):
                pass

        process = await PriorityTestProcess.create(None, system=sdl_system)
        await process.next_state(PriorityTestProcess.state_active)

        # Should always match Priority 1 (exact match)
        handler = process.lookup_transition(TestSignalA.create())
        assert handler == process.priority_1

    @pytest.mark.asyncio
    async def test_no_handlers_returns_none(self, sdl_system):
        """Test that find returns None when no handlers match any priority."""

        class EmptyProcess(SdlProcess):
            state_active = SdlState("active")

            def _init_state_machine(self):
                # No handlers registered
                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_active)

        process = await EmptyProcess.create(None, system=sdl_system)
        await process.next_state(EmptyProcess.state_active)

        # No handlers - should return None
        assert process.lookup_transition(TestSignalA.create()) is None

    @pytest.mark.asyncio
    async def test_complex_real_world_scenario(self, sdl_system):
        """Test complex scenario with all priority levels used realistically."""

        class RobustProcess(SdlProcess):
            state_idle = SdlState("idle")
            state_connecting = SdlState("connecting")
            state_ready = SdlState("ready")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.actions = []

            def _init_state_machine(self):
                # Priority 1: Exact handlers for ready state
                self._event(self.state_ready, TestSignalA, self.handle_work)
                self._event(self.state_ready, TestSignalB, self.handle_more_work)

                # Priority 2: Emergency stop from any state
                self._event(star, EmergencyStopSignal, self.emergency_stop)

                # Priority 3: Buffer anything while connecting
                self._event(self.state_connecting, SdlStarSignal, self.buffer_signal)

                # Priority 4: Log unknown signals (debugging catch-all)
                self._event(star, SdlStarSignal, self.log_unexpected)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_idle)

            async def handle_work(self, signal):
                self.actions.append("work")

            async def handle_more_work(self, signal):
                self.actions.append("more_work")

            async def emergency_stop(self, signal):
                self.actions.append("emergency_stop")
                self._system.stop()

            async def buffer_signal(self, signal):
                self.actions.append("buffer")

            async def log_unexpected(self, signal):
                self.actions.append("log_unexpected")

        process = await RobustProcess.create(None, system=sdl_system)

        # Test in idle state
        await process.next_state(RobustProcess.state_idle)
        assert (
            process.lookup_transition(EmergencyStopSignal.create())
            == process.emergency_stop
        )  # Priority 2
        assert (
            process.lookup_transition(TestSignalA.create()) == process.log_unexpected
        )  # Priority 4

        # Test in connecting state
        await process.next_state(RobustProcess.state_connecting)
        assert (
            process.lookup_transition(EmergencyStopSignal.create())
            == process.emergency_stop
        )  # Priority 2
        assert (
            process.lookup_transition(TestSignalA.create()) == process.buffer_signal
        )  # Priority 3

        # Test in ready state
        await process.next_state(RobustProcess.state_ready)
        assert (
            process.lookup_transition(TestSignalA.create()) == process.handle_work
        )  # Priority 1
        assert (
            process.lookup_transition(TestSignalB.create()) == process.handle_more_work
        )  # Priority 1
        assert (
            process.lookup_transition(EmergencyStopSignal.create())
            == process.emergency_stop
        )  # Priority 2

    @pytest.mark.asyncio
    async def test_double_star_with_overrides(self, sdl_system):
        """Test that specific handlers override the double star catch-all."""

        class OverrideProcess(SdlProcess):
            state_one = SdlState("one")
            state_two = SdlState("two")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)

            def _init_state_machine(self):
                # Double star catch-all (Priority 4)
                self._event(star, SdlStarSignal, self.catch_all)

                # Specific override in state_one (Priority 1)
                self._event(self.state_one, TestSignalA, self.specific_handler)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_one)

            async def catch_all(self, signal):
                pass

            async def specific_handler(self, signal):
                pass

        process = await OverrideProcess.create(None, system=sdl_system)

        # In state_one
        await process.next_state(OverrideProcess.state_one)
        assert (
            process.lookup_transition(TestSignalA.create()) == process.specific_handler
        )  # Priority 1
        assert (
            process.lookup_transition(TestSignalB.create()) == process.catch_all
        )  # Priority 4

        # In state_two
        await process.next_state(OverrideProcess.state_two)
        assert (
            process.lookup_transition(TestSignalA.create()) == process.catch_all
        )  # Priority 4
        assert (
            process.lookup_transition(TestSignalB.create()) == process.catch_all
        )  # Priority 4


class TestStarMatchingIntegration:
    """Integration tests for star wildcard matching in full SDL system.

    These tests verify star matching works with actual signal delivery,
    state transitions, and multiple processes interacting.
    """

    @pytest.fixture(autouse=True)
    def reset_state(self) -> None:
        """Reset state before each test."""
        SdlIdGenerator._id = 0
        # Reset Signal and Timer class IDs to prevent cross-test contamination
        SdlSignal._id = None
        SdlTimer._id = None
        # Also reset test signal IDs to prevent collision
        TestSignalA._id = None
        TestSignalB._id = None
        EmergencyStopSignal._id = None
        SdlStarSignal._id = None

    @pytest.mark.asyncio
    async def test_star_state_emergency_stop_integration(self, sdl_system):
        """Integration test: Emergency stop via star state handler with signal delivery."""

        class WorkerProcess(SdlProcess):
            state_idle = SdlState("idle")
            state_working = SdlState("working")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.work_count = 0
                self.emergency_stopped = False

            def _init_state_machine(self):
                # Register start signal handler
                self._event(start, SdlStartSignal, self.start_StartTransition)

                # Star state: emergency stop from any state
                self._event(star, EmergencyStopSignal, self.emergency_stop)

                # Regular handlers
                self._event(self.state_idle, TestSignalA, self.start_work)
                self._event(self.state_working, TestSignalB, self.do_work)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_idle)

            async def start_work(self, signal):
                await self.next_state(self.state_working)

            async def do_work(self, signal):
                self.work_count += 1

            async def emergency_stop(self, signal):
                self.emergency_stopped = True

        # Create process (this registers and sends start signal)
        worker = await WorkerProcess.create(None, system=sdl_system)

        # Process the start signal manually
        start_signal = await sdl_system.get_next_signal()
        assert isinstance(start_signal, SdlStartSignal)
        await sdl_system._process_signal(start_signal)
        assert worker.current_state() == WorkerProcess.state_idle

        # Send emergency stop from idle state
        emergency = EmergencyStopSignal.create()
        emergency.set_dst(worker.pid())
        await sdl_system.output(emergency)

        # Process the emergency signal
        emergency_signal = await sdl_system.get_next_signal()
        await sdl_system._process_signal(emergency_signal)

        # Verify emergency stop was called (star state handler worked)
        assert worker.emergency_stopped
        # Still in idle state (emergency handler didn't transition)
        assert worker.current_state() == WorkerProcess.state_idle

    @pytest.mark.asyncio
    async def test_star_signal_buffering_integration(self, sdl_system):
        """Integration test: Star signal handler buffers all signals during initialization."""

        class BufferingProcess(SdlProcess):
            state_initializing = SdlState("initializing")
            state_ready = SdlState("ready")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.buffered = []
                self.processed = []

            def _init_state_machine(self):
                # Register start signal handler
                self._event(start, SdlStartSignal, self.start_StartTransition)

                # Buffer all signals while initializing (star signal)
                self._event(self.state_initializing, SdlStarSignal, self.buffer_it)

                # Process signals when ready
                self._event(self.state_ready, TestSignalA, self.process_a)
                self._event(self.state_ready, TestSignalB, self.process_b)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_initializing)

            async def buffer_it(self, signal):
                self.buffered.append(type(signal).__name__)

            async def process_a(self, signal):
                self.processed.append("A")

            async def process_b(self, signal):
                self.processed.append("B")

        # Create process
        proc = await BufferingProcess.create(None, system=sdl_system)

        # Process start signal
        start_signal = await sdl_system.get_next_signal()
        await sdl_system._process_signal(start_signal)
        assert proc.current_state() == BufferingProcess.state_initializing

        # Send various signals while initializing
        for _ in range(3):
            sig_a = TestSignalA.create()
            sig_a.set_dst(proc.pid())
            await sdl_system.output(sig_a)

            sig_b = TestSignalB.create()
            sig_b.set_dst(proc.pid())
            await sdl_system.output(sig_b)

        # Process all buffered signals (star signal handler should catch them)
        for _ in range(6):
            signal = await sdl_system.get_next_signal()
            await sdl_system._process_signal(signal)

        # Verify signals were buffered (all should hit star signal handler)
        assert len(proc.buffered) == 6  # 3 A + 3 B
        assert proc.processed == []  # None processed (wrong state)

    @pytest.mark.asyncio
    async def test_multiple_processes_with_star_handlers(self, sdl_system):
        """Integration test: Multiple processes each with independent star handlers."""

        class LoggerProcess(SdlProcess):
            state_active = SdlState("active")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.log_count = 0

            def _init_state_machine(self):
                # Log everything (double star)
                self._event(star, SdlStarSignal, self.log_signal)
                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_active)

            async def log_signal(self, signal):
                self.log_count += 1

        class SupervisorProcess(SdlProcess):
            state_managing = SdlState("managing")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.shutdown_received = False

            def _init_state_machine(self):
                # Handle shutdown from any state (star state)
                self._event(star, EmergencyStopSignal, self.shutdown)
                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_managing)

            async def shutdown(self, signal):
                self.shutdown_received = True

        # Create processes
        logger = await LoggerProcess.create(None, system=sdl_system)
        supervisor = await SupervisorProcess.create(None, system=sdl_system)

        # Process start signals
        logger_start = await sdl_system.get_next_signal()
        await sdl_system._process_signal(logger_start)

        supervisor_start = await sdl_system.get_next_signal()
        await sdl_system._process_signal(supervisor_start)

        # Send signals to logger (double star catches all)
        for i in range(5):
            sig = TestSignalA.create()
            sig.set_dst(logger.pid())
            await sdl_system.output(sig)

        # Process logger signals
        for _ in range(5):
            signal = await sdl_system.get_next_signal()
            await sdl_system._process_signal(signal)

        # Send emergency stop to supervisor (star state catches it)
        emergency = EmergencyStopSignal.create()
        emergency.set_dst(supervisor.pid())
        await sdl_system.output(emergency)

        emergency_signal = await sdl_system.get_next_signal()
        await sdl_system._process_signal(emergency_signal)

        # Verify both processes handled signals correctly
        # Logger counts start signal + 5 TestSignalA = 6 total (double star catches everything)
        assert logger.log_count == 6
        assert supervisor.shutdown_received

    @pytest.mark.asyncio
    async def test_star_handler_triggers_state_transition(self, sdl_system):
        """Integration test: Star handler triggers state transitions across states."""

        class StateMachine(SdlProcess):
            state_a = SdlState("a")
            state_b = SdlState("b")
            state_stopped = SdlState("stopped")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.state_history = []

            def _init_state_machine(self):
                # Register start signal handler
                self._event(start, SdlStartSignal, self.start_StartTransition)

                # Star state: emergency transitions to stopped from anywhere
                self._event(star, EmergencyStopSignal, self.go_stopped)

                # Normal transitions
                self._event(self.state_a, TestSignalA, self.a_to_b)
                self._event(self.state_b, TestSignalB, self.b_to_a)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_a)
                self.state_history.append("a")

            async def a_to_b(self, signal):
                await self.next_state(self.state_b)
                self.state_history.append("b")

            async def b_to_a(self, signal):
                await self.next_state(self.state_a)
                self.state_history.append("a")

            async def go_stopped(self, signal):
                await self.next_state(self.state_stopped)
                self.state_history.append("stopped")

        # Create process
        proc = await StateMachine.create(None, system=sdl_system)

        # Process start signal
        start_signal = await sdl_system.get_next_signal()
        await sdl_system._process_signal(start_signal)
        assert proc.state_history == ["a"]

        # Transition a -> b
        sig_a = TestSignalA.create()
        sig_a.set_dst(proc.pid())
        await sdl_system.output(sig_a)
        signal_a = await sdl_system.get_next_signal()
        await sdl_system._process_signal(signal_a)
        assert proc.state_history == ["a", "b"]

        # Transition b -> a
        sig_b = TestSignalB.create()
        sig_b.set_dst(proc.pid())
        await sdl_system.output(sig_b)
        signal_b = await sdl_system.get_next_signal()
        await sdl_system._process_signal(signal_b)
        assert proc.state_history == ["a", "b", "a"]

        # Emergency stop from a -> stopped (via star handler)
        emergency = EmergencyStopSignal.create()
        emergency.set_dst(proc.pid())
        await sdl_system.output(emergency)
        emergency_signal = await sdl_system.get_next_signal()
        await sdl_system._process_signal(emergency_signal)

        # Verify state transitions
        assert proc.state_history == ["a", "b", "a", "stopped"]
        assert proc.current_state() == StateMachine.state_stopped

    @pytest.mark.asyncio
    async def test_double_star_debug_logger_integration(self, sdl_system):
        """Integration test: Double star catch-all logs unexpected signals."""

        class ProductionProcess(SdlProcess):
            state_running = SdlState("running")

            def __init__(self, parent_pid, config_data=None, system=None):
                super().__init__(parent_pid, config_data, system)
                self.expected_count = 0
                self.unexpected_count = 0

            def _init_state_machine(self):
                # Register start signal handler
                self._event(start, SdlStartSignal, self.start_StartTransition)

                # Exact handlers for expected signals (Priority 1)
                self._event(self.state_running, TestSignalA, self.handle_expected)

                # Double star catch-all for debugging unexpected signals (Priority 4)
                self._event(star, SdlStarSignal, self.log_unexpected)

                self._done()

            async def start_StartTransition(self, signal):
                await self.next_state(self.state_running)

            async def handle_expected(self, signal):
                self.expected_count += 1

            async def log_unexpected(self, signal):
                self.unexpected_count += 1

        # Create process
        proc = await ProductionProcess.create(None, system=sdl_system)

        # Process start signal
        start_signal = await sdl_system.get_next_signal()
        await sdl_system._process_signal(start_signal)

        # Send mix of expected and unexpected signals
        # Expected (will hit exact match)
        for _ in range(3):
            sig = TestSignalA.create()
            sig.set_dst(proc.pid())
            await sdl_system.output(sig)

        # Unexpected (will hit double star catch-all)
        for _ in range(2):
            sig = TestSignalB.create()
            sig.set_dst(proc.pid())
            await sdl_system.output(sig)

        # Process all signals
        for _ in range(5):
            signal = await sdl_system.get_next_signal()
            await sdl_system._process_signal(signal)

        # Verify signal routing by priority
        assert (
            proc.expected_count == 3
        )  # TestSignalA handled by exact match (Priority 1)
        assert (
            proc.unexpected_count == 2
        )  # TestSignalB handled by double star (Priority 4)
