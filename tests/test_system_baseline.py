"""Baseline integration tests for SdlSystem instance-based behavior.

These tests verify the instance-based SdlSystem architecture, ensuring that:
- Processes register with specific system instances
- Signal delivery and routing work through system instances
- Timer management operates on system instances
- Multi-process interactions work correctly with system instances
- Multiple system instances are properly isolated from each other

Tests are grouped by functional areas:
- Process registration and lifecycle
- Signal delivery and routing
- Timer management and expiration
- Multi-process interactions
- Multi-system isolation
"""

import pytest

from pysdl import (
    SdlProcess,
    SdlSignal,
    SdlStartSignal,
    SdlSystem,
    SdlTimer,
)
from pysdl.state import start


class MessageSignal(SdlSignal):
    """Test message signal."""


class TimeoutTimer(SdlTimer):
    """Test timeout timer."""


class BaselineTestProcess(SdlProcess):
    """Test process for baseline tests."""

    def _init_state_machine(self) -> None:
        """Initialize state machine."""
        self._event(start, SdlStartSignal, self.handle_start)
        self._event(start, MessageSignal, self.handle_message)
        self._event(start, TimeoutTimer, self.handle_timeout)

    async def handle_start(self, signal: SdlSignal) -> None:
        """Handle start signal."""

    async def handle_message(self, signal: SdlSignal) -> None:
        """Handle message signal."""

    async def handle_timeout(self, signal: SdlSignal) -> None:
        """Handle timeout signal."""


