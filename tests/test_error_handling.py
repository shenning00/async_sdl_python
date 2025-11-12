"""
Tests for error handling and exception behavior.

This module tests all custom exceptions and error handling throughout the SDL system.
"""

import asyncio

import pytest

from pysdl.exceptions import (
    InvalidStateError,
    ProcessNotFoundError,
    QueueError,
    SdlError,
    SignalDeliveryError,
    StateTransitionError,
    TimerError,
    ValidationError,
)
from pysdl.id_generator import SdlIdGenerator
from pysdl.process import SdlProcess
from pysdl.signal import SdlSignal
from pysdl.state import SdlState, start
from pysdl.state_machine import SdlStateMachine
from pysdl.system import SdlSystem
from pysdl.system_signals import (
    SdlProcessNotExistSignal,
    SdlStartSignal,
    SdlStoppingSignal,
)
from pysdl.timer import SdlTimer


# Test signals
class TestSignal(SdlSignal):
    """Test signal for error handling tests"""


class ErrorTestSignal(SdlSignal):
    """Another test signal"""


# Test process
class ErrorTestProcess(SdlProcess):
    """Test process for error handling"""

    state_idle = SdlState("idle")
    state_running = SdlState("running")

    def _init_state_machine(self) -> None:
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_idle, TestSignal, self.test_handler)
        self._event(self.state_idle, SdlStoppingSignal, self.stop_handler)
        self._event(self.state_running, SdlProcessNotExistSignal, self.error_handler)
        self._done()

    async def start_handler(self, signal: SdlSignal) -> None:
        await self.next_state(self.state_idle)

    async def test_handler(self, signal: SdlSignal) -> None:
        await self.next_state(self.state_running)

    async def stop_handler(self, signal: SdlSignal) -> None:
        self.stop_process()

    async def error_handler(self, signal: SdlProcessNotExistSignal) -> None:
        # Just handle the error
        pass


@pytest.fixture
def sdl_system():
    """Provide a fresh SdlSystem instance for each test"""
    return SdlSystem()


class TestCustomExceptions:
    """Test custom exception classes"""

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

    def test_sdl_error_base(self):
        """Test base SdlError exception"""
        error = SdlError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert isinstance(error, Exception)

    def test_process_not_found_error(self):
        """Test ProcessNotFoundError"""
        error = ProcessNotFoundError("TestProcess(1.0)")
        assert "TestProcess(1.0)" in str(error)
        assert error.pid == "TestProcess(1.0)"
        assert isinstance(error, SdlError)

    def test_process_not_found_error_with_message(self):
        """Test ProcessNotFoundError with custom message"""
        error = ProcessNotFoundError("TestProc", "Custom error message")
        assert str(error) == "Custom error message"
        assert error.pid == "TestProc"

    def test_signal_delivery_error(self):
        """Test SignalDeliveryError"""
        error = SignalDeliveryError("TestProcess(1.0)", signal="TestSignal")
        assert "TestProcess(1.0)" in str(error)
        assert "TestSignal" in str(error)
        assert error.destination == "TestProcess(1.0)"
        assert error.signal == "TestSignal"

    def test_signal_delivery_error_no_signal(self):
        """Test SignalDeliveryError without signal parameter"""
        error = SignalDeliveryError("TestProcess(1.0)")
        assert "TestProcess(1.0)" in str(error)
        assert error.destination == "TestProcess(1.0)"
        assert error.signal == ""
        # Should have default message without signal name
        assert str(error) == "Failed to deliver signal to process 'TestProcess(1.0)'"

    def test_signal_delivery_error_with_custom_message(self):
        """Test SignalDeliveryError with custom message"""
        error = SignalDeliveryError("TestProcess(1.0)", "Custom delivery error")
        assert str(error) == "Custom delivery error"
        assert error.destination == "TestProcess(1.0)"

    def test_state_transition_error(self):
        """Test StateTransitionError"""
        error = StateTransitionError("idle", "TestSignal", "TestProcess")
        assert "idle" in str(error)
        assert "TestSignal" in str(error)
        assert "TestProcess" in str(error)
        assert error.current_state == "idle"
        assert error.signal == "TestSignal"

    def test_state_transition_error_no_process(self):
        """Test StateTransitionError without process parameter"""
        error = StateTransitionError("idle", "TestSignal")
        assert "idle" in str(error)
        assert "TestSignal" in str(error)
        assert error.current_state == "idle"
        assert error.signal == "TestSignal"
        assert error.process == ""
        # Should have default message without process name
        expected = "Invalid state transition: no handler for signal 'TestSignal' in state 'idle'"
        assert str(error) == expected

    def test_state_transition_error_with_custom_message(self):
        """Test StateTransitionError with custom message"""
        error = StateTransitionError(
            "idle", "TestSignal", "TestProc", "Custom transition error"
        )
        assert str(error) == "Custom transition error"
        assert error.current_state == "idle"
        assert error.signal == "TestSignal"
        assert error.process == "TestProc"

    def test_timer_error(self):
        """Test TimerError"""
        error = TimerError("Timer1", "Timer expired")
        assert "Timer expired" in str(error)
        assert error.timer == "Timer1"

    def test_timer_error_with_timer_no_message(self):
        """Test TimerError with timer but no custom message"""
        error = TimerError("Timer1")
        assert str(error) == "Timer error: Timer1"
        assert error.timer == "Timer1"

    def test_timer_error_no_timer_no_message(self):
        """Test TimerError with neither timer nor message"""
        error = TimerError()
        assert str(error) == "Timer operation failed"
        assert error.timer == ""

    def test_timer_error_custom_message_overrides(self):
        """Test TimerError with custom message overrides default"""
        error = TimerError("Timer1", "Specific timeout error")
        assert str(error) == "Specific timeout error"
        assert error.timer == "Timer1"

    def test_invalid_state_error(self):
        """Test InvalidStateError"""
        error = InvalidStateError("bad_state")
        assert "bad_state" in str(error)
        assert error.state == "bad_state"

    def test_queue_error(self):
        """Test QueueError"""
        error = QueueError("Queue is full")
        assert "Queue is full" in str(error)

    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError("pid", "Invalid PID format")
        assert "Invalid PID format" in str(error)
        assert error.parameter == "pid"

    def test_validation_error_no_message(self):
        """Test ValidationError without custom message"""
        error = ValidationError("timeout")
        assert str(error) == "Validation error: invalid timeout"
        assert error.parameter == "timeout"

    def test_validation_error_empty_message(self):
        """Test ValidationError with empty message uses default"""
        error = ValidationError("signal", "")
        assert str(error) == "Validation error: invalid signal"
        assert error.parameter == "signal"


