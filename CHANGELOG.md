# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Optimized CI cache configuration
- Removed temporary test scripts and improved .gitignore

## [1.0.0] - 2025-10-26

### Breaking Changes
- Refactored `SdlSystem` from static class to instance-based design
- All `SdlProcess.create()` and `__init__()` now require `system` parameter
- Processes must reference their system via `self._system` attribute instead of static methods
- All `SdlSystem.method()` static calls are now `system.method()` instance calls

### Added
- Instance-based SdlSystem design enabling multiple independent systems in the same process
- Star signal wildcard matching with 4-level priority system for flexible event handling
- System parameter requirement for proper isolation between SDL systems
- Comprehensive test suite with 242 tests achieving 84% code coverage
- Environment variable debugging capabilities in CI pipeline
- Enhanced logging format with improved trace capabilities

### Changed
- Eliminated global state in SdlSystem for better testability and isolation
- Updated all examples to use instance-based API
- `SdlRegistry.get()` now raises `KeyError` for missing keys when no default is provided
- Improved error handling and validation throughout the codebase

### Fixed
- Black formatting compliance in state_machine.py
- Claude Code CI job authentication and MCP server issues
- Registry behavior to be more Pythonic with proper exception handling

### Documentation
- Added log trace format enhancement design document
- Updated all documentation to reflect instance-based API
- Improved troubleshooting guide with common migration issues

### Migration
See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed upgrade instructions from v0.0.1 to v1.0.0.

## [0.0.1] - Initial Release

### Added
- Core actor model implementation based on SDL (Specification and Description Language)
- Asynchronous signal routing with asyncio for efficient concurrent execution
- Finite state machine framework with clean state transition definitions
- Timer support with millisecond precision and multiple concurrent timers per process
- Process hierarchies with parent-child relationships and lifecycle management
- Singleton process support for service patterns
- Type-safe API with comprehensive type hints for Python 3.9+
- Configurable logging system with fine-grained control and minimal performance overhead
- Complete documentation suite including:
  - Architecture guide with design patterns and decisions
  - API reference with comprehensive examples
  - Getting started tutorial for beginners
  - Examples demonstrating all major features
  - Logging configuration guide
  - Troubleshooting guide
- Zero external dependencies (Python standard library only)
- Initial test coverage with pytest and pytest-asyncio

### Features
- Processes communicate exclusively through asynchronous signals
- State machines define complex behavior through clean transitions
- Parent-child process relationships with automatic lifecycle management
- Name-based process registry for singleton patterns
- Unique PID generation for process identification
- Event logging for debugging and monitoring
- Async/await native implementation leveraging Python's asyncio

---

## Release Notes

### Version 1.0.0 Highlights

This major release represents a significant architectural improvement, transitioning from a static class-based system to an instance-based design. This change:

- Enables running multiple independent SDL systems in the same Python process
- Eliminates global state, making the framework more testable and maintainable
- Provides better isolation between different system instances
- Follows modern Python best practices for library design

The migration from v0.0.1 requires updating code to create `SdlSystem` instances and pass them to processes. While this is a breaking change, it provides a cleaner, more flexible architecture that supports advanced use cases like running multiple systems concurrently or testing with isolated system instances.

### Version 0.0.1 Highlights

The initial release established the core framework with:

- A clean, type-safe implementation of the SDL actor model
- Comprehensive async/await support for concurrent execution
- Zero external dependencies for easy adoption
- Complete documentation and examples
- Strong foundation for building event-driven applications

---

[Unreleased]: https://github.com/shenning00/async_sdl_python/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/shenning00/async_sdl_python/compare/v0.0.1...v1.0.0
[0.0.1]: https://github.com/shenning00/async_sdl_python/releases/tag/v0.0.1
