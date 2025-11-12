"""Integration tests for async_sdl_python.

This module tests full scenarios including:
- Complete ping-pong communication
- Process creation and destruction
- Complex state machines
- Timer-based transitions
- Error conditions
"""

from typing import Any, Optional

import pytest

from pysdl.id_generator import SdlIdGenerator
from pysdl.process import SdlProcess
from pysdl.signal import SdlSignal
from pysdl.state import SdlState, start
from pysdl.system import SdlSystem
from pysdl.system_signals import SdlStartSignal, SdlStoppingSignal
from pysdl.timer import SdlTimer


class TestIntegration:
    """Integration test cases."""

    @pytest.fixture(autouse=True)
    def reset_system(self) -> None:
        """Reset system state before each test."""
        SdlIdGenerator._id = 0
        # Reset Signal and Timer class IDs to prevent cross-test contamination
        SdlSignal._id = None
        SdlTimer._id = None

    @pytest.fixture
    def sdl_system(self) -> SdlSystem:
        """Provide a fresh SdlSystem instance for each test."""
        return SdlSystem()

    class SimplePingPongProcess(SdlProcess):
        """Simplified ping-pong process for testing."""

        class PingSignal(SdlSignal):
            """Ping signal."""

        class PongSignal(SdlSignal):
            """Pong signal."""

        class StopSignal(SdlSignal):
            """Stop signal."""

        state_wait_ping = SdlState("wait_ping")
        state_wait_pong = SdlState("wait_pong")
        state_wait_stopping = SdlState("wait_stopping")

        def __init__(
            self,
            parent_pid: Optional[str],
            peer_pid: Optional[str] = None,
            system: Optional[SdlSystem] = None,
        ) -> None:
            super().__init__(parent_pid, config_data=peer_pid, system=system)
            self.peer_pid = peer_pid
            self.ping_count = 0
            self.pong_count = 0
            self.max_pings = 3

        def _init_state_machine(self) -> None:
            """Initialize state machine."""
            self._event(start, SdlStartSignal, self.start_transition)
            self._event(self.state_wait_ping, self.PingSignal, self.handle_ping)
            self._event(self.state_wait_pong, self.PongSignal, self.handle_pong)
            self._event(self.state_wait_pong, self.StopSignal, self.handle_stop)
            self._event(
                self.state_wait_stopping, SdlStoppingSignal, self.handle_stopping
            )

        async def start_transition(self, _: SdlSignal) -> None:
            """Start: if peer, send ping and wait for pong."""
            if self.peer_pid is not None:
                await self.output(self.PingSignal.create(), self.peer_pid)
                await self.next_state(self.state_wait_pong)
            else:
                await self.next_state(self.state_wait_ping)

        async def handle_ping(self, signal: SdlSignal) -> None:
            """Handle ping signal."""
            self.ping_count += 1
            src = signal.src()
            if src is not None:
                if self.ping_count >= self.max_pings:
                    await self.output(self.StopSignal.create(), src)
                    await self.stop()
                    await self.next_state(self.state_wait_stopping)
                else:
                    await self.output(self.PongSignal.create(), src)

        async def handle_pong(self, signal: SdlSignal) -> None:
            """Handle pong signal."""
            self.pong_count += 1
            src = signal.src()
            if src is not None:
                await self.output(self.PingSignal.create(), src)

        async def handle_stop(self, _: SdlSignal) -> None:
            """Handle stop signal."""
            await self.stop()
            await self.next_state(self.state_wait_stopping)

        async def handle_stopping(self, _: SdlSignal) -> None:
            """Handle stopping signal."""
            self.stop_process()

    @pytest.mark.asyncio
    async def test_ping_pong_scenario(self, sdl_system) -> None:
        """Test full ping-pong communication scenario."""
        # Create two processes
        # Note: peer_pid is passed as config_data parameter to create()
        p1 = await self.SimplePingPongProcess.create(
            None, config_data=None, system=sdl_system
        )
        p2 = await self.SimplePingPongProcess.create(
            None, config_data=p1.pid(), system=sdl_system
        )

        # Process signals manually (simplified event loop)
        for _ in range(20):  # Process up to 20 signals
            if sdl_system._get_queue().empty():
                break

            try:
                signal = await sdl_system.get_next_signal()
                process = sdl_system.lookup_proc_map(signal.dst())  # type: ignore
                if process is not None:
                    handler = process.lookup_transition(signal)
                    if handler is not None:
                        await handler(signal)
            except Exception:
                break

        # Verify ping-pong occurred
        assert p1.ping_count >= 1
        assert p2.pong_count >= 1

    @pytest.mark.asyncio
    async def test_process_creation_and_destruction(self, sdl_system) -> None:
        """Test process lifecycle from creation to destruction."""

        class TestProcess(SdlProcess):
            def _init_state_machine(self) -> None:
                self._event(start, SdlStartSignal, self.handle_start)
                self._event(
                    self.state_stopping, SdlStoppingSignal, self.handle_stopping
                )

            state_stopping = SdlState("stopping")

            async def handle_start(self, _: SdlSignal) -> None:
                await self.stop()
                await self.next_state(self.state_stopping)

            async def handle_stopping(self, _: SdlSignal) -> None:
                self.stop_process()

        # Create process
        process = await TestProcess.create(None, system=sdl_system)
        pid = process.pid()

        assert pid in sdl_system.proc_map
        assert process.current_state() == start

        # Process start signal
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        assert handler is not None
        await handler(signal)

        # Process stopping signal
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        assert handler is not None
        await handler(signal)

        # Process should be removed
        assert pid not in sdl_system.proc_map

    @pytest.mark.asyncio
    async def test_timer_based_state_transition(self, sdl_system) -> None:
        """Test state machine with timer-based transitions."""

        class TimerProcess(SdlProcess):
            class TimeoutTimer(SdlTimer):
                pass

            state_waiting = SdlState("waiting")
            state_timeout = SdlState("timeout")

            def __init__(
                self,
                parent_pid: Optional[str],
                config_data: Optional[Any] = None,
                system: Optional[SdlSystem] = None,
            ) -> None:
                super().__init__(parent_pid, config_data, system=system)
                self.timed_out = False

            def _init_state_machine(self) -> None:
                self._event(start, SdlStartSignal, self.handle_start)
                self._event(self.state_waiting, self.TimeoutTimer, self.handle_timeout)

            async def handle_start(self, _: SdlSignal) -> None:
                self.start_timer(self.TimeoutTimer.create(), 100)  # 100ms
                await self.next_state(self.state_waiting)

            async def handle_timeout(self, _: SdlSignal) -> None:
                self.timed_out = True
                await self.next_state(self.state_timeout)

        process = await TimerProcess.create(None, system=sdl_system)

        # Process start signal
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        await handler(signal)

        assert process.current_state() == process.state_waiting
        assert process.pid() in sdl_system.timer_map

        # Simulate timer expiry
        from time import time

        current_time = int(round(time() * 1000))
        await sdl_system.expire(current_time + 200)

        # Timer should have expired and sent signal
        assert not sdl_system._get_queue().empty()

        # Process timeout signal
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        await handler(signal)

        assert process.timed_out is True
        assert process.current_state() == process.state_timeout

    @pytest.mark.asyncio
    async def test_parent_child_process_hierarchy(self, sdl_system) -> None:
        """Test parent-child process relationships."""

        class ChildProcess(SdlProcess):
            def _init_state_machine(self) -> None:
                self._event(start, SdlStartSignal, self.handle_start)

            async def handle_start(self, _: SdlSignal) -> None:
                pass

        class ParentProcess(SdlProcess):
            def __init__(
                self,
                parent_pid: Optional[str],
                config_data: Optional[Any] = None,
                system: Optional[SdlSystem] = None,
            ) -> None:
                super().__init__(parent_pid, config_data, system=system)
                self.children_created = 0

            def _init_state_machine(self) -> None:
                self._event(start, SdlStartSignal, self.handle_start)

            async def handle_start(self, _: SdlSignal) -> None:
                # Create child processes
                await ChildProcess.create(self.pid(), system=self._system)
                await ChildProcess.create(self.pid(), system=self._system)
                self.children_created = 2

        parent = await ParentProcess.create(None, system=sdl_system)

        # Process start signals
        for _ in range(3):  # Parent + 2 children
            if not sdl_system._get_queue().empty():
                signal = await sdl_system.get_next_signal()
                process = sdl_system.lookup_proc_map(signal.dst())  # type: ignore
                if process is not None:
                    handler = process.lookup_transition(signal)
                    if handler is not None:
                        await handler(signal)

        # Should have 3 processes: 1 parent + 2 children
        assert len(sdl_system.proc_map) == 3
        assert parent.children_created == 2

    @pytest.mark.asyncio
    async def test_multiple_timers_per_process(self, sdl_system) -> None:
        """Test process with multiple concurrent timers."""

        class MultiTimerProcess(SdlProcess):
            class Timer1(SdlTimer):
                pass

            class Timer2(SdlTimer):
                pass

            class Timer3(SdlTimer):
                pass

            def __init__(
                self,
                parent_pid: Optional[str],
                config_data: Optional[Any] = None,
                system: Optional[SdlSystem] = None,
            ) -> None:
                super().__init__(parent_pid, config_data, system=system)
                self.timer1_fired = False
                self.timer2_fired = False
                self.timer3_fired = False

            def _init_state_machine(self) -> None:
                state_running = SdlState("running")
                self._event(start, SdlStartSignal, self.handle_start)
                self._event(state_running, self.Timer1, self.handle_timer1)
                self._event(state_running, self.Timer2, self.handle_timer2)
                self._event(state_running, self.Timer3, self.handle_timer3)
                self.state_running = state_running

            async def handle_start(self, _: SdlSignal) -> None:
                self.start_timer(self.Timer1.create(), 100)
                self.start_timer(self.Timer2.create(), 200)
                self.start_timer(self.Timer3.create(), 300)
                await self.next_state(self.state_running)

            async def handle_timer1(self, _: SdlSignal) -> None:
                self.timer1_fired = True

            async def handle_timer2(self, _: SdlSignal) -> None:
                self.timer2_fired = True

            async def handle_timer3(self, _: SdlSignal) -> None:
                self.timer3_fired = True

        process = await MultiTimerProcess.create(None, system=sdl_system)

        # Process start signal
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        await handler(signal)

        # Should have 3 timers
        assert len(sdl_system.timer_map[process.pid()]) == 3

        # Expire all timers
        from time import time

        current_time = int(round(time() * 1000))
        await sdl_system.expire(current_time + 400)

        # Process all timer signals
        while not sdl_system._get_queue().empty():
            signal = await sdl_system.get_next_signal()
            handler = process.lookup_transition(signal)
            if handler is not None:
                await handler(signal)

        assert process.timer1_fired is True
        assert process.timer2_fired is True
        assert process.timer3_fired is True

    @pytest.mark.asyncio
    async def test_error_condition_nonexistent_destination(self, sdl_system) -> None:
        """Test sending signal to non-existent destination."""

        class SenderProcess(SdlProcess):
            def _init_state_machine(self) -> None:
                self._event(start, SdlStartSignal, self.handle_start)

            async def handle_start(self, _: SdlSignal) -> None:
                # Try to send to non-existent process
                result = await self.output(SdlSignal.create(), "NonExistent(0.0)")
                assert result is False  # Should fail

        process = await SenderProcess.create(None, system=sdl_system)

        # Process start signal
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        await handler(signal)

    @pytest.mark.asyncio
    async def test_complex_state_machine(self, sdl_system) -> None:
        """Test complex state machine with multiple states and transitions."""

        class ComplexProcess(SdlProcess):
            class EventA(SdlSignal):
                pass

            class EventB(SdlSignal):
                pass

            class EventC(SdlSignal):
                pass

            state_A = SdlState("state_A")
            state_B = SdlState("state_B")
            state_C = SdlState("state_C")
            state_final = SdlState("final")

            def __init__(
                self,
                parent_pid: Optional[str],
                config_data: Optional[Any] = None,
                system: Optional[SdlSystem] = None,
            ) -> None:
                super().__init__(parent_pid, config_data, system=system)
                self.path = []

            def _init_state_machine(self) -> None:
                self._event(start, SdlStartSignal, self.handle_start)
                self._event(self.state_A, self.EventA, self.handle_a)
                self._event(self.state_B, self.EventB, self.handle_b)
                self._event(self.state_C, self.EventC, self.handle_c)

            async def handle_start(self, _: SdlSignal) -> None:
                self.path.append("start")
                await self.next_state(self.state_A)

            async def handle_a(self, _: SdlSignal) -> None:
                self.path.append("A")
                await self.next_state(self.state_B)

            async def handle_b(self, _: SdlSignal) -> None:
                self.path.append("B")
                await self.next_state(self.state_C)

            async def handle_c(self, _: SdlSignal) -> None:
                self.path.append("C")
                await self.next_state(self.state_final)

        process = await ComplexProcess.create(None, system=sdl_system)

        # Process start
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        await handler(signal)
        assert process.current_state() == process.state_A

        # Send EventA
        await process.output(process.EventA.create(), process.pid())
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        await handler(signal)
        assert process.current_state() == process.state_B

        # Send EventB
        await process.output(process.EventB.create(), process.pid())
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        await handler(signal)
        assert process.current_state() == process.state_C

        # Send EventC
        await process.output(process.EventC.create(), process.pid())
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        await handler(signal)
        assert process.current_state() == process.state_final

        assert process.path == ["start", "A", "B", "C"]

    @pytest.mark.asyncio
    async def test_signal_between_multiple_processes(self, sdl_system) -> None:
        """Test signal routing between multiple processes."""

        class EchoProcess(SdlProcess):
            class EchoRequest(SdlSignal):
                pass

            class EchoReply(SdlSignal):
                pass

            state_ready = SdlState("ready")

            def __init__(
                self,
                parent_pid: Optional[str],
                config_data: Optional[Any] = None,
                system: Optional[SdlSystem] = None,
            ) -> None:
                super().__init__(parent_pid, config_data, system=system)
                self.echo_count = 0

            def _init_state_machine(self) -> None:
                self._event(start, SdlStartSignal, self.handle_start)
                self._event(
                    self.state_ready, self.EchoRequest, self.handle_echo_request
                )

            async def handle_start(self, _: SdlSignal) -> None:
                await self.next_state(self.state_ready)

            async def handle_echo_request(self, signal: SdlSignal) -> None:
                self.echo_count += 1
                src = signal.src()
                if src is not None:
                    await self.output(self.EchoReply.create(self.echo_count), src)

        # Create echo server and multiple clients
        server = await EchoProcess.create(None, system=sdl_system)

        # Process server start
        signal = await sdl_system.get_next_signal()
        handler = server.lookup_transition(signal)
        await handler(signal)

        # Send echo requests
        client_pid = "Client(0.0)"
        for i in range(5):
            req = EchoProcess.EchoRequest.create()
            req.set_src(client_pid)
            req.set_dst(server.pid())
            await sdl_system.output(req)

        # Process all echo requests
        while not sdl_system._get_queue().empty():
            signal = await sdl_system.get_next_signal()
            process = sdl_system.lookup_proc_map(signal.dst())  # type: ignore
            if process is not None:
                handler = process.lookup_transition(signal)
                if handler is not None:
                    await handler(signal)

        assert server.echo_count == 5
