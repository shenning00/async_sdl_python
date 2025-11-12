"""Tests for pysdl.logger module.

This test suite covers the SdlLogger class including:
- Configuration via API and environment variables
- Log level management
- Category-based logging control
- All logging methods (info, debug, warning, error)
- Specialized logging methods (signal, state, create, event, app)
- Configuration validation and error handling
"""

import logging
import os
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

from pysdl.logger import LogCategory, SdlLogger
from pysdl.process import SdlProcess
from pysdl.signal import SdlSignal
from pysdl.state import SdlState


@pytest.fixture
def reset_logger() -> Generator[None, None, None]:
    """Reset logger to default state before and after each test.

    This ensures tests don't interfere with each other due to
    the static nature of SdlLogger.
    """
    # Reset before test
    SdlLogger._configured = False
    SdlLogger._enabled_categories = {
        LogCategory.SIGNALS: True,
        LogCategory.STATES: True,
        LogCategory.PROCESSES: True,
        LogCategory.TIMERS: True,
        LogCategory.SYSTEM: True,
        LogCategory.APPLICATION: True,
    }
    SdlLogger._min_level = logging.DEBUG
    SdlLogger._logger.setLevel(logging.DEBUG)

    # Clear any environment variables
    env_vars_to_clear = ["SDL_LOG_LEVEL", "SDL_LOG_CATEGORIES"]
    old_env = {}
    for var in env_vars_to_clear:
        if var in os.environ:
            old_env[var] = os.environ[var]
            del os.environ[var]

    yield

    # Reset after test
    SdlLogger._configured = False
    SdlLogger._enabled_categories = {
        LogCategory.SIGNALS: True,
        LogCategory.STATES: True,
        LogCategory.PROCESSES: True,
        LogCategory.TIMERS: True,
        LogCategory.SYSTEM: True,
        LogCategory.APPLICATION: True,
    }
    SdlLogger._min_level = logging.DEBUG
    SdlLogger._logger.setLevel(logging.DEBUG)

    # Restore environment variables
    for var, value in old_env.items():
        os.environ[var] = value


@pytest.fixture
def mock_process() -> MagicMock:
    """Create a mock process for testing logging methods."""
    process = MagicMock(spec=SdlProcess)
    process.pid.return_value = "test_pid_123"
    process.name.return_value = "TestProcess"
    process.current_state.return_value = "idle"
    return process


@pytest.fixture
def mock_signal() -> MagicMock:
    """Create a mock signal for testing signal logging."""
    signal = MagicMock(spec=SdlSignal)
    signal.name.return_value = "TestSignal"
    signal.id.return_value = 42
    signal.src.return_value = "src_pid_456"
    signal.dst.return_value = "dst_pid_789"
    signal.dumpdata.return_value = "signal_data"
    return signal


@pytest.fixture
def mock_state() -> MagicMock:
    """Create a mock state for testing state transition logging."""
    state = MagicMock(spec=SdlState)
    state.__str__.return_value = "test_state"
    return state


class TestLogCategory:
    """Test LogCategory enum."""

    def test_all_categories_defined(self) -> None:
        """Verify all expected log categories exist."""
        expected_categories = {
            "signals",
            "states",
            "processes",
            "timers",
            "system",
            "application",
        }
        actual_categories = {cat.value for cat in LogCategory}
        assert actual_categories == expected_categories

    def test_category_values_are_strings(self) -> None:
        """Verify category values are lowercase strings."""
        for category in LogCategory:
            assert isinstance(category.value, str)
            assert category.value.islower()


