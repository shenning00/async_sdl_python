"""Test suite for SdlProcess.

This module tests process lifecycle, state transitions, signal handling, and parent-child relationships.
"""

from typing import Any, Optional

import pytest

from pysdl.exceptions import ValidationError
from pysdl.id_generator import SdlIdGenerator
from pysdl.process import SdlProcess, SdlSingletonProcess
from pysdl.signal import SdlSignal
from pysdl.state import SdlState, start
from pysdl.system import SdlSystem
from pysdl.system_signals import SdlStartSignal
from pysdl.timer import SdlTimer


class TestSdlProcess:
    """Test cases for SdlProcess class."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> None:
        """Reset state before each test."""
        from pysdl.signal import SdlSignal
        from pysdl.timer import SdlTimer

        SdlIdGenerator._id = 0
        # Reset Signal and Timer class IDs to prevent cross-test contamination
        SdlSignal._id = None
        SdlTimer._id = None
        # Reset process instance counter
        self.TestProcess._instance_count = 0

    @pytest.fixture
    def sdl_system(self) -> SdlSystem:
        """Provide a fresh SdlSystem instance for each test."""
        return SdlSystem()

    class TestProcess(SdlProcess):
        """Test process for basic functionality."""

        def _init_state_machine(self) -> None:
            """Initialize a minimal state machine."""
            self._event(start, SdlStartSignal, self.handle_start)

        async def handle_start(self, signal: SdlSignal) -> None:
            """Handle start signal."""

    class CounterProcess(SdlProcess):
        """Test process that counts signals."""

        def __init__(
            self, parent_pid: Optional[str], config_data: Optional[Any] = None
        ) -> None:
            super().__init__(parent_pid, config_data)
            self.count = 0

        def _init_state_machine(self) -> None:
            """Initialize state machine."""
            self._event(start, SdlStartSignal, self.handle_start)

        async def handle_start(self, signal: SdlSignal) -> None:
            """Handle start signal."""
            self.count += 1

    def test_process_creation_without_registration(self, sdl_system) -> None:
        """Test creating a process without registration."""
        process = self.TestProcess(None, system=sdl_system)
        assert process is not None
        assert isinstance(process, SdlProcess)

    @pytest.mark.asyncio
    async def test_process_create_with_registration(self, sdl_system) -> None:
        """Test creating and registering a process."""
        process = await self.TestProcess.create(None, system=sdl_system)
        assert process is not None
        assert process.pid() in sdl_system.proc_map

    def test_process_pid_format(self, sdl_system) -> None:
        """Test process PID format."""
        process = self.TestProcess(None, system=sdl_system)
        pid = process.pid()
        assert "TestProcess" in pid
        assert "(" in pid
        assert "." in pid
        assert ")" in pid

    def test_process_id_assignment(self, sdl_system) -> None:
        """Test that processes get unique IDs."""

        class Process1(SdlProcess):
            def _init_state_machine(self) -> None:
                pass

        class Process2(SdlProcess):
            def _init_state_machine(self) -> None:
                pass

        p1 = Process1(None, system=sdl_system)
        p2 = Process2(None, system=sdl_system)

        assert p1.id() != p2.id()

    def test_process_instance_count(self, sdl_system) -> None:
        """Test process instance counting."""
        p1 = self.TestProcess(None, system=sdl_system)
        p2 = self.TestProcess(None, system=sdl_system)
        p3 = self.TestProcess(None, system=sdl_system)

        assert p1.instance() == 1
        assert p2.instance() == 2
        assert p3.instance() == 3

    def test_process_name(self, sdl_system) -> None:
        """Test process name matches class name."""
        process = self.TestProcess(None, system=sdl_system)
        assert process.name() == "TestProcess"

    def test_process_parent(self, sdl_system) -> None:
        """Test process parent assignment."""
        process = self.TestProcess("Parent(0.0)", system=sdl_system)
        assert process.get_parent() == "Parent(0.0)"

    def test_process_set_parent(self, sdl_system) -> None:
        """Test setting process parent."""
        process = self.TestProcess(None, system=sdl_system)
        process.set_parent("NewParent(1.0)")
        assert process.get_parent() == "NewParent(1.0)"

    def test_process_initial_state(self, sdl_system) -> None:
        """Test initial process state is 'start'."""
        process = self.TestProcess(None, system=sdl_system)
        assert process.current_state() == start

    @pytest.mark.asyncio
    async def test_process_next_state(self, sdl_system) -> None:
        """Test changing process state."""
        process = self.TestProcess(None, system=sdl_system)
        new_state = SdlState("new_state")
        await process.next_state(new_state)
        assert process.current_state() == new_state

    @pytest.mark.asyncio
    async def test_process_next_state_same_state(self, sdl_system) -> None:
        """Test that setting same state doesn't trigger transition."""
        process = self.TestProcess(None, system=sdl_system)
        initial_state = process.current_state()
        await process.next_state(initial_state)
        assert process.current_state() == initial_state

    def test_process_build_pid(self, sdl_system) -> None:
        """Test build_pid class method."""
        pid = self.TestProcess.build_pid(5)
        assert "TestProcess" in pid
        assert "5" in pid

    def test_process_str_representation(self, sdl_system) -> None:
        """Test process string representation."""
        process = self.TestProcess(None, system=sdl_system)
        assert str(process) == process.pid()

    def test_process_repr(self, sdl_system) -> None:
        """Test process repr representation."""
        process = self.TestProcess(None, system=sdl_system)
        assert repr(process) == process.pid()

    @pytest.mark.asyncio
    async def test_process_output_signal(self, sdl_system) -> None:
        """Test sending signal to another process."""
        sender = await self.TestProcess.create(None, system=sdl_system)
        receiver = await self.TestProcess.create(None, system=sdl_system)

        test_signal = SdlSignal.create()
        result = await sender.output(test_signal, receiver.pid())

        assert result is True
        assert test_signal.src() == sender.pid()
        assert test_signal.dst() == receiver.pid()

    @pytest.mark.asyncio
    async def test_process_output_rejects_non_signal(self, sdl_system) -> None:
        """Test that output rejects non-signal objects."""
        process = await self.TestProcess.create(None, system=sdl_system)

        with pytest.raises(
            ValidationError, match="signal must be an instance of SdlSignal"
        ):
            await process.output("not a signal", "dest")  # type: ignore

    @pytest.mark.asyncio
    async def test_process_start_timer(self, sdl_system) -> None:
        """Test starting a timer."""
        process = await self.TestProcess.create(None, system=sdl_system)
        timer = SdlTimer.create()

        process.start_timer(timer, 1000)  # 1 second

        assert process.pid() in sdl_system.timer_map
        assert timer in sdl_system.timer_map[process.pid()]
        assert timer.src() == process.pid()
        assert timer.dst() == process.pid()

    @pytest.mark.asyncio
    async def test_process_start_timer_rejects_non_timer(self, sdl_system) -> None:
        """Test that start_timer rejects non-timer objects."""
        process = await self.TestProcess.create(None, system=sdl_system)

        with pytest.raises(
            ValidationError, match="timer must be an instance of SdlTimer"
        ):
            process.start_timer("not a timer", 1000)  # type: ignore

    @pytest.mark.asyncio
    async def test_process_stop_timer(self, sdl_system) -> None:
        """Test stopping a timer."""
        process = await self.TestProcess.create(None, system=sdl_system)
        timer = SdlTimer.create()

        process.start_timer(timer, 1000)
        assert timer in sdl_system.timer_map[process.pid()]

        process.stop_timer(timer)
        assert process.pid() not in sdl_system.timer_map

    @pytest.mark.asyncio
    async def test_process_stop_timer_rejects_non_timer(self, sdl_system) -> None:
        """Test that stop_timer rejects non-timer objects."""
        process = await self.TestProcess.create(None, system=sdl_system)

        with pytest.raises(
            ValidationError, match="timer must be an instance of SdlTimer"
        ):
            process.stop_timer("not a timer")  # type: ignore

    @pytest.mark.asyncio
    async def test_process_stop(self, sdl_system) -> None:
        """Test process stop sends stopping signal."""
        process = await self.TestProcess.create(None, system=sdl_system)
        await process.stop()

        # Check that stopping signal is queued
        assert not sdl_system._get_queue().empty()

    @pytest.mark.asyncio
    async def test_process_stop_process(self, sdl_system) -> None:
        """Test process cleanup."""
        process = await self.TestProcess.create(None, system=sdl_system)
        pid = process.pid()
        assert pid in sdl_system.proc_map

        process.stop_process()
        assert pid not in sdl_system.proc_map

    @pytest.mark.asyncio
    async def test_process_input(self, sdl_system) -> None:
        """Test process input queues signal."""
        process = await self.TestProcess.create(None, system=sdl_system)
        signal = SdlSignal.create()

        await process.input(signal)
        assert not sdl_system._get_queue().empty()

    @pytest.mark.asyncio
    async def test_process_input_rejects_non_signal(self, sdl_system) -> None:
        """Test that input rejects non-signal objects."""
        process = await self.TestProcess.create(None, system=sdl_system)

        with pytest.raises(
            ValidationError, match="signal must be an instance of SdlSignal"
        ):
            await process.input("not a signal")  # type: ignore

    @pytest.mark.asyncio
    async def test_process_save_signal(self, sdl_system) -> None:
        """Test saving signals."""
        process = await self.TestProcess.create(None, system=sdl_system)
        signal = SdlSignal.create()

        await process.save_signal(signal)
        assert signal in process._save_signals

    def test_process_lookup_transition(self, sdl_system) -> None:
        """Test looking up transition handlers."""
        process = self.TestProcess(None, system=sdl_system)
        process._init_state_machine()  # Initialize state machine manually
        handler = process.lookup_transition(SdlStartSignal.create())
        assert handler is not None

    def test_process_lookup_transition_not_found(self, sdl_system) -> None:
        """Test looking up non-existent transition."""

        class UnknownSignal(SdlSignal):
            pass

        process = self.TestProcess(None, system=sdl_system)
        handler = process.lookup_transition(UnknownSignal.create())
        assert handler is None

    def test_process_lookup_transition_none_signal(self, sdl_system) -> None:
        """Test looking up transition with None signal."""
        process = self.TestProcess(None, system=sdl_system)

        with pytest.raises(
            ValidationError, match="Cannot lookup transition for None signal"
        ):
            process.lookup_transition(None)

    @pytest.mark.asyncio
    async def test_process_with_config_data(self, sdl_system) -> None:
        """Test creating process with config data."""
        config = {"key": "value", "count": 42}
        process = await self.TestProcess.create(None, config, system=sdl_system)
        assert process._config_data == config

    def test_process_init_state_machine_required(self, sdl_system) -> None:
        """Test that _init_state_machine must be implemented."""

        class IncompleteProcess(SdlProcess):
            pass

        with pytest.raises(NotImplementedError):
            process = IncompleteProcess(None, system=sdl_system)
            process._init_state_machine()

    @pytest.mark.asyncio
    async def test_process_create_without_system(self) -> None:
        """Test that create() raises ValidationError when system is None."""
        with pytest.raises(
            ValidationError, match="Process creation requires a system instance"
        ):
            await self.TestProcess.create(None, system=None)

    def test_process_init_without_system(self) -> None:
        """Test that __init__() raises ValidationError when system is None."""
        with pytest.raises(
            ValidationError, match="SdlProcess requires a system instance"
        ):
            self.TestProcess(None, system=None)

    @pytest.mark.asyncio
    async def test_process_next_state_none_raises(self, sdl_system) -> None:
        """Test that next_state raises ValidationError for None state."""
        process = await self.TestProcess.create(None, system=sdl_system)

        with pytest.raises(ValidationError, match="Cannot transition to None state"):
            await process.next_state(None)  # type: ignore

    @pytest.mark.asyncio
    async def test_process_next_state_invalid_type_raises(self, sdl_system) -> None:
        """Test that next_state raises ValidationError for invalid state type."""
        process = await self.TestProcess.create(None, system=sdl_system)

        with pytest.raises(ValidationError, match="Invalid state type"):
            await process.next_state("not_a_state")  # type: ignore

    @pytest.mark.asyncio
    async def test_process_next_state_with_saved_signals(self, sdl_system) -> None:
        """Test that saved signals are sent during state transition."""
        process = await self.TestProcess.create(None, system=sdl_system)
        receiver = await self.TestProcess.create(None, system=sdl_system)

        # Save a signal
        signal = SdlSignal.create()
        signal.set_dst(receiver.pid())
        await process.save_signal(signal)

        # Transition to new state should send saved signals
        new_state = SdlState("new_state")
        await process.next_state(new_state)

        # Verify signal was sent (check queue is not empty)
        assert not sdl_system._get_queue().empty()

    @pytest.mark.asyncio
    async def test_process_next_state_with_saved_signals_exception(
        self, sdl_system
    ) -> None:
        """Test exception handling when sending saved signals fails."""
        process = await self.TestProcess.create(None, system=sdl_system)

        # Create a signal with invalid destination that will cause exception
        signal = SdlSignal.create()
        signal.set_dst("NonExistentProcess(99.99)")
        await process.save_signal(signal)

        # Mock system.output to raise an exception
        original_output = sdl_system.output

        async def mock_output(sig):
            raise RuntimeError("Simulated output failure")

        sdl_system.output = mock_output  # type: ignore

        # Transition should handle exception gracefully
        new_state = SdlState("new_state")
        await process.next_state(new_state)

        # Restore original
        sdl_system.output = original_output

        # Should have transitioned despite error
        assert process.current_state() == new_state

    @pytest.mark.asyncio
    async def test_process_output_invalid_dst_empty(self, sdl_system) -> None:
        """Test that output raises ValidationError for empty dst."""
        process = await self.TestProcess.create(None, system=sdl_system)
        signal = SdlSignal.create()

        with pytest.raises(ValidationError, match="Invalid destination PID"):
            await process.output(signal, "")

    @pytest.mark.asyncio
    async def test_process_output_invalid_dst_none(self, sdl_system) -> None:
        """Test that output raises ValidationError for None dst."""
        process = await self.TestProcess.create(None, system=sdl_system)
        signal = SdlSignal.create()

        with pytest.raises(ValidationError, match="Invalid destination PID"):
            await process.output(signal, None)  # type: ignore

    @pytest.mark.asyncio
    async def test_process_start_timer_negative_msec(self, sdl_system) -> None:
        """Test that start_timer raises TimerError for negative duration."""
        from pysdl.exceptions import TimerError

        process = await self.TestProcess.create(None, system=sdl_system)
        timer = SdlTimer.create()

        with pytest.raises(TimerError, match="Timer duration cannot be negative"):
            process.start_timer(timer, -1000)

    @pytest.mark.asyncio
    async def test_process_start_timer_abs(self, sdl_system) -> None:
        """Test starting a timer with absolute time."""
        process = await self.TestProcess.create(None, system=sdl_system)
        timer = SdlTimer.create()

        # Use a valid absolute time (current time in seconds + 1)
        from time import time

        abs_time = int(time()) + 1

        process.start_timer_abs(timer, abs_time)

        assert process.pid() in sdl_system.timer_map
        assert timer in sdl_system.timer_map[process.pid()]

    @pytest.mark.asyncio
    async def test_process_start_timer_abs_rejects_non_timer(self, sdl_system) -> None:
        """Test that start_timer_abs rejects non-timer objects."""
        process = await self.TestProcess.create(None, system=sdl_system)

        with pytest.raises(
            ValidationError, match="timer must be an instance of SdlTimer"
        ):
            process.start_timer_abs("not a timer", 1000)  # type: ignore

    @pytest.mark.asyncio
    async def test_process_start_timer_abs_invalid_time(self, sdl_system) -> None:
        """Test that start_timer_abs raises TimerError for invalid time."""
        from pysdl.exceptions import TimerError

        process = await self.TestProcess.create(None, system=sdl_system)
        timer = SdlTimer.create()

        with pytest.raises(TimerError, match="Timer absolute time must be positive"):
            process.start_timer_abs(timer, 0)

        with pytest.raises(TimerError, match="Timer absolute time must be positive"):
            process.start_timer_abs(timer, -1)

    @pytest.mark.asyncio
    async def test_process_stop_timer_not_active(self, sdl_system) -> None:
        """Test stopping a timer that was never started."""
        process = await self.TestProcess.create(None, system=sdl_system)
        timer = SdlTimer.create()

        # Stop timer that was never started - should log warning but not raise
        process.stop_timer(timer)

        # No exception should be raised

    @pytest.mark.asyncio
    async def test_process_stop_timer_exception_handling(self, sdl_system) -> None:
        """Test exception handling in stop_timer."""
        process = await self.TestProcess.create(None, system=sdl_system)
        timer = SdlTimer.create()

        # Start timer
        process.start_timer(timer, 1000)

        # Mock system.stopTimer to raise exception
        original_stop = sdl_system.stopTimer

        def mock_stop_timer(t):
            raise RuntimeError("Simulated error")

        sdl_system.stopTimer = mock_stop_timer  # type: ignore

        # Should handle exception gracefully
        process.stop_timer(timer)

        # Restore original
        sdl_system.stopTimer = original_stop

    def test_process_done_method(self, sdl_system) -> None:
        """Test _done() method calls FSM done."""
        process = self.TestProcess(None, system=sdl_system)
        process._init_state_machine()

        # Call _done - it should call FSM.done() without error
        process._done()

        # Verify FSM.done() was called by checking it returns True
        assert process._FSM.done() is True