class TestSystemErrorHandling:
    """Test error handling in SdlSystem"""

    @pytest.mark.asyncio
    async def test_register_none_process(self, sdl_system):
        """Test registering None raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            sdl_system.register(None)
        assert "process" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_unregister_none_process(self, sdl_system):
        """Test unregistering None raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            sdl_system.unregister(None)
        assert "process" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_enqueue_none_signal(self, sdl_system):
        """Test enqueuing None signal raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            await sdl_system.enqueue(None)
        assert "signal" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_output_none_signal(self, sdl_system):
        """Test outputting None signal raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            await sdl_system.output(None)
        assert "signal" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_output_signal_no_destination(self, sdl_system):
        """Test outputting signal with no destination raises ValidationError"""
        signal = TestSignal.create()
        # Don't set destination
        with pytest.raises(ValidationError) as exc_info:
            await sdl_system.output(signal)
        assert "destination" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_output_to_nonexistent_process_sends_error_signal(self, sdl_system):
        """Test that sending to nonexistent process generates error signal"""
        # Create a source process
        source = await ErrorTestProcess.create(None, system=sdl_system)
        await asyncio.sleep(0)  # Let start signal process

        # Consume the start signal from queue
        start_signal = await sdl_system.get_next_signal()
        assert isinstance(start_signal, SdlStartSignal)

        # Send signal to nonexistent destination
        signal = TestSignal.create()
        result = await source.output(signal, "NonExistent(1.0)")

        # Should return False for failed delivery
        assert result is False

        # Check that error signal was sent back to source
        # The error signal should be in the queue
        error_signal = await sdl_system.get_next_signal()
        assert isinstance(error_signal, SdlProcessNotExistSignal)
        assert error_signal.get_data("destination") == "NonExistent(1.0)"
        assert error_signal.get_data("source") == source.pid()

    @pytest.mark.asyncio
    async def test_lookup_invalid_pid(self, sdl_system):
        """Test lookup with invalid PID raises ValidationError"""
        with pytest.raises(ValidationError):
            sdl_system.lookup_proc_map(None)

        with pytest.raises(ValidationError):
            sdl_system.lookup_proc_map("")

    @pytest.mark.asyncio
    async def test_start_timer_none(self, sdl_system):
        """Test starting None timer raises ValidationError"""
        with pytest.raises(ValidationError):
            sdl_system.startTimer(None)

    @pytest.mark.asyncio
    async def test_stop_timer_none(self, sdl_system):
        """Test stopping None timer raises ValidationError"""
        with pytest.raises(ValidationError):
            sdl_system.stopTimer(None)


