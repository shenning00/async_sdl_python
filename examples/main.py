import asyncio
from typing import Any, Optional

from pysdl.logger import SdlLogger
from pysdl.process import SdlProcess
from pysdl.signal import SdlSignal
from pysdl.state import SdlState, start
from pysdl.system import SdlSystem
from pysdl.system_signals import SdlStartSignal, SdlStoppingSignal
from pysdl.timer import SdlTimer


class PingPongProcess(SdlProcess):
    """ping pong process: sends a ping pong signals
    between self and peer process."""

    class PingSignal(SdlSignal):
        def dumpdata(self) -> Optional[str]:
            return "Ping"

    class PongSignal(SdlSignal):
        def dumpdata(self) -> Optional[str]:
            return "Pong"

    class StopSignal(SdlSignal): ...

    state_wait_ping = SdlState("wait_ping")
    state_wait_pong = SdlState("wait_pong")
    state_wait_stopping = SdlState("wait_stopping")

    _count: int = 0

    def __init__(
        self, parent_pid: Optional[str], config_data: Optional[Any] = None, system=None
    ) -> None:
        super().__init__(parent_pid, config_data, system=system)
        # Extract peer_pid from config_data if provided
        self.peer_pid = config_data.get("peer_pid") if config_data else None

    async def start_StartTransition(self, _: SdlSignal) -> None:
        """start: if peer - send ping and wait for pong
        otherwise wait for ping"""
        if self.peer_pid is not None:
            await self.output(self.PingSignal.create(), self.peer_pid)
            await self.next_state(self.state_wait_pong)
        else:
            await self.next_state(self.state_wait_ping)

    async def wait_pong_PongSignal(self, signal: SdlSignal) -> None:
        """handle pong signal"""
        src = signal.src()
        if src is not None:
            await self.output(self.PingSignal.create(), src)

    async def wait_ping_PingSignal(self, signal: SdlSignal) -> None:
        """handle ping signal"""
        self._count += 1
        src = signal.src()
        if src is not None:
            if self._count == 20:
                await self.output(self.StopSignal.create(), src)
                await self.stop()  # post a stop
                await self.next_state(self.state_wait_stopping)
            else:
                await self.output(self.PongSignal.create(), src)

    async def wait_pong_StopSignal(self, _: SdlSignal) -> None:
        """handle pingpong stop signal"""
        await self.stop()
        await self.next_state(self.state_wait_stopping)

    async def wait_stopping(self, _: SdlSignal) -> None:
        """handle stopping signal"""
        self.stop_process()

    def _init_state_machine(self) -> None:
        """initialize state machine"""
        self._event(start, SdlStartSignal, self.start_StartTransition)
        self._event(self.state_wait_ping, self.PingSignal, self.wait_ping_PingSignal)
        self._event(self.state_wait_pong, self.PongSignal, self.wait_pong_PongSignal)
        self._event(self.state_wait_pong, self.StopSignal, self.wait_pong_StopSignal)
        self._event(self.state_wait_stopping, SdlStoppingSignal, self.wait_stopping)


class ProcessInit(SdlProcess):
    class ShutdownTimer(SdlTimer): ...

    p1: PingPongProcess
    p2: PingPongProcess

    def __init__(
        self, parent_pid: Optional[str], config_data: Optional[Any] = None, system=None
    ) -> None:
        super().__init__(parent_pid, config_data, system=system)
        self.wait = SdlState("wait")
        self.state_shutdown_timer = SdlState("shutdown_timer")

    async def start_StartTransition(self, _: SdlSignal) -> None:
        """start pingpong processes, set timer, got to shutdown state"""
        self.p1 = await PingPongProcess.create(self.pid(), None, system=self._system)
        self.p2 = await PingPongProcess.create(
            self.pid(), {"peer_pid": self.p1.pid()}, system=self._system
        )

        # start 5 second timer
        self.start_timer(self.ShutdownTimer.create(), 5000)
        # got to state to wait for timer to expire
        await self.next_state(self.state_shutdown_timer)

    async def shutdown_timer_ShutdownTimer(self, _: SdlSignal) -> None:
        """handle shtudown timer"""
        SdlLogger.info("Received shutdown timer...stopping SdlSystem.")
        self._system.stop()

    def _init_state_machine(self) -> None:
        """initialize state machine"""
        self._event(start, SdlStartSignal, self.start_StartTransition)
        self._event(
            self.state_shutdown_timer,
            self.ShutdownTimer,
            self.shutdown_timer_ShutdownTimer,
        )


async def main() -> None:
    """create initial process and run system"""
    system = SdlSystem()
    await ProcessInit.create(None, None, system=system)
    await system.run()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()
    loop.close()
