"""SDL system core implementation.

This module provides the core event loop and system management functionality
for the PySDL framework. Manages process registration, signal routing, timer
scheduling, and the main event loop.
"""

from __future__ import annotations

import asyncio
from time import time
from typing import TYPE_CHECKING

from .exceptions import (
    QueueError,
    SignalDeliveryError,
    TimerError,
    ValidationError,
)
from .logger import SdlLogger
from .system_signals import SdlProcessNotExistSignal

if TYPE_CHECKING:
    from pysdl.process import SdlProcess
    from pysdl.signal import SdlSignal
    from pysdl.timer import SdlTimer


class SdlSystem:
    """Instance-based SDL system.

    Manages processes, timers, and signal routing for an independent SDL system instance.

    Attributes:
        proc_map: Registry mapping process IDs to SdlProcess instances.
        timer_map: Registry mapping process IDs to lists of active timers.
        ready_list: Queue of processes ready for signal processing.
        _queue: Asyncio queue for signal delivery (created lazily).
        _stop: Flag to stop the event loop.
    """

    def __init__(self) -> None:
        """Initialize a new independent SDL system instance."""
        self.proc_map: dict[str, SdlProcess] = {}
        self.timer_map: dict[str, list[SdlTimer]] = {}
        self.ready_list: list[SdlProcess] = []
        self._queue: asyncio.Queue[SdlSignal] | None = None
        self._stop: bool = False

    def _get_queue(self) -> asyncio.Queue[SdlSignal]:
        """Get or create the asyncio.Queue lazily for this system instance.

        This is needed because asyncio.Queue must be created within
        a running event loop context.

        Returns:
            The queue for this system instance.
        """
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    def register(self, process: SdlProcess | None) -> bool:
        """Register a process with this system instance.

        Args:
            process: The process to register

        Returns:
            True if registered successfully, False if already registered

        Raises:
            ValidationError: If process is None or invalid
        """
        if process is None:
            raise ValidationError("process", "Cannot register None as a process")

        pid = process.pid()
        if not pid or not isinstance(pid, str):
            raise ValidationError("pid", f"Process has invalid PID: {pid}")

        if pid not in self.proc_map:
            self.proc_map[pid] = process
            SdlLogger.event("Registered", process, pid, pid)
            return True

        SdlLogger.warning(f"Process {pid} already registered")
        return False

    def unregister(self, process: SdlProcess | None) -> bool:
        """Unregister a process from this system instance.

        Removes the process from all system data structures (proc_map, timer_map,
        ready_list). Note: This does not send error signals for pending signals
        in the process's inbox, as those signals are in the system queue, not
        process-specific queues.

        Args:
            process: The process to unregister

        Returns:
            True if unregistered successfully, False if process is None

        Raises:
            ValidationError: If process is invalid
        """
        if process is None:
            raise ValidationError("process", "Cannot unregister None as a process")

        pid = process.pid()
        if not pid:
            raise ValidationError("pid", "Process has invalid PID")

        # remove from proc_map
        if pid in self.proc_map:
            del self.proc_map[pid]
            SdlLogger.event("Unregistered", process, pid, pid)
        else:
            SdlLogger.warning(f"Process {pid} was not in proc_map during unregister")

        # remove from timer_map
        if pid in self.timer_map:
            timer_count = len(self.timer_map[pid])
            del self.timer_map[pid]
            SdlLogger.event("TimersCleared", process, pid, f"{timer_count} timers")

        # remove from ready_list
        removed_count = 0
        while process in self.ready_list:
            self.ready_list.remove(process)
            removed_count += 1
        if removed_count > 0:
            SdlLogger.event(
                "ReadyListCleared", process, pid, f"{removed_count} entries"
            )

        return True

    async def enqueue(self, signal: SdlSignal) -> None:
        """Enqueue a signal for processing in this system instance.

        Args:
            signal: The signal to enqueue

        Raises:
            ValidationError: If signal is None or invalid
            QueueError: If queue operation fails
        """
        if signal is None:
            raise ValidationError("signal", "Cannot enqueue None as a signal")

        try:
            await self._get_queue().put(signal)
        except Exception as e:
            SdlLogger.warning(f"Failed to enqueue signal {signal}: {e}")
            raise QueueError(f"Failed to enqueue signal: {e}") from e

    def lookup_proc_map(self, dst: str) -> SdlProcess | None:
        """Lookup a process by PID in this system instance.

        Args:
            dst: The process ID to lookup

        Returns:
            The process if found, None otherwise

        Raises:
            ValidationError: If dst is None or invalid
        """
        if not dst or not isinstance(dst, str):
            raise ValidationError("dst", f"Invalid destination PID: {dst}")

        return self.proc_map.get(dst)

    async def output(self, signal: SdlSignal) -> bool:
        """Send a signal to its destination process in this system instance.

        If the destination process does not exist, a SdlProcessNotExistSignal
        is sent back to the source process (if it exists) to notify it of the
        delivery failure.

        Args:
            signal: The signal to send

        Returns:
            True if signal was delivered, False if destination not found

        Raises:
            ValidationError: If signal is None or invalid
            SignalDeliveryError: If signal delivery to destination fails
        """
        if signal is None:
            raise ValidationError("signal", "Cannot output None as a signal")

        dst = signal.dst()
        if not dst:
            raise ValidationError("signal.dst", "Signal has no destination")

        if dst in self.proc_map:
            process = self.proc_map[dst]
            self.ready_list.append(process)
            try:
                await process.input(signal)
                return True
            except Exception as e:
                SdlLogger.warning(f"Failed to deliver signal {signal} to {dst}: {e}")
                raise SignalDeliveryError(
                    destination=dst,
                    message=f"Failed to deliver signal to process {dst}: {e}",
                    signal=str(type(signal).__name__),
                ) from e
        else:
            # Send error signal back to source if it exists
            src = signal.src()
            SdlLogger.warning(f"Signal {signal.name()} to nonexistent process {dst}")

            if src and src in self.proc_map:
                error_signal = SdlProcessNotExistSignal(
                    original_signal=type(signal).__name__, destination=dst, source=src
                )
                error_signal.set_dst(src)
                error_signal.set_src("SdlSystem")

                try:
                    source_process = self.proc_map[src]
                    self.ready_list.append(source_process)
                    await source_process.input(error_signal)
                    SdlLogger.signal("SdlProcessNotExist", error_signal, source_process)
                except Exception as e:
                    SdlLogger.warning(
                        f"Failed to send error signal to source {src}: {e}"
                    )

            return False

    def startTimer(self, timer: SdlTimer | None) -> None:
        """Start a timer in this system instance.

        Starts a timer for a process. If the timer is already running, it is
        stopped first. Multiple timers can be active for the same process.

        Args:
            timer: The timer to start

        Raises:
            ValidationError: If timer is None
            TimerError: If timer has no source PID
        """
        if timer is None:
            raise ValidationError("timer", "Cannot start None as a timer")

        pid = timer.src()
        if not pid:
            raise TimerError(str(timer), "Timer has no source PID")

        # Stop timer if already running to prevent duplicates
        # Use try-except since stopTimer now raises on None
        try:
            self.stopTimer(timer)
        except ValidationError:
            # Timer not running, that's fine
            pass

        if pid not in self.timer_map:
            self.timer_map[pid] = []
        self.timer_map[pid].append(timer)

    def stopTimer(self, timer: SdlTimer | None) -> bool:
        """Stop a timer in this system instance.

        Removes only the specific timer from the timer map. If this was the last
        timer for the process, the PID entry is removed from the timer map entirely.

        Args:
            timer: The timer to stop

        Returns:
            True if timer was found and stopped, False otherwise

        Raises:
            ValidationError: If timer is None
        """
        if timer is None:
            raise ValidationError("timer", "Cannot stop None as a timer")

        pid = timer.src()
        if not pid:
            SdlLogger.warning(f"Timer {timer} has no source PID")
            return False

        if pid not in self.timer_map:
            return False

        timer_list = self.timer_map[pid]
        if timer not in timer_list:
            return False

        timer_list.remove(timer)

        # Clean up empty timer list to prevent memory leaks
        if not timer_list:
            del self.timer_map[pid]

        return True

    async def get_next_signal(self) -> SdlSignal:
        """Get the next signal from the queue for this system instance.

        Returns:
            The next signal in the queue

        Raises:
            QueueError: If queue operation fails
        """
        try:
            return await self._get_queue().get()
        except Exception as e:
            SdlLogger.warning(f"Failed to get next signal from queue: {e}")
            raise QueueError(f"Failed to get signal from queue: {e}") from e

    async def _process_signal(self, signal: SdlSignal) -> None:
        """Process a single signal by finding and executing its handler.

        Args:
            signal: The signal to process

        Raises:
            ValidationError: If signal validation fails
        """
        process = self.lookup_proc_map(signal.dst())  # type: ignore
        if process is None:
            SdlLogger.warning(f"Signal destination process not found: {signal.dst()}")
            return

        signal_handler = process.lookup_transition(signal)
        if signal_handler is None:
            SdlLogger.signal("SdlSig-NA", signal, process)
            return

        SdlLogger.signal("SdlSig", signal, process)
        try:
            await signal_handler(signal)
        except Exception as e:
            SdlLogger.warning(f"Error in signal handler for {signal} in {process}: {e}")
            # Continue processing - don't crash the system

    async def run(self) -> bool:
        """Main event loop for this SDL system instance.

        Processes signals from the queue and handles timer expiration.
        Continues running until stop() is called.

        Returns:
            True when stopped normally

        Raises:
            Various exceptions may be raised during signal processing
        """
        while True:
            try:
                # Get next signal with timeout to allow periodic timer checks
                signal = None
                try:
                    signal = await asyncio.wait_for(
                        self.get_next_signal(), timeout=0.01
                    )  # 10ms timeout
                except asyncio.TimeoutError:
                    # No signal available, continue to timer check
                    pass

                if signal is not None:
                    try:
                        await self._process_signal(signal)
                    except ValidationError as e:
                        SdlLogger.warning(f"Validation error processing signal: {e}")
                    finally:
                        del signal

                # Check for timer expiries
                try:
                    await self.expire(int(round(time() * 1000)))  # current time in ms
                except Exception as e:
                    SdlLogger.warning(f"Error processing timer expiration: {e}")

                # Check for stop of the system
                if self._stop is True:
                    loop = asyncio.get_event_loop()
                    loop.stop()
                    return True

                # Allow other async runners to run
                await asyncio.sleep(0)

            except QueueError as e:
                SdlLogger.warning(f"Queue error in main loop: {e}")
                # Continue running - the queue error may be transient
                await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                SdlLogger.warning("Keyboard interrupt received, stopping system")
                self.stop()
                return True
            except Exception as e:
                SdlLogger.warning(f"Unexpected error in main loop: {e}")
                # Continue running to avoid complete system failure
                await asyncio.sleep(0.1)

    def stop(self) -> None:
        """Stop this SDL system instance."""
        self._stop = True

    async def expire(self, msec: int) -> None:
        """Process timer expirations for this system instance.

        Checks all active timers and delivers expired timer signals.
        Removes expired timers from the timer map.

        Args:
            msec: Current time in milliseconds

        Raises:
            TimerError: If timer processing fails critically
        """
        expired: list[SdlTimer] = []

        # send all expired timers
        for _pid, timerList in list(self.timer_map.items()):
            for timer in timerList:
                try:
                    timer.expire(msec)
                    if timer.expired():
                        try:
                            await self.output(timer)
                            expired.append(timer)
                        except Exception as e:
                            SdlLogger.warning(
                                f"Failed to deliver expired timer {timer}: {e}"
                            )
                            # Still mark as expired to remove it
                            expired.append(timer)
                except Exception as e:
                    SdlLogger.warning(
                        f"Error checking timer expiration for {timer}: {e}"
                    )

        # stop all expired timers
        for timer in expired:
            try:
                if not self.stopTimer(timer):
                    SdlLogger.warning(f"Timer {timer} was already stopped")
            except Exception as e:
                SdlLogger.warning(f"Error removing expired timer {timer}: {e}")
