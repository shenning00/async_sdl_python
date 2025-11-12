"""Test suite for SdlSystem.

This module tests SdlSystem event loop, signal routing, process management, and timer management.
"""

from typing import Optional

import pytest

from pysdl.id_generator import SdlIdGenerator
from pysdl.process import SdlProcess
from pysdl.signal import SdlSignal
from pysdl.state import start
from pysdl.system import SdlSystem
from pysdl.system_signals import SdlStartSignal
from pysdl.timer import SdlTimer


class TestSdlSystem:
    """Test cases for SdlSystem class."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Reset state before each test."""
        from pysdl.signal import SdlSignal
        from pysdl.timer import SdlTimer

        SdlIdGenerator._id = 0
        SdlSignal._id = None
        SdlTimer._id = None

    @pytest.fixture
    def sdl_system(self):
        """Provide a fresh SdlSystem instance for each test."""
        return SdlSystem()

    class TestProcess(SdlProcess):
        """Test process for system tests."""

        def _init_state_machine(self) -> None:
            """Initialize state machine."""
            self._event(start, SdlStartSignal, self.handle_start)

        async def handle_start(self, signal: SdlSignal) -> None:
            """Handle start signal."""

    def test_system_initial_state(self, sdl_system) -> None:
        """Test system initial state."""
        assert len(sdl_system.proc_map) == 0
        assert len(sdl_system.timer_map) == 0
        assert len(sdl_system.ready_list) == 0
        assert sdl_system._stop is False

    def test_system_register_process(self, sdl_system) -> None:
        """Test registering a process."""
        process = self.TestProcess(None, system=sdl_system)
        result = sdl_system.register(process)

        assert result is True
        assert process.pid() in sdl_system.proc_map
        assert sdl_system.proc_map[process.pid()] is process

    def test_system_register_none_process(self, sdl_system) -> None:
        """Test registering None raises ValidationError."""
        from pysdl.exceptions import ValidationError

        with pytest.raises(ValidationError):
            sdl_system.register(None)

    def test_system_register_duplicate_process(self, sdl_system) -> None:
        """Test registering same process twice."""
        process = self.TestProcess(None, system=sdl_system)
        result1 = sdl_system.register(process)
        result2 = sdl_system.register(process)

        assert result1 is True
        assert result2 is False  # Duplicate registration fails

    def test_system_unregister_process(self, sdl_system) -> None:
        """Test unregistering a process."""
        process = self.TestProcess(None, system=sdl_system)
        sdl_system.register(process)
        assert process.pid() in sdl_system.proc_map

        result = sdl_system.unregister(process)

        assert result is True
        assert process.pid() not in sdl_system.proc_map

    def test_system_unregister_none_process(self, sdl_system) -> None:
        """Test unregistering None raises ValidationError."""
        from pysdl.exceptions import ValidationError

        with pytest.raises(ValidationError):
            sdl_system.unregister(None)

    def test_system_unregister_removes_timers(self, sdl_system) -> None:
        """Test that unregistering process removes its timers."""
        process = self.TestProcess(None, system=sdl_system)
        sdl_system.register(process)

        timer = SdlTimer.create()
        timer.set_src(process.pid())
        sdl_system.startTimer(timer)

        assert process.pid() in sdl_system.timer_map

        sdl_system.unregister(process)

        assert process.pid() not in sdl_system.timer_map

    def test_system_unregister_removes_from_ready_list(self, sdl_system) -> None:
        """Test that unregistering removes process from ready list."""
        process = self.TestProcess(None, system=sdl_system)
        sdl_system.register(process)
        sdl_system.ready_list.append(process)
        sdl_system.ready_list.append(process)  # Add twice

        sdl_system.unregister(process)

        assert process not in sdl_system.ready_list

    @pytest.mark.asyncio
    async def test_system_enqueue_signal(self, sdl_system) -> None:
        """Test enqueueing a signal."""
        signal = SdlSignal.create()
        await sdl_system.enqueue(signal)

        assert not sdl_system._get_queue().empty()

    def test_system_lookup_proc_map(self, sdl_system) -> None:
        """Test looking up process in proc_map."""
        process = self.TestProcess(None, system=sdl_system)
        sdl_system.register(process)

        found = sdl_system.lookup_proc_map(process.pid())
        assert found is process

    def test_system_lookup_proc_map_not_found(self, sdl_system) -> None:
        """Test looking up non-existent process."""
        found = sdl_system.lookup_proc_map("NonExistent(0.0)")
        assert found is None

    @pytest.mark.asyncio
    async def test_system_output_signal(self, sdl_system) -> None:
        """Test outputting signal to a process."""
        process = self.TestProcess(None, system=sdl_system)
        sdl_system.register(process)

        signal = SdlSignal.create()
        signal.set_dst(process.pid())

        result = await sdl_system.output(signal)

        assert result is True
        assert process in sdl_system.ready_list
        assert not sdl_system._get_queue().empty()

    @pytest.mark.asyncio
    async def test_system_output_signal_to_nonexistent(self, sdl_system) -> None:
        """Test outputting signal to non-existent process."""
        signal = SdlSignal.create()
        signal.set_dst("NonExistent(0.0)")

        result = await sdl_system.output(signal)

        assert result is False

    @pytest.mark.asyncio
    async def test_system_output_none_signal(self, sdl_system) -> None:
        """Test outputting None signal raises ValidationError."""
        from pysdl.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await sdl_system.output(None)  # type: ignore

    def test_system_start_timer(self, sdl_system) -> None:
        """Test starting a timer."""
        timer = SdlTimer.create()
        timer.set_src("Process(0.0)")

        sdl_system.startTimer(timer)

        assert "Process(0.0)" in sdl_system.timer_map
        assert timer in sdl_system.timer_map["Process(0.0)"]

    def test_system_start_timer_none(self, sdl_system) -> None:
        """Test starting None timer raises ValidationError."""
        from pysdl.exceptions import ValidationError

        with pytest.raises(ValidationError):
            sdl_system.startTimer(None)

    def test_system_start_timer_multiple_for_same_process(self, sdl_system) -> None:
        """Test starting multiple timers for same process."""

        # Create different timer types to avoid duplicate prevention
        class Timer1(SdlTimer):
            _id: Optional[int] = None  # Override to ensure unique ID

        class Timer2(SdlTimer):
            _id: Optional[int] = None  # Override to ensure unique ID

        timer1 = Timer1.create()
        timer1.set_src("Process(0.0)")
        timer2 = Timer2.create()
        timer2.set_src("Process(0.0)")

        sdl_system.startTimer(timer1)
        sdl_system.startTimer(timer2)

        assert len(sdl_system.timer_map["Process(0.0)"]) == 2

    def test_system_start_timer_prevents_duplicates(self, sdl_system) -> None:
        """Test that starting same timer twice doesn't create duplicates."""
        timer = SdlTimer.create()
        timer.set_src("Process(0.0)")

        sdl_system.startTimer(timer)
        sdl_system.startTimer(timer)

        # Should only have one instance
        assert len(sdl_system.timer_map["Process(0.0)"]) == 1

    def test_system_stop_timer(self, sdl_system) -> None:
        """Test stopping a timer."""
        timer = SdlTimer.create()
        timer.set_src("Process(0.0)")
        sdl_system.startTimer(timer)

        result = sdl_system.stopTimer(timer)

        assert result is True
        assert "Process(0.0)" not in sdl_system.timer_map

    def test_system_stop_timer_none(self, sdl_system) -> None:
        """Test stopping None timer raises ValidationError."""
        from pysdl.exceptions import ValidationError

        with pytest.raises(ValidationError):
            sdl_system.stopTimer(None)

    def test_system_stop_timer_not_found(self, sdl_system) -> None:
        """Test stopping non-existent timer."""
        timer = SdlTimer.create()
        timer.set_src("Process(0.0)")

        result = sdl_system.stopTimer(timer)
        assert result is False

    def test_system_stop_timer_preserves_other_timers(self, sdl_system) -> None:
        """Test that stopping one timer preserves others."""

        # Create different timer types to avoid duplicate prevention
        class Timer1(SdlTimer):
            _id: Optional[int] = None  # Override to ensure unique ID

        class Timer2(SdlTimer):
            _id: Optional[int] = None  # Override to ensure unique ID

        timer1 = Timer1.create()
        timer1.set_src("Process(0.0)")
        timer2 = Timer2.create()
        timer2.set_src("Process(0.0)")

        sdl_system.startTimer(timer1)
        sdl_system.startTimer(timer2)

        sdl_system.stopTimer(timer1)

        assert "Process(0.0)" in sdl_system.timer_map
        assert timer2 in sdl_system.timer_map["Process(0.0)"]
        assert timer1 not in sdl_system.timer_map["Process(0.0)"]

    def test_system_stop_timer_cleans_empty_list(self, sdl_system) -> None:
        """Test that stopping last timer removes PID from timer_map."""
        timer = SdlTimer.create()
        timer.set_src("Process(0.0)")
        sdl_system.startTimer(timer)

        sdl_system.stopTimer(timer)

        assert "Process(0.0)" not in sdl_system.timer_map

    @pytest.mark.asyncio
    async def test_system_get_next_signal_returns_signal(self, sdl_system) -> None:
        """Test getting next signal when available."""
        signal = SdlSignal.create()
        await sdl_system.enqueue(signal)

        retrieved = await sdl_system.get_next_signal()
        assert retrieved is signal

    @pytest.mark.asyncio
    async def test_system_expire_timers(self, sdl_system) -> None:
        """Test timer expiry mechanism."""
        process = self.TestProcess(None, system=sdl_system)
        sdl_system.register(process)

        timer = SdlTimer.create()
        timer.set_src(process.pid())
        timer.set_dst(process.pid())
        timer.start(1000)  # 1 second

        sdl_system.startTimer(timer)

        # Expire timer by advancing time past duration
        await sdl_system.expire(2000)

        # Timer should be removed after expiry
        assert process.pid() not in sdl_system.timer_map

    @pytest.mark.asyncio
    async def test_system_expire_only_expired_timers(self, sdl_system) -> None:
        """Test that only expired timers are removed."""
        process = self.TestProcess(None, system=sdl_system)
        sdl_system.register(process)

        # Create different timer types to avoid duplicate prevention
        class Timer1(SdlTimer):
            _id: Optional[int] = None  # Override to ensure unique ID

        class Timer2(SdlTimer):
            _id: Optional[int] = None  # Override to ensure unique ID

        timer1 = Timer1.create()
        timer1.set_src(process.pid())
        timer1.set_dst(process.pid())
        timer1.start(1000)

        timer2 = Timer2.create()
        timer2.set_src(process.pid())
        timer2.set_dst(process.pid())
        timer2.start(5000)

        sdl_system.startTimer(timer1)
        sdl_system.startTimer(timer2)

        # Advance to 2 seconds - only timer1 should expire
        await sdl_system.expire(2000)

        assert timer2 in sdl_system.timer_map[process.pid()]
        assert timer1 not in sdl_system.timer_map[process.pid()]

    @pytest.mark.asyncio
    async def test_system_expire_sends_timer_signal(self, sdl_system) -> None:
        """Test that expired timer sends signal."""
        process = self.TestProcess(None, system=sdl_system)
        sdl_system.register(process)

        timer = SdlTimer.create()
        timer.set_src(process.pid())
        timer.set_dst(process.pid())
        timer.start(1000)

        sdl_system.startTimer(timer)

        # Clear queue first
        queue = sdl_system._get_queue()
        while not queue.empty():
            queue.get_nowait()

        await sdl_system.expire(2000)

        # Timer signal should be in queue
        assert not queue.empty()

    def test_system_stop(self, sdl_system) -> None:
        """Test stopping the system."""
        assert sdl_system._stop is False
        sdl_system.stop()
        assert sdl_system._stop is True

    def test_system_multiple_processes(self, sdl_system) -> None:
        """Test managing multiple processes."""
        p1 = self.TestProcess(None, system=sdl_system)
        p2 = self.TestProcess(None, system=sdl_system)
        p3 = self.TestProcess(None, system=sdl_system)

        sdl_system.register(p1)
        sdl_system.register(p2)
        sdl_system.register(p3)

        assert len(sdl_system.proc_map) == 3
        assert p1.pid() in sdl_system.proc_map
        assert p2.pid() in sdl_system.proc_map
        assert p3.pid() in sdl_system.proc_map

    @pytest.mark.asyncio
    async def test_system_signal_routing_between_processes(self, sdl_system) -> None:
        """Test signal routing between processes."""
        sender = self.TestProcess(None, system=sdl_system)
        receiver = self.TestProcess(None, system=sdl_system)

        sdl_system.register(sender)
        sdl_system.register(receiver)

        signal = SdlSignal.create()
        signal.set_src(sender.pid())
        signal.set_dst(receiver.pid())

        await sdl_system.output(signal)

        assert receiver in sdl_system.ready_list

    def test_system_timer_map_isolation(self, sdl_system) -> None:
        """Test that timer map isolates timers by PID."""
        timer1 = SdlTimer.create()
        timer1.set_src("Process1(0.0)")
        timer2 = SdlTimer.create()
        timer2.set_src("Process2(0.0)")

        sdl_system.startTimer(timer1)
        sdl_system.startTimer(timer2)

        assert len(sdl_system.timer_map) == 2
        assert timer1 in sdl_system.timer_map["Process1(0.0)"]
        assert timer2 in sdl_system.timer_map["Process2(0.0)"]

    @pytest.mark.asyncio
    async def test_system_ready_list_accumulates(self, sdl_system) -> None:
        """Test that ready list accumulates processes."""
        p1 = self.TestProcess(None, system=sdl_system)
        p2 = self.TestProcess(None, system=sdl_system)

        sdl_system.register(p1)
        sdl_system.register(p2)

        signal1 = SdlSignal.create()
        signal1.set_dst(p1.pid())
        await sdl_system.output(signal1)

        signal2 = SdlSignal.create()
        signal2.set_dst(p2.pid())
        await sdl_system.output(signal2)

        assert p1 in sdl_system.ready_list
        assert p2 in sdl_system.ready_list
