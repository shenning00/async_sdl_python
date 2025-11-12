"""
Async SDL Python - A Python implementation of the SDL (Specification and Description Language) framework.

This package provides an asynchronous framework for building concurrent systems using
the actor model with processes, signals, and state machines.
"""

from __future__ import annotations

# Core components
from .children_manager import SdlChildrenManager

# Exceptions
from .exceptions import (
    InvalidStateError,
    ProcessNotFoundError,
    QueueError,
    SdlError,
    SignalDeliveryError,
    StateTransitionError,
    TimerError,
    ValidationError,
)
from .id_generator import SdlIdGenerator
from .logger import SdlLogger
from .process import SdlProcess, SdlSingletonProcess
from .registry import SdlRegistry
from .signal import SdlSignal
from .state import SdlState, start
from .state_machine import SdlStateMachine
from .system import SdlSystem

# System signals
from .system_signals import (
    SdlProcessNotExistSignal,
    SdlStarSignal,
    SdlStartSignal,
    SdlStoppingSignal,
    SdlStopSignal,
)
from .timer import SdlTimer

__all__ = [
    # Core components
    "SdlChildrenManager",
    "SdlIdGenerator",
    "SdlLogger",
    "SdlProcess",
    "SdlRegistry",
    "SdlSignal",
    "SdlSingletonProcess",
    "SdlState",
    "SdlStateMachine",
    "SdlSystem",
    "SdlTimer",
    # State constants
    "start",
    # System signals
    "SdlProcessNotExistSignal",
    "SdlStarSignal",
    "SdlStartSignal",
    "SdlStopSignal",
    "SdlStoppingSignal",
    # Exceptions
    "InvalidStateError",
    "ProcessNotFoundError",
    "QueueError",
    "SdlError",
    "SignalDeliveryError",
    "StateTransitionError",
    "TimerError",
    "ValidationError",
]
