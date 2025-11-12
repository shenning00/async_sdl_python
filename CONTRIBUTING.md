# Contributing to PySDL

Thank you for considering contributing to PySDL! This document provides guidelines and best practices for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Development Guidelines](#development-guidelines)
- [Testing Requirements](#testing-requirements)
- [Code Style](#code-style)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Review Process](#review-process)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful, constructive, and professional in all interactions.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Familiarity with async/await programming in Python
- Understanding of actor model concepts (helpful but not required)

### Setting Up Your Development Environment

1. Fork the repository on GitHub

2. Clone your fork:
```bash
git clone https://github.com/YOUR_USERNAME/async_sdl_python.git
cd async_sdl_python
```

3. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install development dependencies:
```bash
pip install -e ".[dev]"
```

5. Verify your setup by running the tests:
```bash
pytest
```

## Development Workflow

### 1. Create a Feature Branch

Create a descriptive branch name:

```bash
git checkout -b feature/amazing-feature
# or
git checkout -b fix/bug-description
# or
git checkout -b docs/documentation-improvement
```

Branch naming conventions:
- `feature/` - New features or enhancements
- `fix/` - Bug fixes
- `docs/` - Documentation improvements
- `refactor/` - Code refactoring without behavior changes
- `test/` - Test improvements or additions
- `chore/` - Maintenance tasks, dependency updates, etc.

### 2. Make Your Changes

- Write clear, maintainable code following our guidelines
- Add tests for new functionality
- Update documentation as needed
- Commit frequently with descriptive messages

### 3. Test Your Changes

Run the full test suite:

```bash
# Run all tests
pytest

# Run with coverage reporting
pytest --cov=pysdl --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_specific.py

# Run tests matching a pattern
pytest -k "test_pattern"
```

### 4. Verify Code Quality

Before submitting, ensure your code passes all quality checks:

```bash
# Type checking
mypy pysdl/

# Code formatting (auto-formats code)
black pysdl/ tests/

# Linting
pylint pysdl/
```

### 5. Push and Create Merge Request

```bash
git push origin feature/amazing-feature
```

Then create a Pull Request on GitHub with a clear description of your changes.

## Development Guidelines

### Type Safety

All code must include comprehensive type hints:

```python
from typing import Optional, List, Dict, Any

async def process_signal(
    signal: SdlSignal,
    targets: List[int],
    timeout: Optional[float] = None
) -> Dict[str, Any]:
    """Process a signal and return results.

    Args:
        signal: The signal to process.
        targets: List of target process PIDs.
        timeout: Optional timeout in seconds.

    Returns:
        Dictionary containing processing results.

    Raises:
        ValueError: If targets list is empty.
        TimeoutError: If processing exceeds timeout.
    """
    if not targets:
        raise ValueError("Targets list cannot be empty")
    # Implementation...
```

Key type safety requirements:
- All function signatures must have type hints for parameters and return values
- Use `Optional[T]` or `T | None` for nullable types
- Use proper generic types: `List[T]`, `Dict[K, V]`, etc.
- Define custom types for complex structures using `TypedDict` or dataclasses
- Code must pass `mypy --strict` without errors

### Async Programming

PySDL is built on asyncio. Follow these async best practices:

```python
# GOOD: Proper async/await usage
async def fetch_data(self) -> Data:
    """Fetch data asynchronously."""
    result = await self._async_operation()
    return result

# BAD: Blocking call in async context
async def fetch_data(self) -> Data:
    """Don't do this!"""
    result = time.sleep(1)  # Blocks the event loop!
    return result

# GOOD: Use asyncio primitives
async def wait_for_signal(self, timeout: float) -> Optional[SdlSignal]:
    """Wait for signal with timeout."""
    try:
        return await asyncio.wait_for(self._signal_queue.get(), timeout)
    except asyncio.TimeoutError:
        return None
```

Best practices:
- Never use blocking I/O in async functions (no `time.sleep`, use `asyncio.sleep`)
- Use `async with` for async context managers
- Properly handle exceptions in async contexts
- Use `asyncio.gather()` or `asyncio.TaskGroup()` for concurrent operations
- Avoid mixing sync and async code without proper bridging

### Logging

Use the SdlLogger for framework events:

```python
from pysdl.logger import SdlLogger, SdlLogLevel, SdlLogCategory

# Log state transitions
SdlLogger.log(
    SdlLogLevel.INFO,
    SdlLogCategory.STATE,
    f"Process {self.pid()} transitioned to {new_state.name()}"
)

# Log signal routing
SdlLogger.log(
    SdlLogLevel.DEBUG,
    SdlLogCategory.SIGNAL,
    f"Routing signal {signal.__class__.__name__} from {src} to {dst}"
)
```

Guidelines:
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Use appropriate categories (STATE, SIGNAL, TIMER, PROCESS, SYSTEM)
- Keep log messages concise and informative
- Include relevant context (PIDs, signal types, state names)
- Avoid logging in hot paths unless necessary

### Error Handling

Provide clear, actionable error messages:

```python
class SdlSignalRoutingError(Exception):
    """Raised when signal routing fails."""
    pass

class SdlInvalidStateError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass

async def route_signal(self, signal: SdlSignal, dst: int) -> None:
    """Route a signal to a destination process.

    Raises:
        SdlSignalRoutingError: If destination process not found.
        ValueError: If signal or dst is invalid.
    """
    if not isinstance(signal, SdlSignal):
        raise ValueError(f"Expected SdlSignal, got {type(signal)}")

    if dst not in self._processes:
        raise SdlSignalRoutingError(
            f"Cannot route signal: process {dst} not found"
        )

    await self._deliver_signal(signal, dst)
```

Best practices:
- Define custom exception classes for domain-specific errors
- Inherit from appropriate base exceptions
- Provide descriptive error messages with context
- Document exceptions in docstrings
- Validate inputs and fail fast with clear errors

## Testing Requirements

### Coverage Standards

- Maintain >90% test coverage for new code
- All public APIs must have tests
- Test both success and failure cases
- Include edge cases and boundary conditions

### Test Structure

Organize tests clearly:

```python
import pytest
from pysdl import SdlProcess, SdlSystem, SdlSignal


class TestSdlProcess:
    """Test suite for SdlProcess."""

    @pytest.fixture
    async def system(self):
        """Create a test system instance."""
        return SdlSystem()

    @pytest.fixture
    async def process(self, system):
        """Create a test process."""
        return await TestProcess.create(None, system=system)

    @pytest.mark.asyncio
    async def test_process_creation(self, system):
        """Test that processes are created correctly."""
        process = await TestProcess.create(None, system=system)
        assert process.pid() > 0
        assert process._system is system

    @pytest.mark.asyncio
    async def test_signal_handling(self, process):
        """Test that signals are handled correctly."""
        signal = TestSignal.create()
        await process.input_signal(signal)
        # Verify expected behavior

    @pytest.mark.asyncio
    async def test_invalid_state_transition(self, process):
        """Test that invalid transitions raise errors."""
        with pytest.raises(SdlInvalidStateError):
            await process.next_state(InvalidState())
```

### Test Guidelines

- Use descriptive test names that explain what is being tested
- One assertion focus per test (can have multiple related assertions)
- Use fixtures for common setup
- Test async code with `@pytest.mark.asyncio`
- Mock external dependencies appropriately
- Test error conditions and exceptions
- Include integration tests for complex interactions

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_process.py

# Run specific test
pytest tests/test_process.py::TestSdlProcess::test_process_creation

# Run with coverage
pytest --cov=pysdl --cov-report=html --cov-report=term-missing

# Run only failed tests from last run
pytest --lf

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

## Code Style

### Formatting

We use [Black](https://black.readthedocs.io/) for consistent code formatting:

```bash
# Format all code
black pysdl/ tests/

# Check without modifying
black --check pysdl/ tests/
```

Configuration:
- Line length: 88 characters (Black default)
- Python version: 3.9+

### PEP 8 Compliance

Follow [PEP 8](https://pep8.org/) style guide:

- Use 4 spaces for indentation
- Maximum line length: 88 characters (Black enforced)
- Use descriptive variable and function names
- Follow naming conventions:
  - `snake_case` for functions, methods, variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Docstring Format

Use Google-style docstrings:

```python
async def process_signal(
    self,
    signal: SdlSignal,
    timeout: Optional[float] = None
) -> ProcessResult:
    """Process an incoming signal with optional timeout.

    This method handles signal processing including validation,
    state machine dispatch, and result collection.

    Args:
        signal: The signal to process. Must be a valid SdlSignal instance.
        timeout: Optional timeout in seconds. If None, waits indefinitely.
            Must be positive if provided.

    Returns:
        ProcessResult containing the processing outcome and any generated
        signals or state changes.

    Raises:
        ValueError: If signal is invalid or timeout is negative.
        TimeoutError: If processing exceeds the specified timeout.
        SdlStateError: If process is not in a valid state for this signal.

    Example:
        >>> signal = MySignal.create()
        >>> result = await process.process_signal(signal, timeout=5.0)
        >>> print(result.success)
        True

    Note:
        The timeout applies to the entire processing operation, including
        any async operations triggered by signal handlers.
    """
    pass
```

Requirements:
- All public modules, classes, and functions must have docstrings
- Include description, Args, Returns, Raises, Examples where applicable
- Keep descriptions clear and concise
- Document type information that isn't obvious from type hints

## Documentation

### Update Documentation

When making changes, update relevant documentation:

- **README.md**: For user-facing features or API changes
- **docs/api_reference.md**: For API additions or modifications
- **docs/architecture.md**: For design or architectural changes
- **docs/examples.md**: Add examples demonstrating new features
- **docs/getting_started.md**: For changes affecting the tutorial
- **docs/troubleshooting.md**: For common issues or solutions
- **CHANGELOG.md**: Document all changes following Keep a Changelog format
- **MIGRATION_GUIDE.md**: For breaking changes requiring migration steps

### Writing Good Documentation

- Use clear, simple language
- Include code examples that actually work
- Explain the "why" not just the "what"
- Keep examples focused and minimal
- Test code examples to ensure they work

## Submitting Changes

### Commit Messages

Write clear, descriptive commit messages:

```
feat: Add star signal wildcard matching support

- Implement 4-level priority matching system
- Add tests for wildcard signal handlers
- Update documentation with examples
- Resolves #123
```

Format:
- Use present tense ("Add feature" not "Added feature")
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description if needed
- Reference issues/MRs with `#123` or `Resolves #123`

Commit types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Formatting, missing semicolons, etc.
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

### Pull Request Guidelines

When creating a pull request:

1. **Title**: Clear, descriptive summary of changes
2. **Description**: Include:
   - What changed and why
   - Any breaking changes
   - Testing performed
   - Screenshots if UI-related
   - Related issues
3. **Checklist**:
   - [ ] Tests added and passing
   - [ ] Documentation updated
   - [ ] Type checking passes (`mypy`)
   - [ ] Code formatted with Black
   - [ ] Linting passes
   - [ ] CHANGELOG.md updated
   - [ ] No breaking changes (or documented in MIGRATION_GUIDE.md)

### Review Process

After submitting a pull request:

1. Automated tests will run via CI/CD
2. Maintainers will review your code
3. Address any feedback or requested changes
4. Once approved, a maintainer will merge your changes

Tips for faster reviews:
- Keep changes focused and reasonably sized
- Respond promptly to feedback
- Ensure all CI checks pass
- Write clear descriptions and comments

## Questions?

If you have questions or need help:

- Check existing documentation in the `docs/` directory
- Review closed issues and pull requests for similar questions
- Open a new issue for discussion
- Reach out to maintainers via GitHub

Thank you for contributing to PySDL!