class TestSdlSingletonProcess:
    """Test cases for SdlSingletonProcess class."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> None:
        """Reset state before each test."""
        SdlIdGenerator._id = 0
        # Clear singleton instances
        SdlSingletonProcess._singleton_instance = None

    @pytest.fixture
    def sdl_system(self) -> SdlSystem:
        """Provide a fresh SdlSystem instance for each test."""
        return SdlSystem()

    class TestSingleton(SdlSingletonProcess):
        """Test singleton process."""

        def _init_state_machine(self) -> None:
            """Initialize state machine."""
            self._event(start, SdlStartSignal, self.handle_start)

        async def handle_start(self, signal: SdlSignal) -> None:
            """Handle start signal."""

    @pytest.mark.asyncio
    async def test_singleton_creation(self, sdl_system) -> None:
        """Test singleton process creation."""
        process = await self.TestSingleton.create(None, system=sdl_system)
        assert process is not None
        assert isinstance(process, SdlSingletonProcess)

    @pytest.mark.asyncio
    async def test_singleton_returns_same_instance(self, sdl_system) -> None:
        """Test that singleton returns same instance."""
        process1 = await self.TestSingleton.create(None, system=sdl_system)
        process2 = await self.TestSingleton.create(None, system=sdl_system)

        assert process1 is process2
        assert id(process1) == id(process2)

    @pytest.mark.asyncio
    async def test_singleton_pid(self, sdl_system) -> None:
        """Test singleton PID format."""
        process = await self.TestSingleton.create(None, system=sdl_system)
        pid = process.pid()
        assert "TestSingleton" in pid
        assert ".0)" in pid  # Instance should always be 0

    def test_singleton_single_pid_method(self) -> None:
        """Test singleton single_pid class method."""
        pid = self.TestSingleton.single_pid()
        assert "TestSingleton" in pid
        assert ".0)" in pid

    @pytest.mark.asyncio
    async def test_singleton_no_instance_increment(self, sdl_system) -> None:
        """Test that singleton doesn't increment instance count."""
        process1 = await self.TestSingleton.create(None, system=sdl_system)
        process2 = await self.TestSingleton.create(None, system=sdl_system)

        # Both should have instance 0
        assert process1.instance() == 0
        assert process2.instance() == 0

    @pytest.mark.asyncio
    async def test_singleton_create_without_system(self) -> None:
        """Test that singleton create() raises ValidationError when system is None."""
        # Reset singleton instance
        self.TestSingleton._singleton_instance = None

        with pytest.raises(
            ValidationError,
            match="Singleton process creation requires a system instance",
        ):
            await self.TestSingleton.create(None, system=None)

    def test_singleton_init_state_machine_not_implemented(self) -> None:
        """Test that _init_state_machine must be implemented in singleton."""

        class IncompleteSingleton(SdlSingletonProcess):
            pass

        with pytest.raises(NotImplementedError):
            # Call the parent class method directly
            singleton = object.__new__(IncompleteSingleton)
            singleton._init_state_machine()
