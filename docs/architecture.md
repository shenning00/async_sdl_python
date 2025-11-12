# PySDL Architecture Guide

This document provides a comprehensive overview of the PySDL architecture, design decisions, and implementation patterns.

## Table of Contents

1. [Overview](#overview)
2. [Actor Model Design](#actor-model-design)
3. [Process Lifecycle](#process-lifecycle)
4. [State Machine Pattern](#state-machine-pattern)
5. [Signal Routing Mechanism](#signal-routing-mechanism)
6. [Timer System](#timer-system)
7. [Event Loop Architecture](#event-loop-architecture)
8. [Design Decisions](#design-decisions)
9. [Concurrency Model](#concurrency-model)
10. [Memory Management](#memory-management)

## Overview

PySDL implements the **Specification and Description Language (SDL)** actor model pattern, providing a framework for building concurrent, event-driven applications in Python. The architecture is built on three core pillars:

1. **Processes (Actors)**: Independent computational units
2. **Signals (Messages)**: Asynchronous communication primitives
3. **State Machines**: Behavior definition through state transitions

```
┌─────────────────────────────────────────────────────────────┐
│               SdlSystem Instance (v1.0.0+)                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Central Event Loop                       │  │
│  │  • Signal Queue (asyncio.Queue)                       │  │
│  │  • Process Registry (proc_map)                        │  │
│  │  • Timer Registry (timer_map)                         │  │
│  │  • Instance-based (multiple systems possible)        │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         ▼                  ▼                  ▼             │
│   ┌───────────┐      ┌───────────┐      ┌───────────┐       │
│   │ Process 1 │      │ Process 2 │      │ Process N │       │
│   │           │      │           │      │           │       │
│   │  ┌─────┐  │      │  ┌─────┐  │      │  ┌─────┐  │       │
│   │  │ FSM │  │◄────►│  │ FSM │  │◄────►│  │ FSM │  │       │
│   │  └─────┘  │      │  └─────┘  │      │  └─────┘  │       │
│   │ _system:  │      │ _system:  │      │ _system:  │       │
│   │   ref     │      │   ref     │      │   ref     │       │
│   └───────────┘      └───────────┘      └───────────┘       │
│         △                  △                  △             │
│         └──────────────────┼──────────────────┘             │
│                      Signals Flow                           │
└─────────────────────────────────────────────────────────────┘
```

## Actor Model Design

### Core Principles

PySDL follows the actor model's fundamental principles:

1. **Isolation**: Each process maintains its own state; no shared mutable state
2. **Message Passing**: All communication happens through asynchronous signals
3. **Location Transparency**: Processes are addressed by PID, not by reference
4. **Concurrent Execution**: Multiple processes can be active simultaneously via asyncio

### Process (Actor) Characteristics

Each `SdlProcess` instance:

- Has a unique Process ID (PID) in the format: `ClassName(id.instance)`
- Maintains a finite state machine (FSM) defining behavior
- Receives signals through a system-managed queue
- Executes state transitions asynchronously
- Can create child processes forming hierarchies
- Can start/stop multiple timers

### Why the Actor Model?

The actor model provides several advantages:

- **Simplicity**: No locks, mutexes, or shared state
- **Scalability**: Easy to reason about concurrent behavior
- **Fault Isolation**: Process failures don't propagate automatically
- **Natural Concurrency**: Aligns well with asyncio's event loop
- **Testability**: Each process can be tested in isolation

## Process Lifecycle

### Lifecycle States

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ┌──────────┐                                           │
│  │ Created  │  Process.__init__() called                │
│  └────┬─────┘                                           │
│       │                                                 │
│       │ await Process.create()                          │
│       ▼                                                 │
│  ┌──────────┐                                           │
│  │Registering│  _register() -> SdlSystem.register()    │
│  └────┬─────┘                                           │
│       │                                                 │
│       │ SdlStartSignal sent to self                     │
│       ▼                                                 │
│  ┌──────────┐                                           │
│  │  Active  │  Processing signals, changing states      │
│  └────┬─────┘                                           │
│       │                                                 │
│       │ await self.stop()                               │
│       ▼                                                 │
│  ┌──────────┐                                           │
│  │ Stopping │  SdlStoppingSignal sent to self           │
│  └────┬─────┘                                           │
│       │                                                 │
│       │ stop_process() -> SdlSystem.unregister()        │
│       ▼                                                 │
│  ┌──────────┐                                           │
│  │ Stopped  │  Removed from proc_map, timers cleared    │
│  └──────────┘                                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Creation Pattern

Processes use the **factory method pattern** for creation:

```python
# CORRECT: Using factory method
process = await MyProcess.create(parent_pid, config_data)

# INCORRECT: Direct instantiation (process won't be registered)
process = MyProcess(parent_pid, config_data)  # Don't do this!
```

The `create()` class method:
1. Calls `__init__()` to construct the process
2. Calls `_register()` to add it to the system
3. Initializes the state machine via `_init_state_machine()`
4. Sends `SdlStartSignal` to begin execution
5. Returns the fully initialized process

### Registration

During registration (`_register()`):

1. State machine is initialized via `_init_state_machine()`
2. Process is added to `SdlSystem.proc_map`
3. Creation event is logged
4. Initial state transition is logged
5. `SdlStartSignal` is sent to trigger initial behavior

### Termination

Process termination follows these steps:

1. **Initiate**: Call `await self.stop()`
2. **Signal**: `SdlStoppingSignal` is sent to self
3. **Handler**: State machine handles stopping signal
4. **Cleanup**: Handler calls `self.stop_process()`
5. **Unregister**: Process removed from `proc_map`, `timer_map`, and `ready_list`

## State Machine Pattern

### Finite State Machine (FSM) Design

Each process contains an `SdlStateMachine` instance that maps `(state, signal_type)` pairs to handler functions:

```
State Machine Structure:
  _handlers: Dict[SdlState, Dict[int, Handler]]
             └─────┬─────┘  └────┬────┘  └──┬──┘
                  State      Signal ID   Async Function
```

### Defining State Machines

State machines are defined in `_init_state_machine()`:

```python
def _init_state_machine(self):
    # Register: (State, SignalType, Handler)
    self._event(start, SdlStartSignal, self.start_handler)
    self._event(state_a, SignalX, self.state_a_signal_x_handler)
    self._event(state_b, SignalY, self.state_b_signal_y_handler)
    self._done()  # Finalize FSM
```

### Handler Naming Convention

By convention, handlers are named: `{state}_{signal}`:

```python
async def start_StartSignal(self, signal):
    """Handler for SdlStartSignal in start state."""
    ...

async def wait_timeout_TimeoutTimer(self, signal):
    """Handler for TimeoutTimer in wait_timeout state."""
    ...
```

### State Transitions

State transitions occur via `await self.next_state(new_state)`:

```python
async def start_StartSignal(self, signal):
    # Do work...
    await self.output(SomeSignal.create(), other_pid)
    # Transition to new state
    await self.next_state(self.state_waiting)
```

**Key points:**

- State transitions are logged automatically
- Saved signals are re-delivered in the new state
- Only one state is active at a time
- State transitions are immediate (not queued)

### Signal Lookup

When a signal arrives:

1. System looks up destination process in `proc_map`
2. Process looks up handler in FSM: `_handlers[current_state][signal.id()]`
3. If handler found: execute it
4. If no handler: log warning (signal is dropped)

## Signal Routing Mechanism

### Signal Structure

Every `SdlSignal` contains:

- **ID**: Unique type identifier (class-level, auto-generated)
- **Name**: Signal class name
- **Source PID**: Sender's process ID
- **Destination PID**: Receiver's process ID
- **Data**: Optional payload (any type)

### Signal Flow

```
┌──────────────────────────────────────────────────────────┐
│                      Signal Journey                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Process A                                               │
│  ┌────────────────────────────────────────┐              │
│  │ await self.output(signal, dst_pid)     │              │
│  │   • Sets signal.src = self.pid()       │              │
│  │   • Sets signal.dst = dst_pid          │              │
│  │   • Calls SdlSystem.output(signal)     │              │
│  └────────────┬───────────────────────────┘              │
│               │                                          │
│               ▼                                          │
│  SdlSystem                                               │
│  ┌────────────────────────────────────────┐              │
│  │ SdlSystem.output(signal)               │              │
│  │   • Looks up dst in proc_map           │              │
│  │   • If found: calls process.input()    │              │
│  │   • If not found: logs SdlSig-NA       │              │
│  └────────────┬───────────────────────────┘              │
│               │                                          │
│               ▼                                          │
│  Process B                                               │
│  ┌────────────────────────────────────────┐              │
│  │ process.input(signal)                  │              │
│  │   • Calls SdlSystem.enqueue(signal)    │              │
│  └────────────┬───────────────────────────┘              │
│               │                                          │
│               ▼                                          │
│  SdlSystem Queue                                         │
│  ┌────────────────────────────────────────┐              │
│  │ queue.put(signal)                      │              │
│  │   • Signal queued for processing       │              │
│  └────────────┬───────────────────────────┘              │
│               │                                          │
│               ▼                                          │
│  Event Loop                                              │
│  ┌────────────────────────────────────────┐              │
│  │ signal = queue.get()                   │              │
│  │ process = proc_map[signal.dst()]       │              │
│  │ handler = process.lookup_transition()  │              │
│  │ await handler(signal)                  │              │
│  └────────────────────────────────────────┘              │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Signal Queue

The system uses a single central queue with `asyncio.Queue` (async-native):

- **FIFO ordering**: Signals processed in order received
- **Async-native**: Integrates seamlessly with asyncio event loop
- **Lazy initialization**: Queue created in `_get_queue()` to ensure proper event loop context
- **Non-blocking**: Uses `await queue.get()` for async signal retrieval

### Signal Delivery Guarantees

**Current guarantees:**

- **At-most-once delivery**: Signal delivered once or lost if process doesn't exist
- **FIFO per sender**: Order preserved from same sender
- **No guarantee of cross-process ordering**: Signals from A and B to C may interleave

**Not guaranteed:**

- Delivery if destination process stops before signal is processed
- Delivery if destination doesn't have a handler (signal dropped with warning)

## Timer System

### Timer Architecture

Timers are special signals that deliver themselves after a specified duration:

```
Timer Lifecycle:
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Process                                                │
│  ┌─────────────────────────────────────────┐            │
│  │ timer = MyTimer.create()                │            │
│  │ self.start_timer(timer, 5000)  # 5 sec  │            │
│  └────────────┬────────────────────────────┘            │
│               │                                         │
│               ▼                                         │
│  ┌─────────────────────────────────────────┐            │
│  │ Timer is registered in timer_map:       │            │
│  │   timer_map[pid] = [timer1, timer2, ...] │            │
│  │ Timer expiry time calculated:            │            │
│  │   expiry = current_time_ms + 5000        │            │
│  └────────────┬────────────────────────────┘            │
│               │                                         │
│               ▼                                         │
│  ┌─────────────────────────────────────────┐            │
│  │ Event loop checks timers each iteration │            │
│  │ When expired:                            │            │
│  │   • await SdlSystem.output(timer)        │            │
│  │   • Timer removed from timer_map         │            │
│  └────────────┬────────────────────────────┘            │
│               │                                         │
│               ▼                                         │
│  ┌─────────────────────────────────────────┐            │
│  │ Timer delivered as signal to process    │            │
│  │ Handler in FSM processes timer           │            │
│  └─────────────────────────────────────────┘            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Timer Storage

Timers are stored in `timer_map: Dict[str, List[SdlTimer]]`:

- **Key**: Process PID
- **Value**: List of active timers for that process
- **Multiple timers**: Same process can have multiple concurrent timers
- **Automatic cleanup**: Entry removed when timer list becomes empty

### Timer Precision

- **Resolution**: Milliseconds
- **Accuracy**: Depends on event loop iteration frequency
- **Drift**: Minimal for short timers, can accumulate for long-running systems
- **Expiry check**: Performed every event loop iteration

### Timer Operations

**Starting a timer:**
```python
timer = MyTimer.create()
self.start_timer(timer, msec=1000)  # 1 second
```

**Stopping a timer:**
```python
self.stop_timer(timer)
```

**Timer equality:** Based on timer ID and appcorr value (application correlation)

## Event Loop Architecture

### Main Event Loop

The `SdlSystem.run()` method implements the main event loop:

```python
async def run():
    while True:
        # 1. Get next signal from queue
        try:
            signal = get_next_signal()

            # 2. Route signal to process
            process = lookup_proc_map(signal.dst())
            handler = process.lookup_transition(signal)

            # 3. Execute handler
            await handler(signal)
        except Empty:
            pass

        # 4. Check timer expiries
        await expire(current_time_ms())

        # 5. Check for system stop
        if _stop:
            loop.stop()

        # 6. Yield to other tasks
        await asyncio.sleep(0)
```

### Loop Phases

Each iteration consists of:

1. **Signal Processing**: Dequeue and handle one signal
2. **Timer Expiry**: Check and deliver expired timers
3. **Stop Check**: Check for system shutdown
4. **Yield**: Allow other asyncio tasks to run

### Concurrency Points

Concurrency occurs at:

- **Signal handlers**: Each handler is async, can await operations
- **Timer delivery**: Timers delivered asynchronously
- **Process creation**: Factory methods are async
- **State transitions**: Can trigger async signal deliveries

### Blocking Prevention

To avoid blocking:

- Use `await asyncio.sleep(0)` to yield control
- All I/O operations should be async
- Handlers should complete quickly (no long computations)
- Heavy work should be delegated to separate processes

## Design Decisions

### 1. Instance-Based System Design

**Current (v1.0.0+): Instance-based**

```python
class SdlSystem:
    def __init__(self):
        self.proc_map: Dict[str, SdlProcess] = {}  # Instance variable
        self.timer_map: Dict[str, List[SdlTimer]] = {}
        self.ready_list: List[SdlProcess] = []
        # ...

    async def run(self):
        ...
```

**Rationale:**
- Enables multiple independent systems in one process
- Better testability with isolated system instances
- No global state to reset between tests
- Proper object-oriented design
- Thread-safe system instances

**Benefits:**
- Run multiple SDL systems concurrently
- Each test gets a fresh system instance
- More flexible for advanced use cases
- Aligns with modern Python best practices

### 2. Queue Choice

**Current: `asyncio.Queue` (async-native)**

**Implementation details:**
- Queue is lazily initialized in `_get_queue()` method
- Lazy initialization ensures queue is created within proper event loop context
- Each `SdlSystem` instance maintains its own queue instance
- Integrates seamlessly with async/await patterns

**Rationale:**
- No threading used in codebase
- `asyncio.Queue` integrates natively with async/await
- Non-blocking operations via `await queue.get()` and `await queue.put()`
- Better performance than thread-safe `queue.Queue` for async code
- Lazy initialization prevents event loop context issues during system creation

### 3. PID Format

**Current: `ClassName(id.instance)`**

Example: `PingPongProcess(1.0)`, `PingPongProcess(1.1)`

**Rationale:**
- Human-readable in logs
- Encodes both class and instance information
- Unique across process types and instances

**Components:**
- `ClassName`: Process class name
- `id`: Unique class ID (auto-generated)
- `instance`: Instance number (0, 1, 2, ...)

### 4. Signal ID Generation

**Pattern: Class-level lazy initialization**

```python
class MySignal(SdlSignal):
    _id: Optional[int] = None

    @classmethod
    def id(cls) -> int:
        if cls._id is None:
            cls._id = SdlIdGenerator.next()
        return cls._id
```

**Rationale:**
- Same signal type has same ID across instances
- IDs generated on first use
- Deterministic within a session
- Fast lookup in state machines

### 5. Type Safety

**Extensive use of type hints:**

```python
def output(self, signal: SdlSignal, dst: str) -> bool:
    ...
```

**Rationale:**
- Better IDE support (autocomplete, error detection)
- Easier to understand API
- Catches bugs at development time (with mypy)
- Self-documenting code

### 6. Async-First Design

**All signal handlers are async:**

```python
async def state_signal_handler(self, signal: SdlSignal) -> None:
    await self.output(response, signal.src())
```

**Rationale:**
- Aligns with Python's async/await paradigm
- Enables non-blocking I/O
- Simplifies concurrency model
- Future-proof for async operations

## Concurrency Model

### Asyncio Integration

PySDL leverages Python's `asyncio` for concurrency:

- **Single-threaded**: No thread synchronization needed
- **Cooperative multitasking**: Tasks yield control voluntarily
- **Event loop**: Managed by asyncio
- **Non-blocking I/O**: All I/O should be async

### Concurrency Guarantees

**Safe:**
- Multiple processes can be active (handlers executing)
- Signal delivery is atomic (queue operations)
- State transitions are immediate and atomic

**Not safe:**
- Direct attribute access across processes (don't do this!)
- Shared mutable state (violates actor model)

### Avoiding Race Conditions

**Good practices:**

1. **No shared state**: Each process owns its data
2. **Message passing**: Communicate via signals
3. **Immutable signals**: Don't modify signals after sending
4. **Atomic transitions**: Complete state transitions without awaiting external events

## Memory Management

### Process Lifecycle

Processes are garbage collected when:
- Removed from `proc_map` via `unregister()`
- No external references remain
- All timers are stopped

### Signal Lifecycle

Signals are garbage collected after:
- Handler execution completes
- Explicit `del signal` in event loop

### Memory Leaks to Avoid

**Potential leaks:**

1. **Orphaned timers**: Timers for stopped processes
   - **Solution**: `unregister()` clears all timers for PID

2. **Circular references**: Parent-child process references
   - **Solution**: Store PIDs (strings), not process references

3. **Unbounded queues**: Queue grows indefinitely
   - **Mitigation**: Ensure processes are responsive

4. **Save signals**: Signals saved for later delivery
   - **Mitigation**: Clear save queue on state transitions

### Best Practices

1. **Stop processes explicitly**: Call `await process.stop()`
2. **Clean up children**: Parent should stop children before stopping self
3. **Stop timers**: Stop timers when no longer needed
4. **Avoid circular references**: Use PIDs for inter-process references
5. **Limit save signals**: Don't save signals indefinitely

## Performance Considerations

### Throughput Bottlenecks

1. **Single queue**: All signals through one queue
   - **Impact**: Can become bottleneck at high throughput
   - **Mitigation**: Keep handlers fast

2. **Linear timer check**: All timers checked each iteration
   - **Impact**: O(n) complexity for n timers
   - **Mitigation**: Use timers sparingly

3. **Synchronous handler execution**: Handlers execute serially
   - **Impact**: Slow handler blocks others
   - **Mitigation**: Delegate heavy work

### Optimization Opportunities

Future optimizations:

1. **Priority queue for timers**: O(log n) expiry checks
2. **Multiple queues**: Per-process or priority-based queues
3. **Batch processing**: Process multiple signals per iteration
4. **Async timer checks**: Separate timer expiry task

## Extensibility Points

### Custom Signal Types

Define custom signals by subclassing:

```python
class MyCustomSignal(SdlSignal):
    def __init__(self, data=None):
        super().__init__(data)
        self.custom_field = "value"

    def dumpdata(self):
        return f"Custom: {self.custom_field}"
```

### Custom Timer Types

Define custom timers by subclassing:

```python
class MyCustomTimer(SdlTimer):
    def __init__(self, data=None):
        super().__init__(data)
        self.timer_type = "custom"
```

### Process Hierarchies

Build complex systems using parent-child relationships:

```python
class SupervisorProcess(SdlProcess):
    async def start_handler(self, signal):
        # Create supervised children
        child1 = await WorkerProcess.create(self.pid())
        child2 = await WorkerProcess.create(self.pid())
        # Track children (optional)
        self.children = [child1.pid(), child2.pid()]
```

### Custom Logging

Override logging behavior:

```python
from pysdl.logger import SdlLogger

# Configure logging
SdlLogger.info("Custom message")
SdlLogger.event("EventType", process, from_pid, to_pid)
```

## Summary

PySDL's architecture provides:

- **Clean separation of concerns**: Processes, signals, state machines
- **Async-native design**: Built on asyncio for performance
- **Type safety**: Comprehensive type hints throughout
- **Extensibility**: Easy to customize and extend
- **Simplicity**: Minimal API surface, easy to learn

The actor model and state machine patterns provide a solid foundation for building concurrent, event-driven applications in Python.
