"""Test suite for SdlChildrenManager.

This module tests child process tracking, filtering, and parent-child relationships.
"""

from unittest.mock import Mock

import pytest

from pysdl.children_manager import SdlChildrenManager


class TestSdlChildrenManager:
    """Test cases for SdlChildrenManager class."""

    @pytest.fixture
    def manager(self) -> SdlChildrenManager:
        """Create a fresh children manager for each test."""
        return SdlChildrenManager()

    @pytest.fixture
    def mock_process(self) -> Mock:
        """Create a mock process for testing."""
        process = Mock()
        process.pid.return_value = "TestProcess(0.0)"
        return process

    def test_manager_creation(self, manager: SdlChildrenManager) -> None:
        """Test basic manager creation."""
        assert manager is not None
        assert isinstance(manager, SdlChildrenManager)

    def test_manager_initial_empty(self, manager: SdlChildrenManager) -> None:
        """Test that manager starts with no children."""
        assert manager.get_count() == 0
        assert manager.get_child_list() == []

    def test_register_child(
        self, manager: SdlChildrenManager, mock_process: Mock
    ) -> None:
        """Test registering a child process."""
        result = manager.register(mock_process)
        assert result is mock_process
        assert manager.get_count() == 1

    def test_register_child_with_keys(
        self, manager: SdlChildrenManager, mock_process: Mock
    ) -> None:
        """Test registering a child with metadata keys."""
        manager.register(mock_process, role="worker", priority=1)
        children = manager.get_child_list()
        assert len(children) == 1
        assert children[0]["keys"]["role"] == "worker"
        assert children[0]["keys"]["priority"] == 1

    def test_register_multiple_children(self, manager: SdlChildrenManager) -> None:
        """Test registering multiple children."""
        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"
        process3 = Mock()
        process3.pid.return_value = "Process3(0.0)"

        manager.register(process1)
        manager.register(process2)
        manager.register(process3)

        assert manager.get_count() == 3

    def test_get_child_list(
        self, manager: SdlChildrenManager, mock_process: Mock
    ) -> None:
        """Test getting list of all children."""
        manager.register(mock_process, role="test")
        children = manager.get_child_list()

        assert len(children) == 1
        assert children[0]["pid"] == "TestProcess(0.0)"
        assert children[0]["process"] is mock_process
        assert children[0]["keys"]["role"] == "test"

    def test_get_by_pid(self, manager: SdlChildrenManager, mock_process: Mock) -> None:
        """Test getting child by PID."""
        manager.register(mock_process)
        child = manager.get_by_pid("TestProcess(0.0)")

        assert child is not None
        assert child["pid"] == "TestProcess(0.0)"
        assert child["process"] is mock_process

    def test_get_by_pid_not_found(self, manager: SdlChildrenManager) -> None:
        """Test getting child by non-existent PID."""
        child = manager.get_by_pid("NonExistent(0.0)")
        assert child is None

    def test_set_keys_by_pid(
        self, manager: SdlChildrenManager, mock_process: Mock
    ) -> None:
        """Test setting keys for a child by PID."""
        manager.register(mock_process, role="worker")
        result = manager.set_keys_by_pid(
            "TestProcess(0.0)", priority=5, status="active"
        )

        assert result is True
        child = manager.get_by_pid("TestProcess(0.0)")
        assert child is not None
        assert child["keys"]["role"] == "worker"  # Original key preserved
        assert child["keys"]["priority"] == 5  # New key added
        assert child["keys"]["status"] == "active"  # New key added

    def test_set_keys_by_pid_not_found(self, manager: SdlChildrenManager) -> None:
        """Test setting keys for non-existent PID."""
        result = manager.set_keys_by_pid("NonExistent(0.0)", key="value")
        assert result is False

    def test_get_keys_by_pid(
        self, manager: SdlChildrenManager, mock_process: Mock
    ) -> None:
        """Test getting keys for a child by PID."""
        manager.register(mock_process, role="worker", priority=1)
        keys = manager.get_keys_by_pid("TestProcess(0.0)")

        assert keys is not None
        assert keys["role"] == "worker"
        assert keys["priority"] == 1

    def test_get_keys_by_pid_not_found(self, manager: SdlChildrenManager) -> None:
        """Test getting keys for non-existent PID."""
        keys = manager.get_keys_by_pid("NonExistent(0.0)")
        assert keys is None

    def test_add_to_front(self, manager: SdlChildrenManager) -> None:
        """Test adding child to front of list."""
        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"

        manager.register(process1)
        manager.add_to_front(process2)

        children = manager.get_child_list()
        assert len(children) == 2
        assert children[0]["pid"] == "Process2(0.0)"  # Added to front
        assert children[1]["pid"] == "Process1(0.0)"

    def test_get_first_child_with_keys(self, manager: SdlChildrenManager) -> None:
        """Test getting first child matching keys."""
        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"
        process3 = Mock()
        process3.pid.return_value = "Process3(0.0)"

        manager.register(process1, role="worker", priority=1)
        manager.register(process2, role="worker", priority=2)
        manager.register(process3, role="manager", priority=1)

        child = manager.get_first_child_with_keys(role="worker")
        assert child is not None
        assert child["pid"] == "Process1(0.0)"

    def test_get_first_child_with_keys_multiple_criteria(
        self, manager: SdlChildrenManager
    ) -> None:
        """Test getting first child matching multiple keys."""
        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"

        manager.register(process1, role="worker", priority=1)
        manager.register(process2, role="worker", priority=2)

        child = manager.get_first_child_with_keys(role="worker", priority=2)
        assert child is not None
        assert child["pid"] == "Process2(0.0)"

    def test_get_first_child_with_keys_not_found(
        self, manager: SdlChildrenManager, mock_process: Mock
    ) -> None:
        """Test getting first child when no match found."""
        manager.register(mock_process, role="worker")
        child = manager.get_first_child_with_keys(role="manager")
        assert child is None

    def test_get_first_child_with_keys_missing_key(
        self, manager: SdlChildrenManager
    ) -> None:
        """Test getting first child when child is missing a required key."""
        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"

        # Register children with different key sets
        manager.register(process1, role="worker")  # Missing 'priority' key
        manager.register(process2, role="worker", priority=1)  # Has both keys

        # Search for both role and priority - only process2 should match
        child = manager.get_first_child_with_keys(role="worker", priority=1)
        assert child is not None
        assert child["pid"] == "Process2(0.0)"

    def test_get_child_list_with_keys(self, manager: SdlChildrenManager) -> None:
        """Test getting all children matching keys."""
        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"
        process3 = Mock()
        process3.pid.return_value = "Process3(0.0)"

        manager.register(process1, role="worker", priority=1)
        manager.register(process2, role="worker", priority=2)
        manager.register(process3, role="manager", priority=1)

        children = manager.get_child_list_with_keys(role="worker")
        assert len(children) == 2
        assert children[0]["pid"] == "Process1(0.0)"
        assert children[1]["pid"] == "Process2(0.0)"

    def test_get_child_list_with_keys_multiple_criteria(
        self, manager: SdlChildrenManager
    ) -> None:
        """Test getting children matching multiple keys."""
        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"
        process3 = Mock()
        process3.pid.return_value = "Process3(0.0)"

        manager.register(process1, role="worker", priority=1, status="active")
        manager.register(process2, role="worker", priority=1, status="idle")
        manager.register(process3, role="worker", priority=2, status="active")

        children = manager.get_child_list_with_keys(role="worker", priority=1)
        assert len(children) == 2

    def test_get_child_list_with_keys_empty(
        self, manager: SdlChildrenManager, mock_process: Mock
    ) -> None:
        """Test getting children when no match found."""
        manager.register(mock_process, role="worker")
        children = manager.get_child_list_with_keys(role="manager")
        assert len(children) == 0

    def test_get_child_list_with_keys_missing_key(
        self, manager: SdlChildrenManager
    ) -> None:
        """Test getting children when some are missing required keys."""
        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"
        process3 = Mock()
        process3.pid.return_value = "Process3(0.0)"

        # Register children with different key sets
        manager.register(process1, role="worker")  # Missing 'priority' key
        manager.register(process2, role="worker", priority=1)  # Has both keys
        manager.register(process3, role="worker", priority=2)  # Has both keys

        # Search for both role and priority - only process2 and process3 should match
        children = manager.get_child_list_with_keys(role="worker", priority=1)
        assert len(children) == 1
        assert children[0]["pid"] == "Process2(0.0)"

    def test_unregister_by_keys(self, manager: SdlChildrenManager) -> None:
        """Test unregistering child by keys."""
        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"

        manager.register(process1, role="worker", id=1)
        manager.register(process2, role="worker", id=2)

        assert manager.get_count() == 2

        manager.unregister_by_keys(role="worker", id=1)

        assert manager.get_count() == 1
        remaining = manager.get_child_list()
        assert remaining[0]["pid"] == "Process2(0.0)"

    def test_unregister_by_keys_not_found(
        self, manager: SdlChildrenManager, mock_process: Mock
    ) -> None:
        """Test unregistering with keys that don't match."""
        manager.register(mock_process, role="worker")
        initial_count = manager.get_count()

        manager.unregister_by_keys(role="manager")  # No match

        assert manager.get_count() == initial_count

    def test_manager_iteration(self, manager: SdlChildrenManager) -> None:
        """Test iterating over children."""
        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"

        manager.register(process1)
        manager.register(process2)

        pids = [child["pid"] for child in manager]
        assert len(pids) == 2
        assert "Process1(0.0)" in pids
        assert "Process2(0.0)" in pids

    def test_check_keys_match_all_match(self, manager: SdlChildrenManager) -> None:
        """Test _check_keys_match with all matching keys."""
        child = {
            "pid": "Test(0.0)",
            "process": Mock(),
            "keys": {"role": "worker", "priority": 1, "status": "active"},
        }

        assert (
            manager._check_keys_match(child, {"role": "worker", "priority": 1}) is True
        )

    def test_check_keys_match_partial_mismatch(
        self, manager: SdlChildrenManager
    ) -> None:
        """Test _check_keys_match with some mismatched keys."""
        child = {
            "pid": "Test(0.0)",
            "process": Mock(),
            "keys": {"role": "worker", "priority": 1},
        }

        assert (
            manager._check_keys_match(child, {"role": "worker", "priority": 2}) is False
        )

    def test_check_keys_match_missing_key(self, manager: SdlChildrenManager) -> None:
        """Test _check_keys_match with missing key."""
        child = {
            "pid": "Test(0.0)",
            "process": Mock(),
            "keys": {"role": "worker"},
        }

        assert (
            manager._check_keys_match(child, {"role": "worker", "status": "active"})
            is False
        )

    def test_empty_keys_registration(
        self, manager: SdlChildrenManager, mock_process: Mock
    ) -> None:
        """Test registering child with no keys."""
        manager.register(mock_process)
        children = manager.get_child_list()

        assert len(children) == 1
        assert children[0]["keys"] == {}

    def test_get_count_updates(self, manager: SdlChildrenManager) -> None:
        """Test that get_count updates correctly."""
        assert manager.get_count() == 0

        process1 = Mock()
        process1.pid.return_value = "Process1(0.0)"
        manager.register(process1, id=1)
        assert manager.get_count() == 1

        process2 = Mock()
        process2.pid.return_value = "Process2(0.0)"
        manager.register(process2, id=2)
        assert manager.get_count() == 2

        manager.unregister_by_keys(id=1)
        assert manager.get_count() == 1
