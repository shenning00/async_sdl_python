"""Test suite for SdlSystem error handling and edge cases.

This module tests error paths, exception handling, and edge cases in SdlSystem
to achieve comprehensive coverage of the system.py module.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pysdl.exceptions import (
    QueueError,
    SignalDeliveryError,
    TimerError,
    ValidationError,
)
from pysdl.id_generator import SdlIdGenerator
from pysdl.process import SdlProcess
from pysdl.signal import SdlSignal
from pysdl.state import start
from pysdl.system import SdlSystem
from pysdl.system_signals import SdlStartSignal
from pysdl.timer import SdlTimer


class TestProcess(SdlProcess):
    """Test process for error path tests."""

    def _init_state_machine(self) -> None:
        """Initialize state machine."""
        self._event(start, SdlStartSignal, self.handle_start)

    async def handle_start(self, signal: SdlSignal) -> None:
        """Handle start signal."""


class TestSdlSystemErrorPaths:
    """Test cases for SdlSystem error handling and edge cases."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Reset state before each test."""
        SdlIdGenerator._id = 0
        SdlSignal._id = None
        SdlTimer._id = None

    @pytest.fixture
    def sdl_system(self):
        """Provide a fresh SdlSystem instance for each test."""
        return SdlSystem()

    # =====================================================================
    # register() Error Paths
    # =====================================================================

    def test_register_process_with_invalid_pid_type(self, sdl_system) -> None:
        """Test registering process with non-string PID raises ValidationError.

        Covers line 69: Invalid PID type validation.
        """
        # Create a mock process with invalid PID (not a string)
        mock_process = Mock(spec=SdlProcess)
        mock_process.pid.return_value = 123  # Integer instead of string

        with pytest.raises(ValidationError, match="Process has invalid PID"):
            sdl_system.register(mock_process)

    def test_register_process_with_empty_pid(self, sdl_system) -> None:
        """Test registering process with empty PID raises ValidationError.

        Covers line 69: Invalid PID validation (empty string).
        """
        # Create a mock process with empty PID
        mock_process = Mock(spec=SdlProcess)
        mock_process.pid.return_value = ""

        with pytest.raises(ValidationError, match="Process has invalid PID"):
            sdl_system.register(mock_process)

    # =====================================================================
    # unregister() Error Paths
    # =====================================================================

    def test_unregister_process_with_empty_pid(self, sdl_system) -> None:
        """Test unregistering process with empty PID raises ValidationError.

        Covers line 101: Invalid PID in unregister.
        """
        # Create a mock process with empty PID
        mock_process = Mock(spec=SdlProcess)
        mock_process.pid.return_value = ""

        with pytest.raises(ValidationError, match="Process has invalid PID"):
            sdl_system.unregister(mock_process)

    def test_unregister_process_not_in_proc_map_logs_warning(self, sdl_system) -> None:
        """Test unregistering process not in proc_map logs warning.

        Covers line 108: Warning when process not in proc_map.
        """
        # Create a valid process but don't register it
        mock_process = Mock(spec=SdlProcess)
        mock_process.pid.return_value = "TestProcess(0.0)"

        with patch("pysdl.system.SdlLogger.warning") as mock_warning:
            result = sdl_system.unregister(mock_process)

            assert result is True
            mock_warning.assert_called()
            assert "was not in proc_map" in str(mock_warning.call_args)

    # =====================================================================
    # enqueue() Error Paths
    # =====================================================================

    @pytest.mark.asyncio
    async def test_enqueue_none_signal_raises_validation_error(
        self, sdl_system
    ) -> None:
        """Test enqueueing None signal raises ValidationError.

        Covers line 139: None signal validation.
        """
        with pytest.raises(ValidationError, match="Cannot enqueue None"):
            await sdl_system.enqueue(None)  # type: ignore

    @pytest.mark.asyncio
    async def test_enqueue_queue_put_failure_raises_queue_error(
        self, sdl_system
    ) -> None:
        """Test enqueue raises QueueError when queue.put fails.

        Covers lines 143-145: Queue operation failure handling.
        """
        signal = SdlSignal.create()

        # Mock the queue to raise an exception
        with patch.object(sdl_system, "_get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.put.side_effect = RuntimeError("Queue is full")
            mock_get_queue.return_value = mock_queue

            with pytest.raises(QueueError, match="Failed to enqueue signal"):
                await sdl_system.enqueue(signal)

    # =====================================================================
    # lookup_proc_map() Error Paths
    # =====================================================================

    def test_lookup_proc_map_with_none_dst_raises_validation_error(
        self, sdl_system
    ) -> None:
        """Test lookup_proc_map with None dst raises ValidationError.

        Covers line 160: Invalid destination validation.
        """
        with pytest.raises(ValidationError, match="Invalid destination PID"):
            sdl_system.lookup_proc_map(None)  # type: ignore

    def test_lookup_proc_map_with_empty_dst_raises_validation_error(
        self, sdl_system
    ) -> None:
        """Test lookup_proc_map with empty dst raises ValidationError.

        Covers line 160: Invalid destination validation.
        """
        with pytest.raises(ValidationError, match="Invalid destination PID"):
            sdl_system.lookup_proc_map("")

    def test_lookup_proc_map_with_non_string_dst_raises_validation_error(
        self, sdl_system
    ) -> None:
        """Test lookup_proc_map with non-string dst raises ValidationError.

        Covers line 160: Invalid destination validation (type check).
        """
        with pytest.raises(ValidationError, match="Invalid destination PID"):
            sdl_system.lookup_proc_map(123)  # type: ignore

    # =====================================================================
    # output() Error Paths
    # =====================================================================

    @pytest.mark.asyncio
    async def test_output_signal_with_no_destination_raises_validation_error(
        self, sdl_system
    ) -> None:
        """Test output signal with no destination raises ValidationError.

        Covers line 186: Signal with no destination.
        """
        signal = SdlSignal.create()
        signal.set_dst("")  # Empty destination

        with pytest.raises(ValidationError, match="Signal has no destination"):
            await sdl_system.output(signal)

    @pytest.mark.asyncio
    async def test_output_signal_delivery_failure_raises_signal_delivery_error(
        self, sdl_system
    ) -> None:
        """Test output raises SignalDeliveryError when process.input() fails.

        Covers lines 194-196: Signal delivery failure handling.
        """
        # Create a mock process that will fail on input
        mock_process = Mock(spec=SdlProcess)
        mock_process.pid.return_value = "TestProcess(0.0)"
        mock_process.input = AsyncMock(side_effect=RuntimeError("Process crashed"))

        # Register the mock process
        sdl_system.proc_map["TestProcess(0.0)"] = mock_process

        signal = SdlSignal.create()
        signal.set_dst("TestProcess(0.0)")

        with pytest.raises(
            SignalDeliveryError, match="Failed to deliver signal to process"
        ):
            await sdl_system.output(signal)

    @pytest.mark.asyncio
    async def test_output_to_nonexistent_with_error_signal_delivery_failure(
        self, sdl_system
    ) -> None:
        """Test output to nonexistent process when error signal delivery fails.

        Covers lines 218-219: Exception when sending error signal back to source.
        """
        # Create source process that will fail when receiving error signal
        mock_source = Mock(spec=SdlProcess)
        mock_source.pid.return_value = "Source(0.0)"
        mock_source.input = AsyncMock(
            side_effect=RuntimeError("Source process crashed")
        )

        # Register source process
        sdl_system.proc_map["Source(0.0)"] = mock_source

        # Create signal from source to nonexistent destination
        signal = SdlSignal.create()
        signal.set_src("Source(0.0)")
        signal.set_dst("NonExistent(0.0)")

        with patch("pysdl.system.SdlLogger.warning") as mock_warning:
            result = await sdl_system.output(signal)

            assert result is False
            # Verify warning was logged for error signal delivery failure
            warning_calls = [str(call) for call in mock_warning.call_args_list]
            assert any(
                "Failed to send error signal to source" in call
                for call in warning_calls
            )

    # =====================================================================
    # startTimer() Error Paths
    # =====================================================================

    def test_start_timer_with_no_source_pid_raises_timer_error(
        self, sdl_system
    ) -> None:
        """Test starting timer with no source PID raises TimerError.

        Covers line 243: Timer with no source PID.
        """
        timer = SdlTimer.create()
        timer.set_src("")  # Empty source

        with pytest.raises(TimerError, match="Timer has no source PID"):
            sdl_system.startTimer(timer)

    def test_start_timer_handles_validation_error_from_stop_timer(
        self, sdl_system
    ) -> None:
        """Test startTimer handles ValidationError from stopTimer gracefully.

        Covers lines 249-251: ValidationError handling in startTimer.
        This path is executed when stopTimer raises ValidationError, which
        is caught and ignored (timer not running is fine).
        """
        timer = SdlTimer.create()
        timer.set_src("Process(0.0)")

        # Mock stopTimer to raise ValidationError
        with patch.object(
            sdl_system, "stopTimer", side_effect=ValidationError("timer", "Test error")
        ):
            # This should not raise - ValidationError is caught
            sdl_system.startTimer(timer)

            # Timer should be started despite ValidationError
            assert "Process(0.0)" in sdl_system.timer_map
            assert timer in sdl_system.timer_map["Process(0.0)"]

    # =====================================================================
    # stopTimer() Error Paths
    # =====================================================================

    def test_stop_timer_with_no_source_pid_logs_warning(self, sdl_system) -> None:
        """Test stopping timer with no source PID logs warning and returns False.

        Covers lines 277-278: Warning when timer has no source.
        """
        timer = SdlTimer.create()
        timer.set_src("")  # Empty source

        with patch("pysdl.system.SdlLogger.warning") as mock_warning:
            result = sdl_system.stopTimer(timer)

            assert result is False
            mock_warning.assert_called()
            assert "has no source PID" in str(mock_warning.call_args)

    # =====================================================================
    # get_next_signal() Error Paths
    # =====================================================================

    @pytest.mark.asyncio
    async def test_get_next_signal_queue_get_failure_raises_queue_error(
        self, sdl_system
    ) -> None:
        """Test get_next_signal raises QueueError when queue.get fails.

        Covers lines 306-308: Queue operation failure in get_next_signal.
        """
        # Mock the queue to raise an exception
        with patch.object(sdl_system, "_get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.get.side_effect = RuntimeError("Queue corrupted")
            mock_get_queue.return_value = mock_queue

            with pytest.raises(QueueError, match="Failed to get signal from queue"):
                await sdl_system.get_next_signal()

    # =====================================================================
    # _process_signal() Error Paths
    # =====================================================================

    @pytest.mark.asyncio
    async def test_process_signal_with_nonexistent_destination(
        self, sdl_system
    ) -> None:
        """Test _process_signal when destination process doesn't exist.

        Covers lines 319-322: Warning when destination not found.
        """
        signal = SdlSignal.create()
        signal.set_dst("NonExistent(0.0)")

        with patch("pysdl.system.SdlLogger.warning") as mock_warning:
            await sdl_system._process_signal(signal)

            mock_warning.assert_called()
            assert (
                "destination process not found" in str(mock_warning.call_args).lower()
            )

    @pytest.mark.asyncio
    async def test_process_signal_with_no_handler(self, sdl_system) -> None:
        """Test _process_signal when no handler exists for signal.

        Covers lines 324-327: Logging when no signal handler found.
        """
        # Create and register a real process
        process = TestProcess(None, system=sdl_system)
        sdl_system.register(process)

        # Create a signal type that has no handler
        class UnhandledSignal(SdlSignal):
            pass

        signal = UnhandledSignal.create()
        signal.set_dst(process.pid())

        with patch("pysdl.system.SdlLogger.signal") as mock_log_signal:
            await sdl_system._process_signal(signal)

            # Should log "SdlSig-NA" for unhandled signal
            signal_calls = [str(call) for call in mock_log_signal.call_args_list]
            assert any("SdlSig-NA" in call for call in signal_calls)

    # NOTE: Lines 329-333 (signal handler exception) are difficult to test
    # in isolation because they require the state machine to properly register
    # a handler that then raises an exception. This would require deeper integration
    # testing with the state machine. These lines are defensive error handling
    # that prevent the system from crashing if a user's handler fails.
    # Coverage: Acceptable to leave as defensive code without explicit test.

    # =====================================================================
    # expire() Error Paths
    # =====================================================================

    @pytest.mark.asyncio
    async def test_expire_timer_delivery_failure_logs_warning(self, sdl_system) -> None:
        """Test expire logs warning when timer delivery fails.

        Covers lines 423-428: Exception handling when delivering expired timer.
        """
        # Create a process that will fail on timer delivery
        mock_process = Mock(spec=SdlProcess)
        mock_process.pid.return_value = "Process(0.0)"
        mock_process.input = AsyncMock(side_effect=RuntimeError("Process crashed"))

        sdl_system.proc_map["Process(0.0)"] = mock_process

        # Create and start an expired timer
        timer = SdlTimer.create()
        timer.set_src("Process(0.0)")
        timer.set_dst("Process(0.0)")
        timer.start(100)  # Will expire at 100ms

        sdl_system.startTimer(timer)

        with patch("pysdl.system.SdlLogger.warning") as mock_warning:
            # Expire at 200ms - timer should expire
            await sdl_system.expire(200)

            # Warning should be logged
            mock_warning.assert_called()
            warning_calls = [str(call) for call in mock_warning.call_args_list]
            assert any(
                "failed to deliver expired timer" in call.lower()
                for call in warning_calls
            )

            # Timer should still be removed despite delivery failure
            assert "Process(0.0)" not in sdl_system.timer_map

    @pytest.mark.asyncio
    async def test_expire_timer_expiration_check_exception_logs_warning(
        self, sdl_system
    ) -> None:
        """Test expire logs warning when timer.expire() raises exception.

        Covers lines 429-432: Exception handling during timer expiration check.
        """
        # Create a mock timer that fails on expire check
        mock_timer = Mock(spec=SdlTimer)
        mock_timer.src.return_value = "Process(0.0)"
        mock_timer.expire.side_effect = RuntimeError("Timer corrupted")

        # Add timer directly to timer_map
        sdl_system.timer_map["Process(0.0)"] = [mock_timer]

        with patch("pysdl.system.SdlLogger.warning") as mock_warning:
            # Should not raise - exception is caught
            await sdl_system.expire(200)

            mock_warning.assert_called()
            warning_calls = [str(call) for call in mock_warning.call_args_list]
            assert any(
                "error checking timer expiration" in call.lower()
                for call in warning_calls
            )

    @pytest.mark.asyncio
    async def test_expire_stop_timer_failure_logs_warning(self, sdl_system) -> None:
        """Test expire logs warning when stopTimer raises exception.

        Covers lines 438-440: Exception handling when removing expired timer.
        """
        # Create a valid expired timer
        timer = SdlTimer.create()
        timer.set_src("Process(0.0)")
        timer.set_dst("Process(0.0)")
        timer.start(100)

        sdl_system.startTimer(timer)

        # Create process to allow delivery
        process = TestProcess(None, system=sdl_system)
        sdl_system.proc_map["Process(0.0)"] = process

        # Mock stopTimer to raise exception
        with (
            patch.object(
                sdl_system, "stopTimer", side_effect=RuntimeError("Cannot stop timer")
            ),
            patch("pysdl.system.SdlLogger.warning") as mock_warning,
        ):
            await sdl_system.expire(200)

            # Warning should be logged for stopTimer failure
            warning_calls = [str(call) for call in mock_warning.call_args_list]
            assert any(
                "error removing expired timer" in call.lower() for call in warning_calls
            )

    @pytest.mark.asyncio
    async def test_expire_already_stopped_timer_logs_warning(self, sdl_system) -> None:
        """Test expire logs warning when timer was already stopped.

        Covers line 438: Warning when stopTimer returns False.
        """
        # Create a valid expired timer
        timer = SdlTimer.create()
        timer.set_src("Process(0.0)")
        timer.set_dst("Process(0.0)")
        timer.start(100)

        sdl_system.startTimer(timer)

        # Create process to allow delivery
        process = TestProcess(None, system=sdl_system)
        sdl_system.proc_map["Process(0.0)"] = process

        # Mock stopTimer to return False (already stopped)
        with patch.object(sdl_system, "stopTimer", return_value=False):
            with patch("pysdl.system.SdlLogger.warning") as mock_warning:
                await sdl_system.expire(200)

                # Warning should be logged
                warning_calls = [str(call) for call in mock_warning.call_args_list]
                assert any(
                    "was already stopped" in call.lower() for call in warning_calls
                )