class TestSystemBaseline:
    """Test SdlSystem instance-based behavior."""

    @pytest.fixture
    def sdl_system(self):
        """Provide a fresh SdlSystem instance for each test."""
        return SdlSystem()

    async def test_baseline_process_registration_with_global_system(self, sdl_system):
        """Verify process registration works with system instance.

        This tests that:
        - Process.create() with system parameter registers with that system instance
        - Process appears in system.proc_map
        - PID is correctly formatted and unique
        """
        process = await BaselineTestProcess.create(None, system=sdl_system)

        # Process should be registered in system's proc_map
        assert process.pid() in sdl_system.proc_map
        assert sdl_system.proc_map[process.pid()] is process

        # PID should be properly formatted
        assert "BaselineTestProcess" in process.pid()

        # System should have exactly one process
        assert len(sdl_system.proc_map) == 1

    async def test_baseline_process_unregistration_cleans_global_state(
        self, sdl_system
    ):
        """Verify process unregistration cleans up all system state.

        This tests that:
        - Process.stop() unregisters from system instance
        - Process is removed from proc_map
        - All timers for process are removed
        - Process is removed from ready_list
        """
        process = await BaselineTestProcess.create(None, system=sdl_system)

        # Add a timer
        timer = TimeoutTimer.create()
        timer.set_src(process.pid())
        timer.set_dst(process.pid())
        sdl_system.startTimer(timer)

        # Add to ready list
        sdl_system.ready_list.append(process)

        # Verify setup
        assert process.pid() in sdl_system.proc_map
        assert process.pid() in sdl_system.timer_map
        assert process in sdl_system.ready_list

        # Unregister process
        sdl_system.unregister(process)

        # Verify all traces removed
        assert process.pid() not in sdl_system.proc_map
        assert process.pid() not in sdl_system.timer_map
        assert process not in sdl_system.ready_list

    async def test_baseline_signal_delivery_to_registered_process(self, sdl_system):
        """Verify signal delivery works through system instance.

        This tests that:
        - system.output() enqueues signal
        - Destination process is added to ready_list
        - Signal can be retrieved from system queue
        """
        process = await BaselineTestProcess.create(None, system=sdl_system)

        # Drain the start signal that was automatically sent
        _ = await sdl_system.get_next_signal()
        sdl_system.ready_list.clear()

        # Create and send signal
        signal = MessageSignal.create()
        signal.set_src(process.pid())
        signal.set_dst(process.pid())

        result = await sdl_system.output(signal)

        # Verify signal was accepted
        assert result is True

        # Verify process is in ready list
        assert process in sdl_system.ready_list

        # Verify signal in queue
        assert not sdl_system._get_queue().empty()

        # Retrieve and verify signal
        retrieved_signal = await sdl_system.get_next_signal()
        assert retrieved_signal is signal
        assert retrieved_signal.dst() == process.pid()

    async def test_baseline_signal_to_nonexistent_process_sends_error(self, sdl_system):
        """Verify error signal sent when destination doesn't exist.

        This tests that:
        - Sending to nonexistent PID returns False
        - Error signal is generated and sent to source
        - Source process is added to ready_list if it exists
        """
        source = await BaselineTestProcess.create(None, system=sdl_system)

        # Create signal to nonexistent destination
        signal = MessageSignal.create()
        signal.set_src(source.pid())
        signal.set_dst("NonExistent(0.0)")

        result = await sdl_system.output(signal)

        # Output should return False for nonexistent destination
        assert result is False

        # Error signal should be in queue
        assert not sdl_system._get_queue().empty()

        # Source should be in ready list
        assert source in sdl_system.ready_list

        # Retrieve error signal
        error_signal = await sdl_system.get_next_signal()
        assert error_signal.dst() == source.pid()

    async def test_baseline_timer_management_in_global_system(self, sdl_system):
        """Verify timer registration and management in system instance.

        This tests that:
        - system.startTimer() adds timer to system timer_map
        - Multiple timers per process are supported
        - Duplicate timers are prevented
        - system.stopTimer() removes specific timer
        """
        process = await BaselineTestProcess.create(None, system=sdl_system)

        # Create and start timer
        timer1 = TimeoutTimer.create()
        timer1.set_src(process.pid())
        timer1.set_dst(process.pid())
        sdl_system.startTimer(timer1)

        # Verify timer added
        assert process.pid() in sdl_system.timer_map
        assert timer1 in sdl_system.timer_map[process.pid()]

        # Add second timer
        timer2 = TimeoutTimer.create()
        timer2.set_src(process.pid())
        timer2.set_dst(process.pid())
        timer2.set_appcorr(1)  # Different appcorr to allow both
        sdl_system.startTimer(timer2)

        # Verify both timers present
        assert len(sdl_system.timer_map[process.pid()]) == 2

        # Try to add duplicate timer1
        sdl_system.startTimer(timer1)

        # Should still be only 2 timers
        assert len(sdl_system.timer_map[process.pid()]) == 2

        # Stop timer1
        result = sdl_system.stopTimer(timer1)
        assert result is True

        # Verify only timer2 remains
        assert len(sdl_system.timer_map[process.pid()]) == 1
        assert timer2 in sdl_system.timer_map[process.pid()]
        assert timer1 not in sdl_system.timer_map[process.pid()]

    async def test_baseline_timer_expiration_generates_signals(self, sdl_system):
        """Verify timer expiration generates signals in system queue.

        This tests that:
        - system.expire() processes expired timers
        - Expired timers generate signals
        - Expired timers are removed from timer_map
        - Non-expired timers remain in timer_map
        """
        process = await BaselineTestProcess.create(None, system=sdl_system)

        # Drain the start signal
        _ = await sdl_system.get_next_signal()

        # Create timer that will expire
        timer1 = TimeoutTimer.create()
        timer1.set_src(process.pid())
        timer1.set_dst(process.pid())
        timer1.start(100)  # Expires at 100ms
        sdl_system.startTimer(timer1)

        # Create timer that won't expire
        timer2 = TimeoutTimer.create()
        timer2.set_src(process.pid())
        timer2.set_dst(process.pid())
        timer2.set_appcorr(1)
        timer2.start(1000)  # Expires at 1000ms
        sdl_system.startTimer(timer2)

        # Verify both timers present
        assert len(sdl_system.timer_map[process.pid()]) == 2

        # Expire timers at 200ms
        await sdl_system.expire(200)

        # Only timer2 should remain
        assert len(sdl_system.timer_map[process.pid()]) == 1
        assert timer2 in sdl_system.timer_map[process.pid()]
        assert timer1 not in sdl_system.timer_map[process.pid()]

        # Signal should be in queue
        assert not sdl_system._get_queue().empty()

        # Retrieve timer signal
        timer_signal = await sdl_system.get_next_signal()
        assert isinstance(timer_signal, TimeoutTimer)
        assert timer_signal.dst() == process.pid()

    async def test_baseline_multiple_processes_isolated_state(self, sdl_system):
        """Verify multiple processes maintain isolated state in system instance.

        This tests that:
        - Multiple processes can coexist in proc_map
        - Each process has separate timer_map entry
        - Signals route to correct process
        - Unregistering one process doesn't affect others
        """
        process1 = await BaselineTestProcess.create(None, system=sdl_system)
        process2 = await BaselineTestProcess.create(None, system=sdl_system)
        process3 = await BaselineTestProcess.create(None, system=sdl_system)

        # Drain start signals and clear ready list
        _ = await sdl_system.get_next_signal()
        _ = await sdl_system.get_next_signal()
        _ = await sdl_system.get_next_signal()
        sdl_system.ready_list.clear()

        # Verify all registered
        assert len(sdl_system.proc_map) == 3
        assert process1.pid() in sdl_system.proc_map
        assert process2.pid() in sdl_system.proc_map
        assert process3.pid() in sdl_system.proc_map

        # Add timers to each
        timer1 = TimeoutTimer.create()
        timer1.set_src(process1.pid())
        timer1.set_dst(process1.pid())
        sdl_system.startTimer(timer1)

        timer2 = TimeoutTimer.create()
        timer2.set_src(process2.pid())
        timer2.set_dst(process2.pid())
        sdl_system.startTimer(timer2)

        # Verify separate timer entries
        assert process1.pid() in sdl_system.timer_map
        assert process2.pid() in sdl_system.timer_map
        assert process3.pid() not in sdl_system.timer_map  # No timer for process3

        # Send signal to process2
        signal = MessageSignal.create()
        signal.set_src(process1.pid())
        signal.set_dst(process2.pid())
        await sdl_system.output(signal)

        # Verify process2 in ready list
        assert process2 in sdl_system.ready_list
        assert process1 not in sdl_system.ready_list
        assert process3 not in sdl_system.ready_list

        # Unregister process1
        sdl_system.unregister(process1)

        # Verify only process1 removed
        assert process1.pid() not in sdl_system.proc_map
        assert process2.pid() in sdl_system.proc_map
        assert process3.pid() in sdl_system.proc_map

        # Verify process1 timers removed, process2 timers remain
        assert process1.pid() not in sdl_system.timer_map
        assert process2.pid() in sdl_system.timer_map

    async def test_baseline_process_communication_through_global_system(
        self, sdl_system
    ):
        """Verify inter-process communication works through system instance.

        This tests that:
        - Process A can send signals to Process B
        - Signals are properly routed through system queue
        - Both processes maintain independent state
        """
        sender = await BaselineTestProcess.create(None, system=sdl_system)
        receiver = await BaselineTestProcess.create(None, system=sdl_system)

        # Drain start signals and clear ready list
        _ = await sdl_system.get_next_signal()
        _ = await sdl_system.get_next_signal()
        sdl_system.ready_list.clear()

        # Sender sends message to receiver
        message = MessageSignal.create()
        message.set_src(sender.pid())
        message.set_dst(receiver.pid())

        result = await sdl_system.output(message)

        # Verify success
        assert result is True

        # Verify receiver in ready list (not sender)
        assert receiver in sdl_system.ready_list
        assert sender not in sdl_system.ready_list

        # Retrieve signal
        retrieved = await sdl_system.get_next_signal()
        assert retrieved.src() == sender.pid()
        assert retrieved.dst() == receiver.pid()

        # Verify we can look up both processes
        found_sender = sdl_system.lookup_proc_map(sender.pid())
        found_receiver = sdl_system.lookup_proc_map(receiver.pid())
        assert found_sender is sender
        assert found_receiver is receiver

    async def test_baseline_stop_flag_in_global_system(self, sdl_system):
        """Verify system instance stop flag behavior.

        This tests that:
        - system._stop starts as False
        - system.stop() sets flag to True
        - Flag is accessible on system instance
        """
        # Initial state
        assert sdl_system._stop is False

        # Stop system
        sdl_system.stop()

        # Verify flag set
        assert sdl_system._stop is True

    async def test_baseline_queue_initialization_lazy(self, sdl_system):
        """Verify system queue is lazily initialized.

        This tests that:
        - Queue starts as None
        - First access creates queue via _get_queue()
        - Same queue instance used throughout
        """
        # Queue should start as None
        assert sdl_system._queue is None

        # First access creates queue
        queue1 = sdl_system._get_queue()
        assert queue1 is not None
        assert sdl_system._queue is queue1

        # Second access returns same queue
        queue2 = sdl_system._get_queue()
        assert queue2 is queue1

        # Queue should be usable
        signal = MessageSignal.create()
        await sdl_system.enqueue(signal)
        assert not queue1.empty()

    async def test_baseline_ready_list_accumulates_processes(self, sdl_system):
        """Verify ready list accumulates processes waiting for execution.

        This tests that:
        - Processes receiving signals are added to ready_list
        - Same process can appear multiple times if it receives multiple signals
        - Ready list is a simple list, not a set
        """
        process = await BaselineTestProcess.create(None, system=sdl_system)

        # Drain start signal and clear ready list
        _ = await sdl_system.get_next_signal()
        sdl_system.ready_list.clear()

        # Send multiple signals
        signal1 = MessageSignal.create()
        signal1.set_src(process.pid())
        signal1.set_dst(process.pid())
        await sdl_system.output(signal1)

        signal2 = MessageSignal.create()
        signal2.set_src(process.pid())
        signal2.set_dst(process.pid())
        await sdl_system.output(signal2)

        # Process should appear twice in ready list
        ready_count = sdl_system.ready_list.count(process)
        assert ready_count == 2

        # Verify both signals in queue
        assert sdl_system._get_queue().qsize() == 2

    async def test_multiple_systems_isolated_process_maps(self):
        """Verify multiple system instances have completely isolated process maps.

        This tests that:
        - Creating two separate SdlSystem instances
        - Processes created in system1 only appear in system1.proc_map
        - Processes created in system2 only appear in system2.proc_map
        - No cross-contamination between systems
        """
        system1 = SdlSystem()
        system2 = SdlSystem()

        # Create process in system1
        process1 = await BaselineTestProcess.create(None, system=system1)

        # Verify it's ONLY in system1, not system2
        assert process1.pid() in system1.proc_map
        assert process1.pid() not in system2.proc_map
        assert len(system1.proc_map) == 1
        assert len(system2.proc_map) == 0

        # Create process in system2
        process2 = await BaselineTestProcess.create(None, system=system2)

        # Verify isolation
        assert process2.pid() in system2.proc_map
        assert process2.pid() not in system1.proc_map
        assert len(system1.proc_map) == 1
        assert len(system2.proc_map) == 1

        # Verify they're different processes
        assert process1 is not process2
        assert process1.pid() != process2.pid()

    async def test_multiple_systems_isolated_timer_maps(self):
        """Verify multiple system instances have isolated timer maps.

        This tests that:
        - Timers started in system1 only appear in system1.timer_map
        - Timers started in system2 only appear in system2.timer_map
        - Timer expiration only affects the correct system
        """
        system1 = SdlSystem()
        system2 = SdlSystem()

        # Create processes in each system
        process1 = await BaselineTestProcess.create(None, system=system1)
        process2 = await BaselineTestProcess.create(None, system=system2)

        # Create and start timer in system1
        timer1 = TimeoutTimer.create()
        timer1.set_src(process1.pid())
        timer1.set_dst(process1.pid())
        system1.startTimer(timer1)

        # Create and start timer in system2
        timer2 = TimeoutTimer.create()
        timer2.set_src(process2.pid())
        timer2.set_dst(process2.pid())
        system2.startTimer(timer2)

        # Verify isolation
        assert process1.pid() in system1.timer_map
        assert process1.pid() not in system2.timer_map
        assert process2.pid() in system2.timer_map
        assert process2.pid() not in system1.timer_map

        # Verify correct timers in correct systems
        assert timer1 in system1.timer_map[process1.pid()]
        assert timer2 in system2.timer_map[process2.pid()]

    async def test_multiple_systems_isolated_queues(self):
        """Verify multiple system instances have completely isolated signal queues.

        This tests that:
        - Signals sent in system1 only appear in system1's queue
        - Signals sent in system2 only appear in system2's queue
        - No cross-contamination of signals between systems
        """
        system1 = SdlSystem()
        system2 = SdlSystem()

        # Create processes in each system
        process1 = await BaselineTestProcess.create(None, system=system1)
        process2 = await BaselineTestProcess.create(None, system=system2)

        # Drain start signals
        _ = await system1.get_next_signal()
        _ = await system2.get_next_signal()

        # Send signal in system1
        signal1 = MessageSignal.create()
        signal1.set_src(process1.pid())
        signal1.set_dst(process1.pid())
        await system1.output(signal1)

        # Send signal in system2
        signal2 = MessageSignal.create()
        signal2.set_src(process2.pid())
        signal2.set_dst(process2.pid())
        await system2.output(signal2)

        # Verify each system has exactly one signal
        assert system1._get_queue().qsize() == 1
        assert system2._get_queue().qsize() == 1

        # Retrieve signals and verify they're from the correct systems
        retrieved1 = await system1.get_next_signal()
        retrieved2 = await system2.get_next_signal()

        assert retrieved1 is signal1
        assert retrieved2 is signal2
        assert retrieved1.dst() == process1.pid()
        assert retrieved2.dst() == process2.pid()

    async def test_multiple_systems_isolated_ready_lists(self):
        """Verify multiple system instances have isolated ready lists.

        This tests that:
        - Processes added to ready_list in system1 don't appear in system2
        - Processes added to ready_list in system2 don't appear in system1
        - Each system maintains its own ready list
        """
        system1 = SdlSystem()
        system2 = SdlSystem()

        # Create processes in each system
        process1 = await BaselineTestProcess.create(None, system=system1)
        process2 = await BaselineTestProcess.create(None, system=system2)

        # Drain start signals and clear ready lists
        _ = await system1.get_next_signal()
        _ = await system2.get_next_signal()
        system1.ready_list.clear()
        system2.ready_list.clear()

        # Send signal to process1 (adds to system1's ready list)
        signal1 = MessageSignal.create()
        signal1.set_src(process1.pid())
        signal1.set_dst(process1.pid())
        await system1.output(signal1)

        # Verify process1 only in system1's ready list
        assert process1 in system1.ready_list
        assert process1 not in system2.ready_list
        assert len(system1.ready_list) == 1
        assert len(system2.ready_list) == 0

        # Send signal to process2 (adds to system2's ready list)
        signal2 = MessageSignal.create()
        signal2.set_src(process2.pid())
        signal2.set_dst(process2.pid())
        await system2.output(signal2)

        # Verify isolation
        assert process2 in system2.ready_list
        assert process2 not in system1.ready_list
        assert len(system1.ready_list) == 1
        assert len(system2.ready_list) == 1

    async def test_multiple_systems_independent_stop_flags(self):
        """Verify multiple system instances have independent stop flags.

        This tests that:
        - Stopping system1 doesn't affect system2
        - Each system maintains its own _stop flag
        """
        system1 = SdlSystem()
        system2 = SdlSystem()

        # Both should start with _stop = False
        assert system1._stop is False
        assert system2._stop is False

        # Stop system1
        system1.stop()

        # Verify only system1 is stopped
        assert system1._stop is True
        assert system2._stop is False

        # Stop system2
        system2.stop()

        # Verify both are now stopped
        assert system1._stop is True
        assert system2._stop is True
