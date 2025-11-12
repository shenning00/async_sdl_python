# PySDL - Python Asynchronous SDL Library

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Pipeline Status](https://gitlab.com/your-repo/async_sdl_python/badges/main/pipeline.svg)](https://gitlab.com/your-repo/async_sdl_python/-/commits/main)
[![Coverage](https://gitlab.com/your-repo/async_sdl_python/badges/main/coverage.svg)](https://gitlab.com/your-repo/async_sdl_python/-/commits/main)

A lightweight, asynchronous Python library implementing the **Specification and Description Language (SDL)** actor model pattern for building concurrent, event-driven applications.

## Overview

PySDL provides a clean, type-safe framework for building applications based on the actor model and finite state machines. It leverages Python's asyncio for efficient concurrent execution while maintaining clean separation of concerns through message passing.

**Key Features:**

- **Actor Model Implementation**: Processes communicate exclusively through asynchronous signals
- **Finite State Machines**: Define complex behavior through clean state transitions
- **Star Wildcard Matching**: Handle signals from any state or any signal in a state
- **Type-Safe Design**: Comprehensive type hints for better IDE support and type checking
- **Async/Await Native**: Built on asyncio for high-performance concurrent execution
- **Timer Support**: Multiple concurrent timers per process with millisecond precision
- **Process Hierarchies**: Parent-child process relationships with lifecycle management
- **Singleton Processes**: Built-in support for singleton service patterns
- **Configurable Logging**: Fine-grained control over logging with minimal performance overhead

## Quick Start

### Installation

**Using pip** (when published to PyPI):
```bash
pip install pysdl
```

**From source**:
```bash
git clone https://gitlab.com/your-repo/async_sdl_python.git
cd async_sdl_python
# Upgrade pip first to avoid installation issues
python -m pip install --upgrade pip
# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

> **Note:** Upgrading pip is recommended to ensure editable installs work correctly with pyproject.toml-based projects.

**Using PYTHONPATH** (for development):
```bash
export PYTHONPATH=/path/to/async_sdl_python:$PYTHONPATH
```

### Hello World Example

Here's a simple ping-pong example demonstrating the core concepts:

```python
import asyncio
from pysdl import (
    SdlProcess, SdlSignal, SdlState, SdlSystem, SdlStartSignal,
    start
)


class PingSignal(SdlSignal):
    """A ping signal."""
    def dumpdata(self):
        return "Ping!"


class PingPongProcess(SdlProcess):
    """Process that responds to ping signals."""

    state_wait_ping = SdlState("wait_ping")

    def __init__(self, parent_pid, peer_pid=None, system=None):
        super().__init__(parent_pid, system=system)
        self.peer_pid = peer_pid

    async def start_StartTransition(self, _):
        """Initial state: send ping to peer if available."""
        if self.peer_pid:
            await self.output(PingSignal.create(), self.peer_pid)
        await self.next_state(self.state_wait_ping)

    async def wait_ping_PingSignal(self, signal):
        """Respond to ping by sending it back."""
        await self.output(signal, signal.src())

    def _init_state_machine(self):
        """Define the state machine."""
        self._event(start, SdlStartSignal, self.start_StartTransition)
        self._event(self.state_wait_ping, PingSignal, self.wait_ping_PingSignal)
        self._done()


async def main():
    """Create processes and run the system."""
    # Create a system instance
    system = SdlSystem()

    # Create processes with the system instance
    p1 = await PingPongProcess.create(None, system=system)
    p2 = await PingPongProcess.create(None, p1.pid(), system=system)

    # Run the system
    await system.run()


if __name__ == "__main__":
    asyncio.run(main())
```

## Core Concepts

### Processes (Actors)

Processes are independent actors that:
- Maintain their own internal state
- Communicate only through signals (messages)
- Execute state transitions in response to signals
- Can create child processes
- Can start and stop timers

### Signals (Messages)

Signals are typed messages that:
- Are routed between processes by PID
- Carry optional data payloads
- Trigger state transitions when received
- Are queued and processed asynchronously

### States & State Machines

State machines define process behavior:
- Each process has exactly one current state
- States define which signals trigger which handlers
- Handlers can send signals and transition to new states
- State transitions are logged automatically

### Timers

Timers enable time-based behavior:
- Multiple concurrent timers per process
- Millisecond precision
- Automatic delivery as signals when expired
- Can be started, stopped, and restarted

## Documentation

- **[Architecture Guide](docs/architecture.md)**: Deep dive into design decisions and patterns
- **[API Reference](docs/api_reference.md)**: Complete API documentation with examples
- **[Getting Started Tutorial](docs/getting_started.md)**: Step-by-step guide for beginners
- **[Examples](docs/examples.md)**: Comprehensive examples demonstrating features
- **[Logging Configuration](docs/logging_configuration.md)**: Configure logging levels and categories
- **[Troubleshooting](docs/troubleshooting.md)**: Common issues and solutions

## Project Structure

```
async_sdl_python/
├── pysdl/                  # Core library package
│   ├── __init__.py         # Public API exports
│   ├── system.py           # Event loop and system management
│   ├── process.py          # Process base classes
│   ├── signal.py           # Signal base class
│   ├── state.py            # State representation
│   ├── state_machine.py    # FSM implementation
│   ├── timer.py            # Timer implementation
│   ├── logger.py           # Event logging
│   ├── children_manager.py # Child process management
│   ├── id_generator.py     # Unique ID generation
│   ├── registry.py         # Name-based process registry
│   └── system_signals.py   # Built-in system signals
├── tests/                  # Test suite
├── docs/                   # Documentation
├── examples/               # Example applications
│   └── main.py             # Ping-pong example
└── README.md               # This file
```

## Requirements

- **Python**: 3.9 or higher (uses type hints and async features)
- **Dependencies**: None (uses only Python standard library)
- **Development Dependencies**:
  - pytest >= 8.0
  - pytest-asyncio >= 0.23
  - pytest-cov >= 4.1
  - mypy >= 1.13 (for type checking)
  - ruff >= 0.8 (for linting)

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pysdl --cov-report=html

# Run type checking
mypy pysdl/

# Run linting
ruff check pysdl/
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass and coverage remains high
5. Run type checking and linting
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Merge Request

### Development Guidelines

- **Type Safety**: All code must have comprehensive type hints
- **Testing**: Maintain >90% test coverage
- **Documentation**: Update docs for API changes
- **Code Style**: Follow PEP 8, use ruff formatter
- **Async**: Use async/await properly, avoid blocking calls
- **Logging**: Use SdlLogger for framework events

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Authors

- Scott Henning - Initial work

## Acknowledgments

- Inspired by the ITU-T Z.100 Specification and Description Language (SDL)
- Built on Python's powerful asyncio framework
- Designed for clarity, type safety, and performance

## Support

- **Issues**: Report bugs via GitLab Issues
- **Documentation**: See the [docs/](docs/) directory
- **Examples**: See [examples/main.py](examples/main.py) and [docs/examples.md](docs/examples.md)

## Breaking Changes in v1.0.0

PySDL v1.0.0 introduces breaking changes to support instance-based systems. This enables running multiple independent SDL systems in the same process and eliminates global state.

Key changes:
- `SdlSystem` is now instance-based - create instances with `system = SdlSystem()`
- `SdlProcess.create()` and `__init__()` now require `system` parameter
- All `SdlSystem.method()` static calls are now `system.method()` instance calls
- Processes access their system via `self._system` attribute

## Roadmap

Future enhancements under consideration:

- [x] Instance-based system design (multiple independent systems) - **Completed in v1.0.0**
- [ ] Enhanced debugging and introspection tools
- [ ] State machine visualization
- [ ] Performance benchmarking suite
- [ ] Additional example applications
- [ ] Integration with popular async frameworks

## Version History

- **1.0.0** (2024-10-26) - Instance-based system **[BREAKING CHANGES]**
  - Refactored `SdlSystem` from static class to instance-based
  - Added `system` parameter to `SdlProcess` creation and initialization
  - Processes now reference their system instance via `self._system`
  - Enables multiple independent systems in the same process
  - Eliminates global state for better testability
  - All tests updated (242 tests, 83% coverage)
  - All examples updated to use instance-based API

- **0.0.1** - Initial release
  - Core actor model implementation
  - Async signal routing
  - Finite state machines
  - Timer support
  - Process hierarchies
  - Type-safe API
