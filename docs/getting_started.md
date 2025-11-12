# Getting Started with PySDL

This tutorial will teach you PySDL step-by-step by building progressively complex examples.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Your First Process](#your-first-process)
4. [Sending Signals](#sending-signals)
5. [State Transitions](#state-transitions)
6. [Using Timers](#using-timers)
7. [Process Hierarchies](#process-hierarchies)
8. [Star Wildcard Matching](#star-wildcard-matching)
9. [Common Patterns](#common-patterns)
10. [Troubleshooting Tips](#troubleshooting-tips)
11. [Next Steps](#next-steps)

---

## Prerequisites

Before you begin with PySDL, ensure you have:

- **Python 3.9 or higher**: PySDL requires Python 3.9+ for modern type hinting and async features
- **Virtual environment**: Recommended to isolate dependencies
  ```bash
  python3 -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  ```
- **Basic async/await knowledge**: Familiarity with Python's asyncio is helpful but not required

---

## Installation

### Option 1: From Source (Recommended for Development)

```bash
# Clone the repository
git clone https://gitlab.com/your-repo/async_sdl_python.git
cd async_sdl_python

# Install in editable mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH=/path/to/async_sdl_python:$PYTHONPATH
```

### Option 2: Using pip (when published)

```bash
pip install pysdl
```

### Verify Installation

```python
python3 -c "import pysdl; print('PySDL installed successfully!')"
```

---

## Your First Process

Let's create the simplest possible PySDL program: a process that starts and immediately stops.

### Step 1: Import Required Classes

```python
import asyncio
from pysdl import (
    SdlProcess,           # Base class for processes
    SdlState,             # State representation
    SdlSystem,            # System event loop
    SdlStartSignal,       # Start signal
    SdlStoppingSignal,    # Stopping signal
    SdlLogger             # Logging
)
from pysdl.state import start  # Pre-defined "start" state
```

### Step 2: Define Your Process

```python
class HelloProcess(SdlProcess):
    """Our first process."""

    def _init_state_machine(self):
        """Define what signals this process handles."""
        # When in "start" state and receive SdlStartSignal,
        # call start_handler
        self._event(start, SdlStartSignal, self.start_handler)

        # Call _done() at the end of _init_state_machine() for clarity (recommended)
        # This marks completion of the state machine setup
        self._done()

    async def start_handler(self, signal):
        """Handler called when process starts."""
        SdlLogger.info("Hello from PySDL!")
        # Stop the system
        self._system.stop()
```

### Step 3: Create and Run

```python
async def main():
    """Entry point."""
    # Create a system instance
    system = SdlSystem()

    # Create the process (automatically registered with system)
    await HelloProcess.create(parent_pid=None, system=system)

    # Run the system (runs until stopped)
    await system.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4: Run It

```bash
python hello.py
```

**Output:**
```
Created         HelloProcess(1.0) [None] [HelloProcess(1.0)]
State           HelloProcess(1.0) [none->start]
SdlSig          SdlStartSignal [HelloProcess(1.0)] [HelloProcess(1.0)]
Hello from PySDL!
```

**What happened:**

1. `HelloProcess.create()` created and registered the process
2. `_init_state_machine()` defined the state machine
3. `SdlStartSignal` was automatically sent to the process
4. `start_handler()` was called, which logged a message and stopped the system

---

## Sending Signals

Let's make two processes talk to each other.

### Step 1: Define a Custom Signal

```python
from pysdl import SdlSignal

class GreetingSignal(SdlSignal):
    """A greeting signal with a message."""

    def dumpdata(self):
        """Pretty-print the data."""
        return f"Greeting: {self.data}"
```

### Step 2: Define Greeter Process

```python
class GreeterProcess(SdlProcess):
    """Process that sends a greeting."""

    state_waiting = SdlState("waiting")

    def __init__(self, parent_pid, config_data=None, system=None):
        super().__init__(parent_pid, config_data, system=system)
        # Extract friend_pid from config_data
        self.friend_pid = config_data.get("friend_pid") if config_data else None

    async def start_handler(self, signal):
        """Send greeting to friend."""
        greeting = GreetingSignal.create("Hello, friend!")
        await self.output(greeting, self.friend_pid)

        SdlLogger.info(f"{self.pid()} sent greeting")
        await self.next_state(self.state_waiting)

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._done()
```

### Step 3: Define Receiver Process

```python
class ReceiverProcess(SdlProcess):
    """Process that receives greetings."""

    state_listening = SdlState("listening")

    async def start_handler(self, signal):
        """Start listening for greetings."""
        SdlLogger.info(f"{self.pid()} is listening")
        await self.next_state(self.state_listening)

    async def listening_greeting(self, signal):
        """Handle greeting signal."""
        SdlLogger.info(f"{self.pid()} received: {signal.data}")

        # Reply back
        reply = GreetingSignal.create("Hi there!")
        await self.output(reply, signal.src())

        # Stop after replying
        await self.stop()

    async def stopping_handler(self, signal):
        """Clean up."""
        self.stop_process()
        self._system.stop()

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_listening, GreetingSignal, self.listening_greeting)
        self._event(self.state_listening, SdlStoppingSignal, self.stopping_handler)
        self._done()
```

### Step 4: Create Both Processes

```python
async def main():
    """Create both processes."""
    # Create a system instance
    system = SdlSystem()

    # Create receiver first
    receiver = await ReceiverProcess.create(None, system=system)

    # Create greeter with receiver's PID in config_data
    greeter = await GreeterProcess.create(
        None,
        config_data={"friend_pid": receiver.pid()},
        system=system
    )

    # Run the system
    await system.run()


if __name__ == "__main__":
    asyncio.run(main())
```

**Key Concepts:**

- **Custom Signals**: Subclass `SdlSignal` to create typed messages
- **Signal Data**: Use the `data` field to carry payloads
- **`output()`**: Send signals to other processes by PID
- **`signal.src()`**: Get the sender's PID for replies

---

## State Transitions

States define what signals a process can handle. Let's build a traffic light.

### Step 1: Define States and Signals

```python
class ChangeSignal(SdlSignal):
    """Signal to change light."""
    pass


class TrafficLight(SdlProcess):
    """A traffic light with three states."""

    # Define states
    state_red = SdlState("red")
    state_yellow = SdlState("yellow")
    state_green = SdlState("green")
```

### Step 2: Define Handlers for Each State

```python
    async def start_handler(self, signal):
        """Start with red light."""
        SdlLogger.info("Traffic light initialized: RED")
        await self.next_state(self.state_red)

    async def red_change(self, signal):
        """Red -> Green."""
        SdlLogger.info("Changing: RED -> GREEN")
        await self.next_state(self.state_green)

    async def green_change(self, signal):
        """Green -> Yellow."""
        SdlLogger.info("Changing: GREEN -> YELLOW")
        await self.next_state(self.state_yellow)

    async def yellow_change(self, signal):
        """Yellow -> Red."""
        SdlLogger.info("Changing: YELLOW -> RED")
        await self.next_state(self.state_red)
```

### Step 3: Define State Machine

```python
    def _init_state_machine(self):
        """Map signals to handlers based on current state."""
        self._event(start, SdlStartSignal, self.start_handler)

        # ChangeSignal has different behavior in each state
        self._event(self.state_red, ChangeSignal, self.red_change)
        self._event(self.state_green, ChangeSignal, self.green_change)
        self._event(self.state_yellow, ChangeSignal, self.yellow_change)

        self._done()
```

### Step 4: Create a Controller

```python
class Controller(SdlProcess):
    """Controls the traffic light."""

    async def start_handler(self, signal):
        """Create traffic light and trigger changes."""
        self.light = await TrafficLight.create(self.pid(), system=self._system)

        # Send multiple change signals
        await self.output(ChangeSignal.create(), self.light.pid())
        await self.output(ChangeSignal.create(), self.light.pid())
        await self.output(ChangeSignal.create(), self.light.pid())

        # Stop system after changes
        self._system.stop()

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._done()
```

**Output:**
```
Traffic light initialized: RED
Changing: RED -> GREEN
Changing: GREEN -> YELLOW
Changing: YELLOW -> RED
```

**Key Concepts:**

- **States**: Define process behavior modes
- **State-Dependent Handlers**: Same signal, different behavior per state
- **State Transitions**: Use `await self.next_state(state)`
- **Logging**: State transitions are automatically logged

---

## Using Timers

Timers are signals that deliver themselves after a delay.

### Step 1: Define a Timer

```python
from pysdl import SdlTimer

class CoffeeTimer(SdlTimer):
    """Timer for coffee brewing."""
    pass


class CoffeeMaker(SdlProcess):
    """Coffee maker process."""

    state_idle = SdlState("idle")
    state_brewing = SdlState("brewing")
```

### Step 2: Start the Timer

```python
    async def start_handler(self, signal):
        """Initialize coffee maker."""
        SdlLogger.info("Coffee maker ready")
        await self.next_state(self.state_idle)

    async def idle_brew_request(self, signal):
        """Start brewing coffee."""
        SdlLogger.info("Starting to brew coffee...")

        # Start 5-second timer
        self.timer = CoffeeTimer.create()
        self.start_timer(self.timer, 5000)  # 5000 ms = 5 seconds

        await self.next_state(self.state_brewing)
```

### Step 3: Handle Timer Expiry

```python
    async def brewing_timer_expired(self, signal):
        """Coffee is ready!"""
        SdlLogger.info("Coffee is ready! ☕")
        await self.next_state(self.state_idle)

        # Stop the system
        self._system.stop()
```

### Step 4: Define Brew Request Signal

```python
class BrewRequest(SdlSignal):
    """Request to brew coffee."""
    pass
```

### Step 5: Complete State Machine

```python
    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_idle, BrewRequest, self.idle_brew_request)
        self._event(self.state_brewing, CoffeeTimer, self.brewing_timer_expired)
        self._done()
```

### Step 6: Create and Test

```python
async def main():
    """Test coffee maker."""
    # Create system instance
    system = SdlSystem()

    # Create coffee maker
    coffee_maker = await CoffeeMaker.create(None, system=system)

    # Send brew request
    await coffee_maker.input(BrewRequest.create())

    # Run the system
    await system.run()


if __name__ == "__main__":
    asyncio.run(main())
```

**Key Concepts:**

- **Timer Definition**: Subclass `SdlTimer`
- **Starting Timers**: `self.start_timer(timer, milliseconds)`
- **Timer Expiry**: Timer delivered as a signal to the process
- **Multiple Timers**: A process can have many concurrent timers

---

## Process Hierarchies

Let's build a parent-child relationship: a supervisor and workers.

### Step 1: Define Worker Process

```python
class WorkSignal(SdlSignal):
    """Signal to perform work."""
    pass


class WorkerProcess(SdlProcess):
    """Worker process."""

    state_idle = SdlState("idle")

    async def start_handler(self, signal):
        """Worker is ready."""
        SdlLogger.info(f"Worker {self.pid()} ready")
        await self.next_state(self.state_idle)

    async def idle_work(self, signal):
        """Perform work."""
        SdlLogger.info(f"Worker {self.pid()} working...")

        # Simulate work with a timer
        self.start_timer(SdlTimer.create(), 1000)

    async def idle_timer(self, signal):
        """Work complete."""
        SdlLogger.info(f"Worker {self.pid()} done!")

        # Notify parent
        parent = self.get_parent()
        if parent:
            done_signal = SdlSignal.create()
            await self.output(done_signal, parent)

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_idle, WorkSignal, self.idle_work)
        self._event(self.state_idle, SdlTimer, self.idle_timer)
        self._done()
```

### Step 2: Define Supervisor Process

```python
class SupervisorProcess(SdlProcess):
    """Supervisor managing workers."""

    async def start_handler(self, signal):
        """Create worker pool."""
        SdlLogger.info("Supervisor creating workers")

        # Create workers (parent_pid = self.pid())
        self.worker1 = await WorkerProcess.create(self.pid(), system=self._system)
        self.worker2 = await WorkerProcess.create(self.pid(), system=self._system)
        self.worker3 = await WorkerProcess.create(self.pid(), system=self._system)

        # Assign work
        await self.output(WorkSignal.create(), self.worker1.pid())
        await self.output(WorkSignal.create(), self.worker2.pid())
        await self.output(WorkSignal.create(), self.worker3.pid())

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._done()
```

### Step 3: Track Children with SdlChildrenManager

```python
from pysdl import SdlChildrenManager


class AdvancedSupervisor(SdlProcess):
    """Supervisor with child tracking."""

    def __init__(self, parent_pid, config_data, system=None):
        super().__init__(parent_pid, config_data, system=system)
        self.children = SdlChildrenManager()
        self.work_completed = 0

    async def start_handler(self, signal):
        """Create and track workers."""
        for i in range(3):
            worker = await WorkerProcess.create(self.pid(), system=self._system)
            # Register with metadata
            self.children.register(worker, worker_id=i, status="idle")

            # Assign work
            await self.output(WorkSignal.create(), worker.pid())

    async def work_done_handler(self, signal):
        """Track completed work."""
        self.work_completed += 1
        SdlLogger.info(f"Work completed: {self.work_completed}/3")

        if self.work_completed == 3:
            SdlLogger.info("All work complete!")
            self._system.stop()

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(start, SdlSignal, self.work_done_handler)
        self._done()
```

**Key Concepts:**

- **Parent-Child**: Pass `self.pid()` as `parent_pid` when creating children
- **`get_parent()`**: Children can access parent PID
- **SdlChildrenManager**: Track and filter children with metadata
- **Supervision**: Parent can monitor and control children

---

## Star Wildcard Matching

PySDL supports wildcard matching in state machines, allowing handlers to match multiple states or signals.

### The Star State

The `star` state matches any state. Use it for handlers that should work regardless of current state:

```python
from pysdl.state import star

class RobustProcess(SdlProcess):
    def _init_state_machine(self):
        # Handle emergency stop from ANY state
        self._event(star, EmergencyStopSignal, self.emergency_stop)

        # Normal state-specific handlers
        self._event(self.state_running, WorkSignal, self.do_work)
        self._done()

    async def emergency_stop(self, signal):
        """Called regardless of current state."""
        await self.cleanup()
        self._system.stop()
```

### The Star Signal

The `SdlStarSignal` matches any signal type. Use it to catch all signals in a specific state:

```python
from pysdl.system_signals import SdlStarSignal

class BufferingProcess(SdlProcess):
    def _init_state_machine(self):
        # Buffer ANY signal while initializing
        self._event(self.state_initializing, SdlStarSignal, self.buffer_signal)

        # Process specific signals when ready
        self._event(self.state_ready, DataSignal, self.process_data)
        self._done()

    async def buffer_signal(self, signal):
        """Buffer any signal received during init."""
        await self.save_signal(signal)
```

### Priority Matching

Handlers are matched in priority order (highest to lowest):

1. **Exact match** - Specific state + specific signal
2. **Star state** - Any state (`star`) + specific signal
3. **Star signal** - Specific state + any signal (`SdlStarSignal`)
4. **Double star** - Any state + any signal (catch-all)

```python
def _init_state_machine(self):
    # Priority 1: Exact match (highest)
    self._event(self.state_active, WorkSignal, self.handle_work)

    # Priority 2: Star state
    self._event(star, EmergencySignal, self.handle_emergency)

    # Priority 3: Star signal
    self._event(self.state_init, SdlStarSignal, self.buffer_all)

    # Priority 4: Double star (lowest - catch-all)
    self._event(star, SdlStarSignal, self.log_unexpected)

    self._done()
```

### Common Use Cases

**Global Error Handlers**:
```python
# Handle errors from any state
self._event(star, ErrorSignal, self.handle_error)
```

**Signal Buffering**:
```python
# Buffer all signals while not ready
self._event(self.state_connecting, SdlStarSignal, self.buffer_signal)
```

**Debug Logging**:
```python
# Log any unexpected signal
self._event(star, SdlStarSignal, self.log_unexpected)
```

---

## Common Patterns

### Pattern 1: Request-Response

```python
class RequestSignal(SdlSignal):
    """Request with correlation ID."""
    pass


class ResponseSignal(SdlSignal):
    """Response with correlation ID."""
    pass


class ClientProcess(SdlProcess):
    state_waiting = SdlState("waiting")

    def __init__(self, parent_pid, config_data=None, system=None):
        super().__init__(parent_pid, config_data, system=system)
        self.server_pid = config_data.get("server_pid") if config_data else None

    async def start_handler(self, signal):
        request = RequestSignal.create({"request_id": 123})
        await self.output(request, self.server_pid)
        await self.next_state(self.state_waiting)

    async def waiting_response(self, signal):
        SdlLogger.info(f"Received response: {signal.data}")
```

### Pattern 2: Timeout with Retry

```python
class RetryProcess(SdlProcess):
    def __init__(self, parent_pid, config_data=None, system=None):
        super().__init__(parent_pid, config_data, system=system)
        self.retry_count = 0
        self.max_retries = 3
        self.server_pid = config_data.get("server_pid") if config_data else None

    async def send_with_timeout(self):
        await self.output(RequestSignal.create(), self.server_pid)
        self.start_timer(self.TimeoutTimer.create(), 5000)

    async def timeout_handler(self, signal):
        self.retry_count += 1
        if self.retry_count < self.max_retries:
            SdlLogger.info(f"Retry {self.retry_count}/{self.max_retries}")
            await self.send_with_timeout()
        else:
            SdlLogger.warning("Max retries exceeded")
```

### Pattern 3: Singleton Service

```python
from pysdl import SdlSingletonProcess


class DatabaseService(SdlSingletonProcess):
    """Only one instance can exist."""

    async def start_handler(self, signal):
        SdlLogger.info("Database service started")
        self.db_connection = self.connect_to_db()

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._done()


# Create system instance
system = SdlSystem()

# First call creates instance
db1 = await DatabaseService.create(None, system=system)

# Second call returns same instance
db2 = await DatabaseService.create(None, system=system)

assert db1.pid() == db2.pid()  # True!
```

### Pattern 4: Broadcast to Children

```python
class BroadcastSupervisor(SdlProcess):
    async def broadcast_to_children(self, signal_type):
        """Send signal to all children."""
        for child in self.children.get_child_list():
            await self.output(signal_type.create(), child["pid"])
```

---

## Troubleshooting Tips

### Problem: Handler Not Called

**Symptom:** Signal sent but handler doesn't execute

**Solutions:**

1. **Check state machine registration:**
   ```python
   # Make sure you registered the handler
   self._event(self.state_active, MySignal, self.my_handler)
   self._done()  # Don't forget this!
   ```

2. **Check current state:**
   ```python
   # Handler only called if in correct state
   SdlLogger.info(f"Current state: {self.current_state().name()}")
   ```

3. **Check signal destination:**
   ```python
   # Make sure PID is correct
   await self.output(signal, correct_pid)
   ```

### Problem: Process Never Starts

**Symptom:** No logs, process seems inactive

**Solution:** Use `create()`, not `__init__()`:

```python
# CORRECT
process = await MyProcess.create(parent_pid)

# INCORRECT - process not registered!
process = MyProcess(parent_pid)
```

### Problem: Timer Never Fires

**Symptom:** Timer started but handler not called

**Solutions:**

1. **Check handler registration:**
   ```python
   self._event(self.state_waiting, MyTimer, self.timer_handler)
   ```

2. **Check you're in the right state:**
   ```python
   # Timer only delivered to current state
   await self.next_state(self.state_waiting)
   ```

3. **Don't create new timer instance for stopping:**
   ```python
   # CORRECT - stop the same timer instance
   self.timer = MyTimer.create()
   self.start_timer(self.timer, 5000)
   # later...
   self.stop_timer(self.timer)

   # INCORRECT - different instance!
   self.stop_timer(MyTimer.create())
   ```

### Problem: AttributeError on signal.src()

**Symptom:** `AttributeError: 'NoneType' object has no attribute...`

**Solution:** Check if src() is None:

```python
async def handler(self, signal):
    src = signal.src()
    if src:  # Check before using
        await self.output(response, src)
```

---

## Next Steps

Congratulations! You've learned the fundamentals of PySDL. Here's what to explore next:

1. **Read the Examples**: See [examples.md](examples.md) for more complex applications

2. **Study the Architecture**: Understand the design in [architecture.md](architecture.md)

3. **Explore the API**: Complete reference in [api_reference.md](api_reference.md)

4. **Build Something**: Start with a small project:
   - Chat server with multiple clients
   - Job queue with workers
   - Game with multiple entities
   - Workflow engine

5. **Contribute**: Add features, fix bugs, improve docs

---

## Quick Reference Card

```python
# Creating a process
class MyProcess(SdlProcess):
    def _init_state_machine(self):
        self._event(state, SignalType, handler)
        self._done()

# Instantiating
system = SdlSystem()
process = await MyProcess.create(parent_pid, config_data, system=system)

# Sending signals
await self.output(signal, destination_pid)

# State transitions
await self.next_state(new_state)

# Starting timers
self.start_timer(timer, milliseconds)

# Stopping timers
self.stop_timer(timer)

# Stopping process
await self.stop()  # Graceful
self.stop_process()  # Immediate

# Stopping system
self._system.stop()  # From within a process

# Logging
SdlLogger.info("message")
SdlLogger.warning("message")

# Running system
async def main():
    system = SdlSystem()
    await MyProcess.create(None, system=system)
    await system.run()

asyncio.run(main())
```

---

Happy coding with PySDL!