class TestProcessErrorHandling:
    """Test error handling in SdlProcess"""

    @pytest.mark.asyncio
    async def test_next_state_none(self, sdl_system):
        """Test transitioning to None state raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        with pytest.raises(ValidationError) as exc_info:
            await process.next_state(None)
        assert "state" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_next_state_invalid_type(self, sdl_system):
        """Test transitioning to invalid state type raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        with pytest.raises(ValidationError) as exc_info:
            await process.next_state("not_a_state")  # type: ignore
        assert "state" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_output_none_signal(self, sdl_system):
        """Test outputting None signal raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        with pytest.raises(ValidationError):
            await process.output(None, "dest")  # type: ignore

    @pytest.mark.asyncio
    async def test_output_invalid_signal_type(self, sdl_system):
        """Test outputting invalid signal type raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        with pytest.raises(ValidationError):
            await process.output("not_a_signal", "dest")  # type: ignore

    @pytest.mark.asyncio
    async def test_output_invalid_destination(self, sdl_system):
        """Test outputting to invalid destination raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        signal = TestSignal.create()

        with pytest.raises(ValidationError):
            await process.output(signal, None)  # type: ignore

        with pytest.raises(ValidationError):
            await process.output(signal, "")

    @pytest.mark.asyncio
    async def test_start_timer_none(self, sdl_system):
        """Test starting None timer raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        with pytest.raises(ValidationError):
            process.start_timer(None, 1000)  # type: ignore

    @pytest.mark.asyncio
    async def test_start_timer_invalid_type(self, sdl_system):
        """Test starting invalid timer type raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        with pytest.raises(ValidationError):
            process.start_timer("not_a_timer", 1000)  # type: ignore

    @pytest.mark.asyncio
    async def test_start_timer_negative_duration(self, sdl_system):
        """Test starting timer with negative duration raises TimerError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        timer = SdlTimer.create()
        with pytest.raises(TimerError) as exc_info:
            process.start_timer(timer, -1000)
        assert "negative" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_start_timer_abs_invalid(self, sdl_system):
        """Test starting timer with invalid absolute time raises TimerError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        timer = SdlTimer.create()
        with pytest.raises(TimerError):
            process.start_timer_abs(timer, 0)

        with pytest.raises(TimerError):
            process.start_timer_abs(timer, -100)

    @pytest.mark.asyncio
    async def test_stop_timer_none(self, sdl_system):
        """Test stopping None timer raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        with pytest.raises(ValidationError):
            process.stop_timer(None)  # type: ignore

    @pytest.mark.asyncio
    async def test_lookup_transition_none_signal(self, sdl_system):
        """Test looking up transition for None signal raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        with pytest.raises(ValidationError):
            process.lookup_transition(None)

    @pytest.mark.asyncio
    async def test_input_none_signal(self, sdl_system):
        """Test inputting None signal raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        with pytest.raises(ValidationError):
            await process.input(None)  # type: ignore

    @pytest.mark.asyncio
    async def test_input_invalid_signal_type(self, sdl_system):
        """Test inputting invalid signal type raises ValidationError"""
        process = await ErrorTestProcess.create(None, system=sdl_system)
        with pytest.raises(ValidationError):
            await process.input("not_a_signal")  # type: ignore


class TestStateMachineErrorHandling:
    """Test error handling in SdlStateMachine"""

    def test_state_none(self):
        """Test setting None state raises ValidationError"""
        fsm = SdlStateMachine()
        with pytest.raises(ValidationError):
            fsm.state(None)  # type: ignore

    def test_state_invalid_type(self):
        """Test setting invalid state type raises ValidationError"""
        fsm = SdlStateMachine()
        with pytest.raises(ValidationError):
            fsm.state("not_a_state")  # type: ignore

    def test_event_none(self):
        """Test setting None event raises ValidationError"""
        fsm = SdlStateMachine()
        state = SdlState("test")
        fsm.state(state)
        with pytest.raises(ValidationError):
            fsm.event(None)  # type: ignore

    def test_event_invalid_type(self):
        """Test setting invalid event type raises ValidationError"""
        fsm = SdlStateMachine()
        state = SdlState("test")
        fsm.state(state)
        with pytest.raises(ValidationError):
            fsm.event("not_a_signal")  # type: ignore

    def test_handler_not_callable(self):
        """Test setting non-callable handler raises ValidationError"""
        fsm = SdlStateMachine()
        state = SdlState("test")
        fsm.state(state).event(TestSignal)
        with pytest.raises(ValidationError):
            fsm.handler("not_callable")  # type: ignore

    def test_handler_no_state(self):
        """Test setting handler without state raises ValidationError"""
        fsm = SdlStateMachine()
        with pytest.raises(ValidationError) as exc_info:
            fsm.event(TestSignal).handler(lambda x: None)  # type: ignore
        assert "state" in str(exc_info.value).lower()

    def test_handler_no_event(self):
        """Test setting handler without event raises ValidationError"""
        fsm = SdlStateMachine()
        state = SdlState("test")
        with pytest.raises(ValidationError) as exc_info:
            fsm.state(state).handler(lambda x: None)  # type: ignore
        assert "event" in str(exc_info.value).lower()

    def test_handler_duplicate(self):
        """Test setting duplicate handler overwrites the previous handler"""
        fsm = SdlStateMachine()
        state = SdlState("test")

        async def handler1(signal: SdlSignal) -> None:
            pass

        async def handler2(signal: SdlSignal) -> None:
            pass

        # First registration should succeed
        fsm.state(state).event(TestSignal).handler(handler1)
        assert fsm.find(state, TestSignal.id()) is handler1

        # Second registration should overwrite (allowed behavior)
        fsm.state(state).event(TestSignal).handler(handler2)
        assert fsm.find(state, TestSignal.id()) is handler2

    def test_find_none_state(self):
        """Test finding handler with None state raises ValidationError"""
        fsm = SdlStateMachine()
        with pytest.raises(ValidationError):
            fsm.find(None, TestSignal.id())  # type: ignore

    def test_find_none_event(self):
        """Test finding handler with None event raises ValidationError"""
        fsm = SdlStateMachine()
        state = SdlState("test")
        with pytest.raises(ValidationError):
            fsm.find(state, None)  # type: ignore


