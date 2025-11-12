"""Test suite for SdlRegistry.

This module tests the singleton registry functionality used for storing global configuration.
"""

import pytest

from pysdl import SdlRegistry


class TestSdlRegistry:
    """Test cases for SdlRegistry class."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset the registry state before each test.

        This ensures tests are isolated by clearing the singleton instance.
        """
        # Clear the registry dictionary
        SdlRegistry._registry = {}
        # Reset the singleton instance to allow fresh creation
        SdlRegistry._instance = None

    def test_registry_is_singleton(self) -> None:
        """Test that SdlRegistry implements singleton pattern."""
        registry1 = SdlRegistry()
        registry2 = SdlRegistry()
        assert registry1 is registry2
        assert id(registry1) == id(registry2)

    def test_init_registry_not_none(self) -> None:
        """Test that creating a registry returns a valid instance."""
        registry = SdlRegistry()
        assert registry is not None
        assert isinstance(registry, SdlRegistry)

    def test_add_and_get_string_value(self) -> None:
        """Test adding and retrieving a string value."""
        registry = SdlRegistry()
        registry.add("test_key", "test_value")
        value = registry.get("test_key")
        assert value == "test_value"

    def test_add_and_get_int_value(self) -> None:
        """Test adding and retrieving an integer value."""
        registry = SdlRegistry()
        registry.add("count", 42)
        value = registry.get("count")
        assert value == 42

    def test_add_and_get_dict_value(self) -> None:
        """Test adding and retrieving a dictionary value."""
        registry = SdlRegistry()
        test_dict = {"name": "test", "value": 123}
        registry.add("config", test_dict)
        value = registry.get("config")
        assert value == test_dict
        assert value["name"] == "test"

    def test_add_and_get_list_value(self) -> None:
        """Test adding and retrieving a list value."""
        registry = SdlRegistry()
        test_list = [1, 2, 3, 4, 5]
        registry.add("numbers", test_list)
        value = registry.get("numbers")
        assert value == test_list

    def test_overwrite_existing_key(self) -> None:
        """Test that adding a key twice overwrites the previous value."""
        registry = SdlRegistry()
        registry.add("key", "value1")
        registry.add("key", "value2")
        value = registry.get("key")
        assert value == "value2"

    def test_multiple_keys(self) -> None:
        """Test storing multiple key-value pairs."""
        registry = SdlRegistry()
        registry.add("key1", "value1")
        registry.add("key2", "value2")
        registry.add("key3", "value3")
        assert registry.get("key1") == "value1"
        assert registry.get("key2") == "value2"
        assert registry.get("key3") == "value3"

    def test_get_nonexistent_key_raises_keyerror(self) -> None:
        """Test that getting a non-existent key raises KeyError."""
        registry = SdlRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_singleton_preserves_data(self) -> None:
        """Test that data is preserved across singleton instances."""
        registry1 = SdlRegistry()
        registry1.add("shared_key", "shared_value")

        registry2 = SdlRegistry()
        value = registry2.get("shared_key")
        assert value == "shared_value"