class TestSdlLoggerConfiguration:
    """Test SdlLogger configuration methods."""

    def test_configure_log_level_info(self, reset_logger: None) -> None:
        """Test configuring log level to INFO."""
        SdlLogger.configure(level="INFO")

        assert SdlLogger._min_level == logging.INFO
        assert SdlLogger._logger.level == logging.INFO
        assert SdlLogger._configured is True

    def test_configure_log_level_warning(self, reset_logger: None) -> None:
        """Test configuring log level to WARNING."""
        SdlLogger.configure(level="WARNING")

        assert SdlLogger._min_level == logging.WARNING
        assert SdlLogger._logger.level == logging.WARNING

    def test_configure_log_level_error(self, reset_logger: None) -> None:
        """Test configuring log level to ERROR."""
        SdlLogger.configure(level="ERROR")

        assert SdlLogger._min_level == logging.ERROR
        assert SdlLogger._logger.level == logging.ERROR

    def test_configure_log_level_critical(self, reset_logger: None) -> None:
        """Test configuring log level to CRITICAL."""
        SdlLogger.configure(level="CRITICAL")

        assert SdlLogger._min_level == logging.CRITICAL
        assert SdlLogger._logger.level == logging.CRITICAL

    def test_configure_log_level_case_insensitive(self, reset_logger: None) -> None:
        """Test that log level configuration is case-insensitive."""
        SdlLogger.configure(level="info")
        assert SdlLogger._min_level == logging.INFO

        SdlLogger.configure(level="WaRnInG")
        assert SdlLogger._min_level == logging.WARNING

    def test_configure_invalid_log_level(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that invalid log level generates warning."""
        with caplog.at_level(logging.WARNING):
            SdlLogger.configure(level="INVALID_LEVEL")

        assert "Invalid log level: INVALID_LEVEL" in caplog.text
        # Should keep previous level
        assert SdlLogger._min_level == logging.DEBUG

    def test_configure_disable_category(self, reset_logger: None) -> None:
        """Test disabling a specific log category."""
        SdlLogger.configure(categories={"signals": False})

        assert SdlLogger._enabled_categories[LogCategory.SIGNALS] is False
        # Other categories should remain enabled
        assert SdlLogger._enabled_categories[LogCategory.STATES] is True

    def test_configure_enable_specific_categories(self, reset_logger: None) -> None:
        """Test enabling only specific categories."""
        SdlLogger.configure(
            categories={
                "signals": True,
                "states": False,
                "processes": False,
                "timers": False,
                "system": False,
                "application": False,
            }
        )

        assert SdlLogger._enabled_categories[LogCategory.SIGNALS] is True
        assert SdlLogger._enabled_categories[LogCategory.STATES] is False
        assert SdlLogger._enabled_categories[LogCategory.PROCESSES] is False

    def test_configure_invalid_category(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that invalid category generates warning."""
        with caplog.at_level(logging.WARNING):
            SdlLogger.configure(categories={"invalid_category": True})

        assert "Invalid log category: invalid_category" in caplog.text

    def test_configure_reset(self, reset_logger: None) -> None:
        """Test reset functionality restores defaults."""
        # First change some settings
        SdlLogger.configure(
            level="ERROR", categories={"signals": False, "states": False}
        )

        # Verify they changed
        assert SdlLogger._min_level == logging.ERROR
        assert SdlLogger._enabled_categories[LogCategory.SIGNALS] is False

        # Reset to defaults
        SdlLogger.configure(reset=True)

        # Verify defaults restored
        assert SdlLogger._min_level == logging.DEBUG
        assert SdlLogger._logger.level == logging.DEBUG
        assert all(enabled for enabled in SdlLogger._enabled_categories.values())

    def test_configure_reset_with_new_settings(self, reset_logger: None) -> None:
        """Test reset=True followed by new settings."""
        # Set initial non-default state
        SdlLogger.configure(level="ERROR")
        assert SdlLogger._min_level == logging.ERROR

        # Reset and apply new settings
        SdlLogger.configure(reset=True, level="WARNING")

        assert SdlLogger._min_level == logging.WARNING

    def test_configure_env_log_level(self, reset_logger: None) -> None:
        """Test configuration from SDL_LOG_LEVEL environment variable."""
        os.environ["SDL_LOG_LEVEL"] = "WARNING"

        SdlLogger.configure()

        assert SdlLogger._min_level == logging.WARNING

    def test_configure_env_categories(self, reset_logger: None) -> None:
        """Test configuration from SDL_LOG_CATEGORIES environment variable."""
        os.environ["SDL_LOG_CATEGORIES"] = "signals,states"

        SdlLogger.configure()

        # Only specified categories should be enabled
        assert SdlLogger._enabled_categories[LogCategory.SIGNALS] is True
        assert SdlLogger._enabled_categories[LogCategory.STATES] is True
        assert SdlLogger._enabled_categories[LogCategory.PROCESSES] is False
        assert SdlLogger._enabled_categories[LogCategory.TIMERS] is False
        assert SdlLogger._enabled_categories[LogCategory.SYSTEM] is False
        assert SdlLogger._enabled_categories[LogCategory.APPLICATION] is False

    def test_configure_env_categories_with_whitespace(self, reset_logger: None) -> None:
        """Test parsing categories with whitespace."""
        os.environ["SDL_LOG_CATEGORIES"] = "signals , states , processes"

        SdlLogger.configure()

        assert SdlLogger._enabled_categories[LogCategory.SIGNALS] is True
        assert SdlLogger._enabled_categories[LogCategory.STATES] is True
        assert SdlLogger._enabled_categories[LogCategory.PROCESSES] is True
        assert SdlLogger._enabled_categories[LogCategory.TIMERS] is False

    def test_configure_env_overrides_api_level(self, reset_logger: None) -> None:
        """Test that environment variables override API level parameter.

        Note: The implementation gives env variables priority over direct
        API parameters for level. This is by design - env variables are
        checked and override the level parameter if present.
        """
        os.environ["SDL_LOG_LEVEL"] = "WARNING"

        # Even though we pass ERROR, env var takes precedence
        SdlLogger.configure(level="ERROR")

        # Environment variable should win
        assert SdlLogger._min_level == logging.WARNING

    def test_configure_env_categories_ignored_if_api_provided(
        self, reset_logger: None
    ) -> None:
        """Test env categories ignored when API categories provided."""
        os.environ["SDL_LOG_CATEGORIES"] = "signals"

        SdlLogger.configure(categories={"states": True, "processes": False})

        # Should use API categories, not env
        assert SdlLogger._enabled_categories[LogCategory.STATES] is True
        # signals should still be True from defaults, not from env
        assert SdlLogger._enabled_categories[LogCategory.SIGNALS] is True


class TestSdlLoggerIsEnabled:
    """Test is_enabled() method for checking if logging is active."""

    def test_is_enabled_default_all_enabled(self, reset_logger: None) -> None:
        """Test that all categories are enabled by default."""
        assert SdlLogger.is_enabled(LogCategory.SIGNALS)
        assert SdlLogger.is_enabled(LogCategory.STATES)
        assert SdlLogger.is_enabled(LogCategory.PROCESSES)
        assert SdlLogger.is_enabled(LogCategory.TIMERS)
        assert SdlLogger.is_enabled(LogCategory.SYSTEM)
        assert SdlLogger.is_enabled(LogCategory.APPLICATION)

    def test_is_enabled_respects_category_setting(self, reset_logger: None) -> None:
        """Test that is_enabled respects category configuration."""
        SdlLogger.configure(categories={"signals": False})

        assert not SdlLogger.is_enabled(LogCategory.SIGNALS)
        assert SdlLogger.is_enabled(LogCategory.STATES)

    def test_is_enabled_respects_log_level(self, reset_logger: None) -> None:
        """Test that is_enabled respects log level."""
        SdlLogger.configure(level="ERROR")

        # DEBUG level should not be enabled when min level is ERROR
        assert not SdlLogger.is_enabled(LogCategory.SIGNALS, logging.DEBUG)
        # ERROR level should be enabled
        assert SdlLogger.is_enabled(LogCategory.SIGNALS, logging.ERROR)

    def test_is_enabled_auto_configures_from_env(self, reset_logger: None) -> None:
        """Test that is_enabled auto-configures from environment on first use."""
        os.environ["SDL_LOG_CATEGORIES"] = "signals"

        # First call should trigger auto-configuration
        assert SdlLogger.is_enabled(LogCategory.SIGNALS)
        assert not SdlLogger.is_enabled(LogCategory.STATES)
        assert SdlLogger._configured is True


class TestSdlLoggerGetConfiguration:
    """Test get_configuration() method."""

    def test_get_configuration_default(self, reset_logger: None) -> None:
        """Test getting default configuration."""
        config = SdlLogger.get_configuration()

        assert config["level"] == "DEBUG"
        assert config["categories"]["signals"] is True
        assert config["categories"]["states"] is True
        assert config["categories"]["processes"] is True
        assert config["categories"]["timers"] is True
        assert config["categories"]["system"] is True
        assert config["categories"]["application"] is True

    def test_get_configuration_after_changes(self, reset_logger: None) -> None:
        """Test configuration reflects changes."""
        SdlLogger.configure(
            level="WARNING", categories={"signals": False, "states": True}
        )

        config = SdlLogger.get_configuration()

        assert config["level"] == "WARNING"
        assert config["categories"]["signals"] is False
        assert config["categories"]["states"] is True


class TestSdlLoggerBasicMethods:
    """Test basic logging methods: info, debug, warning, error."""

    def test_info_logs_message(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test info() method logs at INFO level."""
        with caplog.at_level(logging.INFO):
            SdlLogger.info("Test info message")

        assert "Test info message" in caplog.text
        assert caplog.records[0].levelname == "INFO"

    def test_info_respects_log_level(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test info() respects configured log level."""
        SdlLogger.configure(level="ERROR")

        with caplog.at_level(logging.INFO):
            SdlLogger.info("Should not appear")

        assert "Should not appear" not in caplog.text

    def test_debug_logs_message(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test debug() method logs at DEBUG level."""
        with caplog.at_level(logging.DEBUG):
            SdlLogger.debug("Test debug message")

        assert "Test debug message" in caplog.text
        assert caplog.records[0].levelname == "DEBUG"

    def test_debug_respects_log_level(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test debug() respects configured log level."""
        SdlLogger.configure(level="INFO")

        with caplog.at_level(logging.DEBUG):
            SdlLogger.debug("Should not appear")

        assert "Should not appear" not in caplog.text

    def test_warning_logs_message(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test warning() method logs at WARNING level."""
        with caplog.at_level(logging.WARNING):
            SdlLogger.warning("Test warning message")

        assert "Test warning message" in caplog.text
        assert caplog.records[0].levelname == "WARNING"

    def test_warning_respects_log_level(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test warning() respects configured log level."""
        SdlLogger.configure(level="ERROR")

        with caplog.at_level(logging.WARNING):
            SdlLogger.warning("Should not appear")

        assert "Should not appear" not in caplog.text

    def test_error_logs_message(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test error() method logs at ERROR level."""
        with caplog.at_level(logging.ERROR):
            SdlLogger.error("Test error message")

        assert "Test error message" in caplog.text
        assert caplog.records[0].levelname == "ERROR"


class TestSdlLoggerSignalMethod:
    """Test signal() method for logging signal events."""

    def test_signal_logs_when_enabled(
        self,
        reset_logger: None,
        mock_signal: MagicMock,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test signal() logs when SIGNALS category is enabled."""
        with caplog.at_level(logging.DEBUG):
            SdlLogger.signal("SdlSig", mock_signal, mock_process)

        # Verify the formatted output contains key information
        assert "SdlSig" in caplog.text
        assert "TestSignal" in caplog.text
        assert "(42)" in caplog.text  # signal ID

    def test_signal_not_logged_when_category_disabled(
        self,
        reset_logger: None,
        mock_signal: MagicMock,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test signal() doesn't log when SIGNALS category disabled."""
        SdlLogger.configure(categories={"signals": False})

        with caplog.at_level(logging.DEBUG):
            SdlLogger.signal("SdlSig", mock_signal, mock_process)

        assert "SdlSig" not in caplog.text

    def test_signal_not_logged_when_level_too_high(
        self,
        reset_logger: None,
        mock_signal: MagicMock,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test signal() doesn't log when log level too high."""
        SdlLogger.configure(level="ERROR")

        with caplog.at_level(logging.DEBUG):
            SdlLogger.signal("SdlSig", mock_signal, mock_process)

        assert "TestSignal" not in caplog.text


class TestSdlLoggerStateMethod:
    """Test state() method for logging state transitions."""

    def test_state_logs_when_enabled(
        self,
        reset_logger: None,
        mock_process: MagicMock,
        mock_state: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test state() logs when STATES category is enabled."""
        current_state = MagicMock(spec=SdlState)
        current_state.__str__.return_value = "old_state"
        current_state.__format__ = lambda self, spec: "old_state"
        new_state = MagicMock(spec=SdlState)
        new_state.__str__.return_value = "new_state"
        new_state.__format__ = lambda self, spec: "new_state"

        with caplog.at_level(logging.DEBUG):
            SdlLogger.state(mock_process, current_state, new_state)

        assert "SdlState" in caplog.text
        assert "newstate" in caplog.text

    def test_state_not_logged_when_category_disabled(
        self,
        reset_logger: None,
        mock_process: MagicMock,
        mock_state: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test state() doesn't log when STATES category disabled."""
        SdlLogger.configure(categories={"states": False})

        with caplog.at_level(logging.DEBUG):
            SdlLogger.state(mock_process, mock_state, mock_state)

        assert "SdlState" not in caplog.text


class TestSdlLoggerCreateMethod:
    """Test create() method for logging process creation."""

    def test_create_logs_when_enabled(
        self,
        reset_logger: None,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test create() logs when PROCESSES category is enabled."""
        with caplog.at_level(logging.DEBUG):
            SdlLogger.create(mock_process, "parent_pid_456")

        assert "Created" in caplog.text
        assert "create" in caplog.text
        assert "parent_pid_456" in caplog.text

    def test_create_logs_none_parent(
        self,
        reset_logger: None,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test create() handles None parent (root process)."""
        with caplog.at_level(logging.DEBUG):
            SdlLogger.create(mock_process, None)

        assert "Created" in caplog.text
        assert "None" in caplog.text

    def test_create_not_logged_when_category_disabled(
        self,
        reset_logger: None,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test create() doesn't log when PROCESSES category disabled."""
        SdlLogger.configure(categories={"processes": False})

        with caplog.at_level(logging.DEBUG):
            SdlLogger.create(mock_process, "parent_pid")

        assert "Created" not in caplog.text


class TestSdlLoggerEventMethod:
    """Test event() method for logging process events."""

    def test_event_logs_when_enabled(
        self,
        reset_logger: None,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test event() logs when PROCESSES category is enabled."""
        with caplog.at_level(logging.DEBUG):
            SdlLogger.event("Stopped", mock_process, "dst_pid", "src_pid")

        assert "Stopped" in caplog.text

    def test_event_not_logged_when_category_disabled(
        self,
        reset_logger: None,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test event() doesn't log when PROCESSES category disabled."""
        SdlLogger.configure(categories={"processes": False})

        with caplog.at_level(logging.DEBUG):
            SdlLogger.event("Stopped", mock_process, "dst", "src")

        assert "Stopped" not in caplog.text


class TestSdlLoggerAppMethod:
    """Test app() method for application-level logging."""

    def test_app_logs_when_enabled(
        self,
        reset_logger: None,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test app() logs when APPLICATION category is enabled."""
        with caplog.at_level(logging.DEBUG):
            SdlLogger.app(mock_process, "Application message")

        assert "SdlApp" in caplog.text
        assert "Application message" in caplog.text
        assert "TestProcess" in caplog.text

    def test_app_not_logged_when_category_disabled(
        self,
        reset_logger: None,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test app() doesn't log when APPLICATION category disabled."""
        SdlLogger.configure(categories={"application": False})

        with caplog.at_level(logging.DEBUG):
            SdlLogger.app(mock_process, "Should not appear")

        assert "Should not appear" not in caplog.text

    def test_app_not_logged_when_level_too_high(
        self,
        reset_logger: None,
        mock_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test app() respects log level."""
        SdlLogger.configure(level="ERROR")

        with caplog.at_level(logging.DEBUG):
            SdlLogger.app(mock_process, "Should not appear")

        assert "Should not appear" not in caplog.text


class TestSdlLoggerLazyEvaluation:
    """Test that logging uses lazy evaluation for performance."""

    def test_signal_not_called_when_disabled(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that expensive signal methods not called when disabled."""
        SdlLogger.configure(categories={"signals": False})

        # Create a mock that will raise if methods are called
        signal = MagicMock(spec=SdlSignal)
        signal.name.side_effect = Exception("Should not be called")

        process = MagicMock(spec=SdlProcess)

        # This should not raise because lazy evaluation prevents calls
        SdlLogger.signal("SdlSig", signal, process)

        # Verify the expensive methods were never called
        signal.name.assert_not_called()

    def test_app_not_formatted_when_disabled(
        self, reset_logger: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that app() doesn't format when disabled."""
        SdlLogger.configure(categories={"application": False})

        process = MagicMock(spec=SdlProcess)
        process.current_state.side_effect = Exception("Should not be called")

        # Should not raise due to lazy evaluation
        SdlLogger.app(process, "Test message")

        # Verify expensive formatting methods were never called
        process.current_state.assert_not_called()