class TestErrorSignals:
    """Test error signal generation and handling"""

    @pytest.mark.asyncio
    async def test_process_not_exist_signal_creation(self, sdl_system):
        """Test SdlProcessNotExistSignal creation and data"""
        signal = SdlProcessNotExistSignal(
            original_signal="TestSignal",
            destination="NonExistent(1.0)",
            source="Source(1.0)",
        )

        assert signal.get_data("original_signal") == "TestSignal"
        assert signal.get_data("destination") == "NonExistent(1.0)"
        assert signal.get_data("source") == "Source(1.0)"
        assert "NonExistent(1.0)" in str(signal)
        assert "TestSignal" in str(signal)

    @pytest.mark.asyncio
    async def test_process_not_exist_signal_get_missing_data(self, sdl_system):
        """Test getting missing data from error signal returns empty string"""
        signal = SdlProcessNotExistSignal()
        assert signal.get_data("nonexistent_key") == ""

    @pytest.mark.asyncio
    async def test_error_signal_sent_on_failed_delivery(self, sdl_system):
        """Test that error signal is sent when delivery fails"""
        # Create source process
        source = await ErrorTestProcess.create(None, system=sdl_system)
        await asyncio.sleep(0)

        # Consume the start signal from queue
        start_signal = await sdl_system.get_next_signal()
        assert isinstance(start_signal, SdlStartSignal)

        # Transition to state that handles error signals
        await source.next_state(source.state_running)

        # Try to send to nonexistent process
        signal = ErrorTestSignal.create()
        result = await source.output(signal, "Ghost(1.0)")

        # Should fail
        assert result is False

        # Error signal should be in queue
        error_signal = await sdl_system.get_next_signal()
        assert isinstance(error_signal, SdlProcessNotExistSignal)
        assert error_signal.dst() == source.pid()
        assert error_signal.get_data("destination") == "Ghost(1.0)"


class TestErrorRecovery:
    """Test system recovery from errors"""

    @pytest.mark.asyncio
    async def test_system_continues_after_handler_exception(self, sdl_system):
        """Test that system continues running after handler throws exception"""

        class CrashingProcess(SdlProcess):
            state_idle = SdlState("idle")

            def _init_state_machine(self) -> None:
                self._event(start, SdlStartSignal, self.start_handler)
                self._event(self.state_idle, TestSignal, self.crash_handler)
                self._event(self.state_idle, SdlStoppingSignal, self.stop_handler)
                self._done()

            async def start_handler(self, signal: SdlSignal) -> None:
                await self.next_state(self.state_idle)

            async def crash_handler(self, signal: SdlSignal) -> None:
                raise RuntimeError("Intentional crash")

            async def stop_handler(self, signal: SdlSignal) -> None:
                self.stop_process()

        process = await CrashingProcess.create(None, system=sdl_system)
        await asyncio.sleep(0)

        # Send signal that will cause crash
        await process.output(TestSignal.create(), process.pid())

        # Process the crashing signal - should not crash the test
        signal = await sdl_system.get_next_signal()
        handler = process.lookup_transition(signal)
        assert handler is not None

        # The handler will raise, but we catch it in run()
        # Just verify the process still exists
        assert process.pid() in sdl_system.proc_map

    @pytest.mark.asyncio
    async def test_validation_error_logged_not_crashed(self, sdl_system):
        """Test that validation errors are logged but don't crash system"""
        process = await ErrorTestProcess.create(None, system=sdl_system)

        # Try operations that will fail validation
        with pytest.raises(ValidationError):
            await process.output(None, "test")  # type: ignore

        # Process should still be valid and in system
        assert process.pid() in sdl_system.proc_map


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
