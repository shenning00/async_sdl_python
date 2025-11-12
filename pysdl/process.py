"""
process.py
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from time import time
from typing import Any, TypeVar

from pysdl.exceptions import (
    TimerError,
    ValidationError,
)
from pysdl.id_generator import SdlIdGenerator
from pysdl.logger import SdlLogger
from pysdl.signal import SdlSignal
from pysdl.state import SdlState, start
from pysdl.state_machine import SdlStateMachine
from pysdl.system import SdlSystem
from pysdl.system_signals import (
    SdlStartSignal,
    SdlStoppingSignal,
)
from pysdl.timer import SdlTimer

T = TypeVar("T", bound="SdlProcess")


class SdlProcess:
    """Base SDL process class.

    Provides the foundation for all SDL processes including state machine
    management, signal handling, timer support, and lifecycle management.

    Processes must implement _init_state_machine() to define their behavior.
    Use the create() class method to properly instantiate and register processes.

    Class Attributes:
        _id: Unique ID for this process class (shared across instances).
        _instance_count: Counter for instances of this process class.
    """

    # Class variables (shared across all instances of this process type)
    _id: int | None = None
    _instance_count: int = 0

    @classmethod
    async def create(
        cls: type[T],
        parent_pid: str | None,
        config_data: Any | None = None,
        system: SdlSystem | None = None,
    ) -> T:
        """Create and register a process with a system.

        Args:
            parent_pid: Parent process ID (or None for root)
            config_data: Optional configuration data
            system: SdlSystem instance to register with (required)

        Returns:
            The created and registered process instance

        Raises:
            ValidationError: If system is None
        """
        if system is None:
            raise ValidationError(
                "system", "Process creation requires a system instance"
            )

        process = cls(parent_pid, config_data, system=system)
        await process._register()
        return process

    def __init__(
        self,
        parent_pid: str | None,
        config_data: Any | None = None,
        system: SdlSystem | None = None,
    ) -> None:
        """Initialize a process.

        Args:
            parent_pid: Parent process ID (or None for root)
            config_data: Optional configuration data
            system: SdlSystem instance to register with (required)

        Raises:
            ValidationError: If system is None

        Note:
            Instance variables initialized here:
            - _system: System instance this process belongs to
            - _parent: Parent process ID
            - _instance: Instance number for this process class
            - _pid: Process ID string
            - _FSM: State machine for this process
            - _state: Current state
            - _save_signals: Saved signals for state transitions
            - _config_data: Configuration data
        """
        if system is None:
            raise ValidationError("system", "SdlProcess requires a system instance")

        # Initialize instance variables
        self._system: SdlSystem = system
        self._parent: str | None = parent_pid
        self.__class__._id = self.__class__.id()

        if isinstance(self, SdlSingletonProcess):
            pass
        else:
            self.__class__.incr_instance()

        self._instance: int = self._instance_count
        self._pid: str = f"{self.name()}({self.id()}.{self.instance()})"
        self._FSM: SdlStateMachine = SdlStateMachine()
        self._state: SdlState = start
        self._save_signals: list[SdlSignal] = []
        self._config_data: Any | None = config_data

    def __str__(self) -> str:
        return self._pid

    def __repr__(self) -> str:
        return self._pid

    @classmethod
    def name(cls) -> str:
        """get class name"""
        return cls.__name__

    @classmethod
    def build_pid(cls, instance: int) -> str:
        return f"{cls.__name__}({cls.id()}.{instance})"

    def set_parent(self, parent: str) -> None:
        self._parent = parent

    def get_parent(self) -> str | None:
        return self._parent

    @classmethod
    def id(cls) -> int:
        if cls._id is None:
            cls._id = SdlIdGenerator.next()
        return cls._id

    @classmethod
    def incr_instance(cls) -> int | None:
        cls._instance_count += 1
        return cls._id

    def instance(self) -> int:
        return self._instance

    def pid(self) -> str:
        """get pid"""
        return self._pid

    def current_state(self) -> SdlState:
        """get state"""
        return self._state

    async def next_state(self, state: SdlState) -> None:
        """Transition to a new state.

        Args:
            state: The new state to transition to

        Raises:
            ValidationError: If state is None or invalid
        """
        if state is None:
            raise ValidationError("state", "Cannot transition to None state")

        if not isinstance(state, SdlState):
            raise ValidationError("state", f"Invalid state type: {type(state)}")

        if state != self._state:
            SdlLogger.state(self, self._state, state)
            self._state = state
            for signal in self._save_signals:
                try:
                    await self.output(signal, signal.dst())  # type: ignore
                except Exception as e:
                    SdlLogger.warning(
                        f"Failed to send saved signal {signal} in {self.pid()}: {e}"
                    )

    async def output(self, signal: SdlSignal, dst: str) -> bool:
        """Send a signal to a destination process.

        Args:
            signal: The signal to send
            dst: Destination process ID

        Returns:
            True if signal was delivered successfully

        Raises:
            ValidationError: If signal or dst is invalid
        """
        if not isinstance(signal, SdlSignal):
            raise ValidationError("signal", "signal must be an instance of SdlSignal")

        if not dst or not isinstance(dst, str):
            raise ValidationError("dst", f"Invalid destination PID: {dst}")

        signal.set_dst(dst)
        signal.set_src(self.pid())
        return await self._system.output(signal)

    def start_timer(self, timer: SdlTimer, msec: int) -> None:
        """Start a timer with relative time.

        Args:
            timer: The timer to start
            msec: Milliseconds from now when timer should expire

        Raises:
            ValidationError: If timer is invalid
            TimerError: If msec is negative
        """
        if not isinstance(timer, SdlTimer):
            raise ValidationError("timer", "timer must be an instance of SdlTimer")

        if msec < 0:
            raise TimerError(str(timer), f"Timer duration cannot be negative: {msec}ms")

        timer.set_dst(self.pid())
        timer.set_src(self.pid())
        abs_msec = int(round(time() * 1000)) + msec
        timer.start(abs_msec)
        self._system.startTimer(timer)

    def start_timer_abs(self, timer: SdlTimer, sec: int) -> None:
        """Start a timer with absolute time.

        Args:
            timer: The timer to start
            sec: Absolute time in seconds when timer should expire

        Raises:
            ValidationError: If timer is invalid
            TimerError: If sec is invalid
        """
        if not isinstance(timer, SdlTimer):
            raise ValidationError("timer", "timer must be an instance of SdlTimer")

        if sec <= 0:
            raise TimerError(str(timer), f"Timer absolute time must be positive: {sec}")

        timer.set_dst(self.pid())
        timer.set_src(self.pid())
        timer.start(sec)
        self._system.startTimer(timer)

    def stop_timer(self, timer: SdlTimer) -> None:
        """Stop a timer.

        Args:
            timer: The timer to stop

        Raises:
            ValidationError: If timer is invalid
        """
        if not isinstance(timer, SdlTimer):
            raise ValidationError("timer", "timer must be an instance of SdlTimer")

        timer.set_dst(self.pid())
        timer.set_src(self.pid())

        try:
            if not self._system.stopTimer(timer):
                SdlLogger.warning(f"Timer {timer} was not active")
        except Exception as e:
            SdlLogger.warning(f"Error stopping timer {timer}: {e}")

    async def stop(self) -> None:
        await self.output(SdlStoppingSignal.create(), self.pid())

    def stop_process(self) -> None:
        SdlLogger.event("Stopped", self, self.pid(), self.pid())
        self._system.unregister(self)

    # methods for derived classes to invoke
    async def _register(self) -> None:
        self._init_state_machine()
        self._system.register(self)
        SdlLogger.create(self, self._parent)
        SdlLogger.state(self, "none", self._state)  # type: ignore
        await self.output(SdlStartSignal.create(), self.pid())

    def _event(
        self,
        _state: SdlState,
        _signal: type[SdlSignal],
        _handler: Callable[..., Coroutine[Any, Any, None]],
    ) -> SdlProcess:
        """add (state, id, handler) tuple to the state machine"""
        self._FSM.state(_state).event(_signal).handler(_handler)
        return self

    def _done(self) -> None:
        """state machine definition is done"""
        self._FSM.done()

    def _init_state_machine(self) -> None:
        raise NotImplementedError(
            "_init_state_machine() must be defined in your SdlProcess"
        )

    def lookup_transition(
        self, signal: SdlSignal | None
    ) -> Callable[..., Coroutine[Any, Any, None]] | None:
        """Lookup state transition handler for a signal.

        Uses 4-level priority matching:
        1. Exact match (state, signal)
        2. Star state (any state, specific signal)
        3. Star signal (specific state, any signal)
        4. Double star (any state, any signal)

        Args:
            signal: The signal to find a handler for

        Returns:
            Handler function or None if not found

        Raises:
            ValidationError: If signal is None
        """
        if signal is None:
            raise ValidationError("signal", "Cannot lookup transition for None signal")

        found = self._FSM.find(self.current_state(), signal.id())
        if found is None:
            SdlLogger.warning(
                f"No handler for signal {signal.id()} ({signal.name()}) "
                f"in state {self.current_state()} for process {self.pid()}"
            )

        return found

    # methods for sdl system to invoke
    async def input(self, signal: SdlSignal) -> None:
        """Post a signal to the system queue.

        Args:
            signal: The signal to enqueue

        Raises:
            ValidationError: If signal is invalid
        """
        if not isinstance(signal, SdlSignal):
            raise ValidationError("signal", "signal must be an instance of SdlSignal")

        await self._system.enqueue(signal)

    async def save_signal(self, signal: SdlSignal) -> None:
        self._save_signals.append(signal)


S = TypeVar("S", bound="SdlSingletonProcess")


class SdlSingletonProcess(SdlProcess):
    """Singleton process base class.

    Ensures only one instance of this process type exists in the system.
    Subsequent calls to create() return the same instance.

    Class Attributes:
        _singleton_instance: The singleton instance of this process class.
    """

    # Class variable for singleton instance (use single underscore for consistency)
    _singleton_instance: SdlSingletonProcess | None = None

    @classmethod
    async def create(
        cls: type[S],
        parent_pid: str | None,
        config_data: Any | None = None,
        system: SdlSystem | None = None,
    ) -> S:
        """Create and register a singleton process with a system.

        Args:
            parent_pid: Parent process ID (or None for root)
            config_data: Optional configuration data
            system: SdlSystem instance to register with (required)

        Returns:
            The singleton process instance (created on first call, returned on subsequent calls)

        Raises:
            ValidationError: If system is None
        """
        if cls._singleton_instance is None:
            if system is None:
                raise ValidationError(
                    "system", "Singleton process creation requires a system instance"
                )
            cls._singleton_instance = cls(parent_pid, config_data, system=system)
            await cls._singleton_instance._register()
        return cls._singleton_instance  # type: ignore

    def _init_state_machine(self) -> None:
        raise NotImplementedError(
            "_init_state_machine() must be defined in your SdlProcess"
        )

    @classmethod
    def single_pid(cls) -> str:
        return f"{cls.__name__}({cls.id()}.0)"
