# PySDL API Reference

Complete API documentation for PySDL with examples and usage patterns.

## Table of Contents

1. [Core Classes](#core-classes)
2. [SdlSystem](#sdlsystem)
3. [SdlProcess](#sdlprocess)
4. [SdlSingletonProcess](#sdlsingletonprocess)
5. [SdlSignal](#sdlsignal)
6. [SdlTimer](#sdltimer)
7. [SdlState](#sdlstate)
8. [SdlStateMachine](#sdlstatemachine)
9. [System Signals](#system-signals)
10. [SdlLogger](#sdllogger)
11. [SdlChildrenManager](#sdlchildrenmanager)
12. [Utilities](#utilities)

---

## Core Classes

The PySDL framework consists of these primary classes:

| Class | Purpose |
|-------|---------|
| `SdlSystem` | Central event loop and process registry |
| `SdlProcess` | Base class for all processes (actors) |
| `SdlSingletonProcess` | Base class for singleton processes |
| `SdlSignal` | Base class for all signals (messages) |
| `SdlTimer` | Timer signal for time-based events |
| `SdlState` | State representation for FSMs |
| `SdlStateMachine` | Finite state machine implementation |
| `SdlLogger` | Event and debug logging |
| `SdlChildrenManager` | Child process tracking and filtering |

---

## SdlSystem

The central system class managing the event loop, process registry, and signal routing.

**Instance-based design (v1.0.0+)**: SdlSystem is now instance-based, allowing multiple independent SDL systems in the same process.

### Instance Variables

```python
class SdlSystem:
    proc_map: Dict[str, SdlProcess]       # Process registry
    timer_map: Dict[str, List[SdlTimer]]  # Active timers
    ready_list: List[SdlProcess]          # Processes with pending signals
    _queue: asyncio.Queue[SdlSignal] | None  # Lazily initialized signal queue
    _stop: bool                            # Stop flag
```

### Constructor

```python
def __init__(self)
```

Creates a new SDL system instance with empty registries.

**Example:**
```python
system = SdlSystem()
```

### Instance Methods

#### `register(process: Optional[SdlProcess]) -> bool`

Register a process with the system.

**Parameters:**
- `process`: Process instance to register

**Returns:**
- `True` if registered successfully, `False` if process is None or already registered

**Raises:**
- `ValidationError`: If process is None or has invalid PID

**Example:**
```python
# Usually called automatically by Process.create()
system = SdlSystem()
process = MyProcess(parent_pid, config_data, system=system)
system.register(process)
```

---

#### `unregister(process: Optional[SdlProcess]) -> bool`

Unregister a process and clean up its resources.

**Parameters:**
- `process`: Process instance to unregister

**Returns:**
- `True` (always)

**Raises:**
- `ValidationError`: If process is None or has invalid PID

**Side Effects:**
- Removes process from `proc_map`
- Removes all timers for the process from `timer_map`
- Removes process from `ready_list`

**Example:**
```python
# Usually called by process.stop_process()
system.unregister(process)
```

---

#### `async enqueue(signal: SdlSignal) -> None`

Add a signal to the system queue.

**Parameters:**
- `signal`: Signal to enqueue

**Raises:**
- `ValidationError`: If signal is None or invalid
- `QueueError`: If queue operation fails

**Example:**
```python
# Usually called by process.input()
await system.enqueue(signal)
```

---

#### `async output(signal: SdlSignal) -> bool`

Route a signal to its destination process.

**Parameters:**
- `signal`: Signal to route (must have destination set)

**Returns:**
- `True` if delivered successfully, `False` otherwise

**Raises:**
- `ValidationError`: If signal is None or has no destination
- `SignalDeliveryError`: If signal delivery to destination fails

**Side Effects:**
- Adds destination process to `ready_list`
- Enqueues signal to process inbox

**Example:**
```python
# Usually called by process.output()
signal = MySignal.create()
signal.set_dst(target_pid)
signal.set_src(source_pid)
await system.output(signal)
```

---

#### `startTimer(timer: Optional[SdlTimer]) -> None`

Start a timer for a process.

**Parameters:**
- `timer`: Timer to start

**Raises:**
- `ValidationError`: If timer is None
- `TimerError`: If timer has no source PID

**Side Effects:**
- Stops timer if already running (prevents duplicates)
- Adds timer to `timer_map[pid]`

**Example:**
```python
# Usually called by process.start_timer()
timer = MyTimer.create()
timer.set_src(process_pid)
timer.start(expiry_time_ms)
system.startTimer(timer)
```

---

#### `stopTimer(timer: Optional[SdlTimer]) -> bool`

Stop a specific timer.

**Parameters:**
- `timer`: Timer to stop

**Returns:**
- `True` if timer was found and stopped, `False` otherwise

**Raises:**
- `ValidationError`: If timer is None

**Side Effects:**
- Removes timer from `timer_map[pid]`
- Deletes PID entry if no timers remain

**Example:**
```python
# Usually called by process.stop_timer()
system.stopTimer(timer)
```

---

#### `async run() -> bool`

Run the main event loop.

**Returns:**
- `True` when stopped normally

**Behavior:**
- Processes signals from queue
- Checks for timer expiries
- Yields to other async tasks
- Stops when `SdlSystem.stop()` is called

**Example:**
```python
async def main():
    system = SdlSystem()
    await MyProcess.create(None, None, system=system)
    await system.run()  # Runs forever

asyncio.run(main())
```

---

#### `stop() -> None`

Signal the system to stop.

**Side Effects:**
- Sets internal `_stop` flag
- Event loop will stop on next iteration

**Example:**
```python
# Called by a process to shut down the system
system.stop()

# Or from within a process:
self._system.stop()
```

---

#### `async expire(msec: int) -> None`

Check for and deliver expired timers.

**Parameters:**
- `msec`: Current time in milliseconds

**Side Effects:**
- Delivers expired timers as signals
- Removes expired timers from `timer_map`

**Example:**
```python
# Called automatically by event loop
await system.expire(int(time() * 1000))
```

---

## SdlProcess

Base class for all processes (actors).

### Constructor

```python
def __init__(self, parent_pid: Optional[str], config_data: Optional[Any] = None, system: Optional[SdlSystem] = None)
```

**Parameters:**
- `parent_pid`: PID of parent process (or None for root processes)
- `config_data`: Optional configuration data
- `system`: SDL system instance (required in v1.0.0+)

**Note:** Use `await Process.create()` instead of calling `__init__` directly.

---

### Class Methods

#### `async create(parent_pid: Optional[str], config_data: Optional[Any] = None, system: Optional[SdlSystem] = None) -> SdlProcess`

Factory method to create and register a process.

**Parameters:**
- `parent_pid`: PID of parent process
- `config_data`: Optional configuration data
- `system`: SDL system instance (required in v1.0.0+)

**Returns:**
- Fully initialized and registered process instance

**Example:**
```python
class MyProcess(SdlProcess):
    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._done()

    async def start_handler(self, signal):
        await self.next_state(SdlState("running"))

# Create system and process
system = SdlSystem()
process = await MyProcess.create(None, {"key": "value"}, system=system)
```

---

#### `name() -> str`

Get the class name.

**Returns:**
- Class name as string

**Example:**
```python
MyProcess.name()  # Returns: "MyProcess"
```

---

#### `id() -> int`

Get the unique class ID.

**Returns:**
- Unique integer ID for this class

**Example:**
```python
MyProcess.id()  # Returns: 1 (first class registered)
```

---

### Instance Methods

#### `pid() -> str`

Get the process ID.

**Returns:**
- PID in format `ClassName(id.instance)`

**Example:**
```python
process.pid()  # Returns: "MyProcess(1.0)"
```

---

#### `current_state() -> SdlState`

Get the current state.

**Returns:**
- Current state object

**Example:**
```python
state = process.current_state()
print(state.name())  # "running"
```

---

#### `async next_state(state: SdlState) -> None`

Transition to a new state.

**Parameters:**
- `state`: New state to transition to

**Side Effects:**
- Updates current state
- Logs state transition
- Re-delivers saved signals

**Example:**
```python
async def handler(self, signal):
    # Do work...
    await self.next_state(self.state_done)
```

---

#### `async output(signal: SdlSignal, dst: str) -> bool`

Send a signal to another process.

**Parameters:**
- `signal`: Signal to send
- `dst`: Destination PID

**Returns:**
- `True` if sent successfully, `False` otherwise

**Side Effects:**
- Sets signal source to `self.pid()`
- Sets signal destination to `dst`
- Routes signal through `SdlSystem`

**Raises:**
- `ValidationError`: If signal is not an SdlSignal instance

**Example:**
```python
async def handler(self, signal):
    response = MySignal.create(data="response")
    await self.output(response, signal.src())
```

---

#### `start_timer(timer: SdlTimer, msec: int) -> None`

Start a timer that will expire after specified milliseconds (relative time).

**Parameters:**
- `timer`: Timer instance
- `msec`: Milliseconds until expiry (relative time)

**Side Effects:**
- Sets timer source/destination to `self.pid()`
- Calculates absolute expiry time
- Registers timer with system

**Raises:**
- `ValidationError`: If timer is not an SdlTimer instance
- `TimerError`: If msec is negative

**Example:**
```python
class MyProcess(SdlProcess):
    class TimeoutTimer(SdlTimer):
        pass

    async def handler(self, signal):
        # Start 5 second timer
        self.start_timer(self.TimeoutTimer.create(), 5000)
```

---

#### `start_timer_abs(timer: SdlTimer, sec: int) -> None`

Start a timer with absolute expiry time in seconds.

**Parameters:**
- `timer`: Timer instance
- `sec`: Absolute time in seconds when timer should expire

**Side Effects:**
- Sets timer source/destination to `self.pid()`
- Registers timer with system using absolute time

**Raises:**
- `ValidationError`: If timer is not an SdlTimer instance
- `TimerError`: If sec is not positive

**Example:**
```python
from time import time

class MyProcess(SdlProcess):
    class ScheduledTimer(SdlTimer):
        pass

    async def handler(self, signal):
        # Timer expires at specific time
        expiry_time = int(time()) + 3600  # 1 hour from now
        self.start_timer_abs(self.ScheduledTimer.create(), expiry_time)
```

---

#### `stop_timer(timer: SdlTimer) -> None`

Stop a running timer.

**Parameters:**
- `timer`: Timer instance to stop

**Side Effects:**
- Removes timer from system timer map

**Raises:**
- `ValidationError`: If timer is not an SdlTimer instance

**Example:**
```python
# Stop a previously started timer
self.stop_timer(self.timeout_timer)
```

---

#### `async stop() -> None`

Initiate process shutdown.

**Side Effects:**
- Sends `SdlStoppingSignal` to self

**Example:**
```python
async def shutdown_handler(self, signal):
    await self.stop()
```

---

#### `stop_process() -> None`

Immediately stop and unregister the process.

**Side Effects:**
- Unregisters process from system
- Stops all timers
- Logs stop event

**Example:**
```python
async def stopping_handler(self, signal):
    self.stop_process()
```

---

### Protected Methods (For Subclasses)

#### `_init_state_machine() -> None`

**Must be overridden** by subclasses to define the FSM.

**Example:**
```python
def _init_state_machine(self):
    self._event(start, SdlStartSignal, self.start_handler)
    self._event(self.state_run, MySignal, self.run_handler)
    self._done()
```

---

#### `_event(state: SdlState, signal: Type[SdlSignal], handler: Callable) -> SdlProcess`

Register a state transition handler.

**Parameters:**
- `state`: State in which this handler is active
- `signal`: Signal type that triggers the handler
- `handler`: Async function to call

**Returns:**
- Self (for method chaining)

**Example:**
```python
self._event(start, SdlStartSignal, self.start_handler)
```

---

#### `_done() -> None`

Finalize state machine definition.

**Example:**
```python
def _init_state_machine(self):
    # ... register events ...
    self._done()
```

---

## SdlSingletonProcess

Base class for singleton processes (only one instance can exist).

### Class Methods

#### `async create(parent_pid: Optional[str], config_data: Optional[Any] = None, system: Optional[SdlSystem] = None) -> SdlSingletonProcess`

Create or return existing singleton instance.

**Parameters:**
- `parent_pid`: PID of parent process
- `config_data`: Optional configuration data
- `system`: SDL system instance (required in v1.0.0+)

**Returns:**
- The singleton instance

**Behavior:**
- First call: Creates new instance
- Subsequent calls: Returns existing instance

**Example:**
```python
class DatabaseManager(SdlSingletonProcess):
    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._done()

system = SdlSystem()

# First call creates instance
db1 = await DatabaseManager.create(None, None, system=system)

# Second call returns same instance
db2 = await DatabaseManager.create(None, None, system=system)

assert db1.pid() == db2.pid()  # Same instance!
```

---

#### `single_pid() -> str`

Get the PID of the singleton instance.

**Returns:**
- PID in format `ClassName(id.0)`

**Example:**
```python
DatabaseManager.single_pid()  # "DatabaseManager(5.0)"
```

---

## SdlSignal

Base class for all signals (messages).

### Constructor

```python
def __init__(self, _data: Optional[Any] = None)
```

**Parameters:**
- `_data`: Optional data payload

**Note:** Use `Signal.create()` instead of calling `__init__` directly.

---

### Class Methods

#### `id() -> int`

Get the unique signal type ID.

**Returns:**
- Unique integer ID for this signal class

**Example:**
```python
class MySignal(SdlSignal):
    pass

MySignal.id()  # Returns: 10 (example)
```

---

#### `create(_data: Optional[Any] = None) -> SdlSignal`

Factory method to create a signal instance.

**Parameters:**
- `_data`: Optional data payload

**Returns:**
- Signal instance with ID set

**Example:**
```python
signal = MySignal.create(data={"key": "value"})
```

---

### Instance Methods

#### `name() -> str`

Get the signal name.

**Returns:**
- Signal class name

**Example:**
```python
signal.name()  # "MySignal"
```

---

#### `src() -> Optional[str]`

Get the source PID.

**Returns:**
- Source PID or None if not set

**Example:**
```python
async def handler(self, signal):
    sender = signal.src()  # Who sent this?
```

---

#### `set_src(_src: str) -> None`

Set the source PID.

**Parameters:**
- `_src`: Source PID

**Example:**
```python
signal.set_src("MyProcess(1.0)")
```

---

#### `dst() -> Optional[str]`

Get the destination PID.

**Returns:**
- Destination PID or None if not set

**Example:**
```python
destination = signal.dst()
```

---

#### `set_dst(_dst: str) -> None`

Set the destination PID.

**Parameters:**
- `_dst`: Destination PID

**Example:**
```python
signal.set_dst("MyProcess(1.1)")
```

---

#### `dumpdata() -> Optional[str]`

Get a human-readable representation of the signal data.

**Returns:**
- String representation or None

**Note:** Override in subclasses to customize.

**Example:**
```python
class MySignal(SdlSignal):
    def dumpdata(self):
        return f"MyData: {self.data}"
```

---

## SdlTimer

Timer signal that delivers itself after a specified duration.

**Inherits from:** `SdlSignal`

### Instance Methods

#### `start(msec: int) -> None`

Set the timer duration.

**Parameters:**
- `msec`: Absolute expiry time in milliseconds since epoch

**Example:**
```python
timer = MyTimer.create()
current_time_ms = int(time() * 1000)
timer.start(current_time_ms + 5000)  # 5 seconds from now
```

---

#### `expired() -> bool`

Check if timer has expired.

**Returns:**
- `True` if expired, `False` otherwise

**Example:**
```python
if timer.expired():
    print("Timer has expired!")
```

---

#### `expire(msec: int) -> None`

Update timer expiry check.

**Parameters:**
- `msec`: Current time in milliseconds

**Example:**
```python
timer.expire(current_time_ms)
if timer.expired():
    # Deliver timer
```

---

#### `appcorr() -> int`

Get the application correlation value.

**Returns:**
- Integer correlation value

**Usage:** Distinguish between multiple instances of the same timer type.

**Example:**
```python
timer.set_appcorr(42)
correlation = timer.appcorr()
```

---

#### `set_appcorr(_appcorr: int) -> None`

Set the application correlation value.

**Parameters:**
- `_appcorr`: Correlation value

**Example:**
```python
timer = MyTimer.create()
timer.set_appcorr(user_id)  # Track which user this timer is for
```

---

## SdlState

Represents a state in a finite state machine.

### Constructor

```python
def __init__(self, name: str)
```

**Parameters:**
- `name`: State name

**Example:**
```python
state_idle = SdlState("idle")
state_active = SdlState("active")
```

---

### Instance Methods

#### `name() -> str`

Get the state name.

**Returns:**
- State name

**Example:**
```python
state.name()  # "idle"
```

---

### Pre-defined States

```python
from pysdl.state import start, wait, star

# start: Initial state for all processes
# wait: Generic waiting state
# star: Wildcard state matching any state
```

### Star State (`star`)

**Module**: `pysdl.state`

The `star` wildcard state matches any state. Use it to register handlers that should work regardless of the current state.

**Example:**
```python
from pysdl.state import star

# Handle emergency from any state
self._event(star, EmergencyStopSignal, self.emergency_stop)
```

---

## SdlStateMachine

Finite state machine implementation.

**Note:** Typically used internally by `SdlProcess`. Users rarely interact directly.

### Instance Methods

#### `state(state: SdlState) -> SdlStateMachine`

Set the current state for registration.

**Parameters:**
- `state`: State to register

**Returns:**
- Self (for method chaining)

**Raises:**
- `ValidationError`: If state is not an SdlState instance

---

#### `event(event: Type[SdlSignal]) -> SdlStateMachine`

Set the current event (signal type) for registration.

**Parameters:**
- `event`: Signal class

**Returns:**
- Self (for method chaining)

**Raises:**
- `ValidationError`: If event is not a SdlSignal subclass

---

#### `handler(handle: Callable) -> SdlStateMachine`

Register handler for current state/event.

**Parameters:**
- `handle`: Async handler function

**Returns:**
- Self (for method chaining)

**Raises:**
- `ValidationError`: If handler is not callable, or if state or event not set

---

#### `done() -> bool`

Finalize FSM definition.

**Returns:**
- `True`

---

#### `find(_state: SdlState, _event: int) -> Optional[Callable]`

Find a handler for a state/event combination using priority-based wildcard matching.

**Priority Matching** (highest to lowest):
1. **Exact match**: Specific state + specific signal
2. **Star state**: `star` + specific signal (handle signal from any state)
3. **Star signal**: Specific state + `SdlStarSignal` (handle any signal in state)
4. **Double star**: `star` + `SdlStarSignal` (catch-all)

**Parameters:**
- `_state`: The current state to match
- `_event`: The signal ID to match

**Returns:**
- Handler function if found, `None` otherwise

**Raises:**
- `ValidationError`: If state or event is None

**Example:**
```python
# Exact match (Priority 1)
handler = fsm.find(state_running, WorkSignal.id())

# Star state match (Priority 2)
handler = fsm.find(star, EmergencySignal.id())  # If star handler registered

# Star signal match (Priority 3)
handler = fsm.find(state_init, unknown_signal.id())  # If star signal handler registered

# Double star match (Priority 4)
handler = fsm.find(state_any, unknown_signal.id())  # If double star handler registered
```

---

## System Signals

Built-in signals for process lifecycle management.

### SdlStartSignal

Sent to a process immediately after registration.

**Purpose:** Trigger initial behavior

**Example:**
```python
def _init_state_machine(self):
    self._event(start, SdlStartSignal, self.start_handler)
    self._done()

async def start_handler(self, signal):
    # Initialize process
    await self.next_state(self.state_running)
```

---

### SdlStoppingSignal

Sent to a process when `await self.stop()` is called.

**Purpose:** Allow graceful shutdown

**Example:**
```python
def _init_state_machine(self):
    self._event(self.state_running, SdlStoppingSignal, self.stopping_handler)
    self._done()

async def stopping_handler(self, signal):
    # Clean up resources
    self.stop_process()
```

---

### SdlStarSignal

**Module**: `pysdl.system_signals`

The star signal wildcard matches any signal type. Use it to register handlers that should catch all signals in a specific state.

**Example:**
```python
from pysdl.system_signals import SdlStarSignal

# Buffer all signals while initializing
self._event(self.state_init, SdlStarSignal, self.buffer_signal)

# Ultimate catch-all (with star state)
self._event(star, SdlStarSignal, self.log_everything)
```

---

## SdlLogger

Event and debug logging.

### Static Methods

#### `configure(level: Optional[str] = None, categories: Optional[Dict[str, bool]] = None, reset: bool = False) -> None`

Configure the logger with desired settings.

**Parameters:**
- `level`: Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL). If None, uses current level or environment variable SDL_LOG_LEVEL
- `categories`: Dictionary mapping category names to enabled status. Category names: "signals", "states", "processes", "timers", "system", "application". If None, all categories remain at current settings
- `reset`: If True, reset to default configuration before applying settings

**Example:**
```python
# Set log level to INFO and enable only signal and state logging
SdlLogger.configure(
    level="INFO",
    categories={"signals": True, "states": True, "processes": False}
)

# Disable all logging by setting high threshold
SdlLogger.configure(level="CRITICAL")

# Reset to defaults
SdlLogger.configure(reset=True)
```

**Environment Variables:**
- `SDL_LOG_LEVEL`: Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `SDL_LOG_CATEGORIES`: Comma-separated list of categories to enable (e.g., "signals,states"). If set, unlisted categories are disabled

---

#### `debug(message: str) -> None`

Log a debug message.

**Parameters:**
- `message`: Debug message to log

**Example:**
```python
SdlLogger.debug("Processing signal queue")
```

---

#### `info(message: str) -> None`

Log an informational message.

**Parameters:**
- `message`: Message to log

**Example:**
```python
SdlLogger.info("System starting up")
```

---

#### `warning(message: str) -> None`

Log a warning message.

**Parameters:**
- `message`: Warning message

**Example:**
```python
SdlLogger.warning("No handler found for signal")
```

---

#### `error(message: str) -> None`

Log an error message.

**Parameters:**
- `message`: Error message to log

**Example:**
```python
SdlLogger.error("Failed to process signal")
```

---

#### `app(process: SdlProcess, message: str) -> None`

Log an application-level message for a process.

**Parameters:**
- `process`: The process logging the message
- `message`: Application message to log

**Example:**
```python
SdlLogger.app(self, "Work item processed successfully")
```

---

#### `event(event_type: str, process: SdlProcess, from_pid: str, to_pid: str) -> None`

Log a process event.

**Parameters:**
- `event_type`: Type of event
- `process`: Process instance
- `from_pid`: Source PID
- `to_pid`: Destination PID

**Example:**
```python
SdlLogger.event("Created", process, parent_pid, process.pid())
```

---

#### `signal(event_type: str, signal: SdlSignal, process: SdlProcess) -> None`

Log a signal event.

**Parameters:**
- `event_type`: Event type ("SdlSig", "SdlSig-NA")
- `signal`: Signal instance
- `process`: Target process

**Example:**
```python
SdlLogger.signal("SdlSig", signal, process)
```

---

#### `state(process: SdlProcess, old_state: SdlState, new_state: SdlState) -> None`

Log a state transition.

**Parameters:**
- `process`: Process instance
- `old_state`: Previous state
- `new_state`: New state

**Example:**
```python
SdlLogger.state(self, self._state, new_state)
```

---

#### `create(process: SdlProcess, parent_pid: Optional[str]) -> None`

Log process creation.

**Parameters:**
- `process`: Created process
- `parent_pid`: Parent PID or None

**Example:**
```python
SdlLogger.create(process, parent_pid)
```

---

## SdlChildrenManager

Manage child processes with metadata and filtering.

### Constructor

```python
def __init__(self)
```

**Example:**
```python
class ParentProcess(SdlProcess):
    def __init__(self, parent_pid, config_data):
        super().__init__(parent_pid, config_data)
        self.children = SdlChildrenManager()
```

---

### Instance Methods

#### `register(child_process: SdlProcess, **kwargs: Any) -> SdlProcess`

Register a child process with optional metadata. The child is added to the end of the list.

**Parameters:**
- `child_process`: Child process instance
- `**kwargs`: Arbitrary key-value metadata

**Returns:**
- The child process (for convenience)

**Example:**
```python
child = await WorkerProcess.create(self.pid(), system=system)
self.children.register(child, role="worker", priority=1)
```

---

#### `add_to_front(child_process: SdlProcess, **kwargs: Any) -> None`

Register a child process at the front of the list with optional metadata.

**Parameters:**
- `child_process`: Child process instance
- `**kwargs`: Arbitrary key-value metadata

**Example:**
```python
child = await WorkerProcess.create(self.pid(), system=system)
self.children.add_to_front(child, role="priority_worker", priority=10)
```

---

#### `get_child_list() -> List[Dict[str, Any]]`

Get all children.

**Returns:**
- List of child dictionaries with keys: `process`, `pid`, `keys`

**Example:**
```python
for child in self.children.get_child_list():
    print(child["pid"], child["keys"])
```

---

#### `get_first_child_with_keys(**kwargs: Any) -> Optional[Dict[str, Any]]`

Find first child matching all specified key-value pairs.

**Parameters:**
- `**kwargs`: Key-value pairs to match

**Returns:**
- Child dictionary or None

**Example:**
```python
child = self.children.get_first_child_with_keys(role="worker")
if child:
    await self.output(signal, child["pid"])
```

---

#### `get_child_list_with_keys(**kwargs: Any) -> List[Dict[str, Any]]`

Find all children matching specified key-value pairs.

**Parameters:**
- `**kwargs`: Key-value pairs to match

**Returns:**
- List of matching child dictionaries

**Example:**
```python
workers = self.children.get_child_list_with_keys(role="worker")
for worker in workers:
    await self.output(WorkSignal.create(), worker["pid"])
```

---

#### `get_by_pid(pid: str) -> Optional[Dict[str, Any]]`

Find child by PID.

**Parameters:**
- `pid`: Process ID

**Returns:**
- Child dictionary or None

**Example:**
```python
child = self.children.get_by_pid("WorkerProcess(2.0)")
```

---

#### `set_keys_by_pid(pid: str, **kwargs: Any) -> bool`

Update metadata for a child.

**Parameters:**
- `pid`: Process ID
- `**kwargs`: Key-value pairs to update

**Returns:**
- `True` if child found and updated, `False` otherwise

**Example:**
```python
self.children.set_keys_by_pid(child_pid, status="busy")
```

---

#### `get_keys_by_pid(pid: str) -> Optional[Dict[str, Any]]`

Get metadata for a child by PID.

**Parameters:**
- `pid`: Process ID

**Returns:**
- Dictionary of metadata key-value pairs, or None if child not found

**Example:**
```python
keys = self.children.get_keys_by_pid(child_pid)
if keys and keys.get("status") == "idle":
    # Assign work to idle child
    pass
```

---

#### `unregister_by_keys(**kwargs: Any) -> None`

Remove first child matching keys.

**Parameters:**
- `**kwargs`: Key-value pairs to match

**Example:**
```python
self.children.unregister_by_keys(status="completed")
```

---

#### `get_count() -> int`

Get number of children.

**Returns:**
- Child count

**Example:**
```python
if self.children.get_count() < 10:
    # Spawn more children
    pass
```

---

## Utilities

### SdlIdGenerator

Generates unique integer IDs.

#### `next() -> int`

Get the next unique ID.

**Returns:**
- Unique integer

**Example:**
```python
from pysdl.id_generator import SdlIdGenerator

unique_id = SdlIdGenerator.next()
```

---

### SdlRegistry

Name-based registry for mapping keys to values. Implemented as a singleton.

The registry provides a global key-value store useful for:
- Registering singleton services (database, logger, config)
- Looking up well-known processes by name
- Service discovery
- Storing arbitrary configuration data

**Usage Pattern:**
```python
from pysdl.registry import SdlRegistry

# Create or get the singleton instance
registry = SdlRegistry()

# Register a service
registry.add("database", db_process.pid())

# Look up the service
db_pid = registry.get("database")
```

#### `__init__() -> None`

Get or create the singleton registry instance.

**Returns:**
- The singleton SdlRegistry instance

**Example:**
```python
# All instances reference the same underlying registry
registry1 = SdlRegistry()
registry2 = SdlRegistry()
# registry1 and registry2 are the same instance
```

---

#### `add(key: str, value: Any) -> None`

Register a value under a key.

**Parameters:**
- `key`: Symbolic name/key
- `value`: Value to store (typically a PID string, but can be any value)

**Example:**
```python
registry = SdlRegistry()
registry.add("database", db_process.pid())
registry.add("config", {"timeout": 30, "retries": 3})
```

---

#### `get(key: str) -> Any`

Look up value by key.

**Parameters:**
- `key`: Symbolic name/key

**Returns:**
- The stored value

**Raises:**
- `KeyError`: If key is not found in registry

**Example:**
```python
registry = SdlRegistry()
try:
    db_pid = registry.get("database")
    await self.output(signal, db_pid)
except KeyError:
    SdlLogger.error("Database service not registered")
```

---

## Complete Example

Here's a complete example demonstrating the API:

```python
import asyncio
from pysdl import (
    SdlProcess, SdlSignal, SdlState, SdlTimer,
    SdlSystem, SdlStartSignal, SdlStoppingSignal,
    start, SdlLogger
)


class WorkRequest(SdlSignal):
    """Request to perform work."""
    def dumpdata(self):
        return f"Work: {self.data}"


class WorkResponse(SdlSignal):
    """Response after work completed."""
    pass


class WorkerProcess(SdlProcess):
    """Worker process that handles work requests."""

    class TimeoutTimer(SdlTimer):
        """Timeout for work completion."""
        pass

    state_idle = SdlState("idle")
    state_working = SdlState("working")

    async def start_handler(self, signal):
        """Initialize worker."""
        SdlLogger.info(f"Worker {self.pid()} ready")
        await self.next_state(self.state_idle)

    async def idle_work_request(self, signal):
        """Handle work request."""
        SdlLogger.info(f"Worker {self.pid()} processing work")

        # Start timeout timer
        self.start_timer(self.TimeoutTimer.create(), 5000)

        # Do work...
        await self.next_state(self.state_working)

        # Send response
        response = WorkResponse.create()
        await self.output(response, signal.src())

    async def working_timeout(self, signal):
        """Handle timeout."""
        SdlLogger.warning(f"Worker {self.pid()} timed out")
        await self.next_state(self.state_idle)

    async def stopping_handler(self, signal):
        """Handle shutdown."""
        SdlLogger.info(f"Worker {self.pid()} stopping")
        self.stop_process()

    def _init_state_machine(self):
        """Define state machine."""
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_idle, WorkRequest, self.idle_work_request)
        self._event(self.state_working, self.TimeoutTimer, self.working_timeout)
        self._event(self.state_working, SdlStoppingSignal, self.stopping_handler)
        self._done()


class ManagerProcess(SdlProcess):
    """Manager that creates workers and assigns work."""

    async def start_handler(self, signal):
        """Create workers."""
        self.worker1 = await WorkerProcess.create(self.pid(), system=self._system)
        self.worker2 = await WorkerProcess.create(self.pid(), system=self._system)

        # Send work request
        work = WorkRequest.create(data="Build widget")
        await self.output(work, self.worker1.pid())

    def _init_state_machine(self):
        """Define state machine."""
        self._event(start, SdlStartSignal, self.start_handler)
        self._done()


async def main():
    """Entry point."""
    # Create system instance
    system = SdlSystem()

    # Create manager process
    await ManagerProcess.create(None, system=system)

    # Run the system
    await system.run()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Summary

This API reference covers all public classes and methods in PySDL. For more information:

- **Architecture**: See [architecture.md](architecture.md)
- **Tutorial**: See [getting_started.md](getting_started.md)
- **Examples**: See [examples.md](examples.md)
- **Troubleshooting**: See [troubleshooting.md](troubleshooting.md)
