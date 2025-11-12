# PySDL Troubleshooting Guide

Common issues, solutions, debugging tips, and best practices for PySDL development.

## Table of Contents

1. [Common Issues](#common-issues)
2. [Debugging Tips](#debugging-tips)
3. [Performance Troubleshooting](#performance-troubleshooting)
4. [FAQ](#faq)
5. [Error Messages](#error-messages)
6. [Best Practices](#best-practices)

---

## Common Issues

### Issue: Handler Not Called

**Symptoms:**
- Signal is sent but handler doesn't execute
- No error messages
- Process seems unresponsive

**Causes and Solutions:**

#### 1. Not in the correct state

```python
# PROBLEM
class MyProcess(SdlProcess):
    state_a = SdlState("state_a")
    state_b = SdlState("state_b")

    def _init_state_machine(self):
        # Handler only registered for state_b
        self._event(self.state_b, MySignal, self.handler)
        self._done()

    async def start_handler(self, signal):
        # BUG: Transition to state_a, but handler is for state_b!
        await self.next_state(self.state_a)

# SOLUTION
async def start_handler(self, signal):
    # Transition to the correct state
    await self.next_state(self.state_b)
```

**Debug tip:** Log current state
```python
async def debugging_handler(self, signal):
    SdlLogger.info(f"Current state: {self.current_state().name()}")
```

#### 2. Always Call `_done()`

The `_done()` method should always be called at the end of `_init_state_machine()` to mark completion of the state machine setup. While not strictly enforced, it's a best practice for code clarity and consistency.

```python
# RECOMMENDED PATTERN
def _init_state_machine(self):
    self._event(start, SdlStartSignal, self.start_handler)
    self._event(self.state_idle, MySignal, self.idle_handler)
    self._done()  # Always call _done() to finalize FSM
```

**Note:** All documentation examples consistently use `_done()` and it should be considered part of the standard pattern.

#### 3. Wrong signal type

```python
# PROBLEM
self._event(self.state_idle, WrongSignal, self.handler)

# Signal sent
await self.output(CorrectSignal.create(), dst)  # Won't match!

# SOLUTION
self._event(self.state_idle, CorrectSignal, self.handler)
```

#### 4. Signal sent to wrong PID

```python
# PROBLEM
await self.output(signal, "wrong_pid")

# SOLUTION
# Verify PID is correct
SdlLogger.info(f"Sending to: {destination_pid}")
await self.output(signal, destination_pid)
```

---

### Issue: Process Never Starts

**Symptoms:**
- No log messages from process
- Process seems to not exist
- `SdlStartSignal` never handled

**Cause:** Direct instantiation instead of using `create()`

```python
# PROBLEM - Direct instantiation (process not registered)
class MyProcess(SdlProcess):
    def __init__(self, parent_pid, config_data=None, system=None):
        super().__init__(parent_pid, config_data, system=system)

process = MyProcess(parent_pid, config, system=system)  # Not registered!

# SOLUTION - Use create() method
system = SdlSystem()
process = await MyProcess.create(parent_pid, config, system=system)
```

**Why:** The `create()` method:
1. Calls `__init__()` to construct the process
2. Calls `_register()` to add to system
3. Initializes state machine
4. Sends `SdlStartSignal`

---

### Issue: TypeError - `__init__()` doesn't accept system= parameter

**Symptoms:**
```python
TypeError: __init__() got an unexpected keyword argument 'system'
```

**Cause:** Custom `__init__()` method missing the `system` parameter

**Problem:**
```python
# INCORRECT - Missing system parameter
class MyProcess(SdlProcess):
    def __init__(self, parent_pid, config_data=None):
        super().__init__(parent_pid, config_data, system=None)  # Won't work!
```

**Solution:**
```python
# CORRECT - Include system parameter with default None
class MyProcess(SdlProcess):
    def __init__(self, parent_pid, config_data=None, system=None):
        super().__init__(parent_pid, config_data, system=system)
        # Your custom initialization here
        self.my_custom_field = config_data
```

**Why:** The `create()` class method always passes `system=` as a keyword argument. Your `__init__()` must accept it, even if you just pass it to `super().__init__()`.

**Common patterns:**
```python
# Pattern 1: Simple process with config
def __init__(self, parent_pid, config_data=None, system=None):
    super().__init__(parent_pid, config_data, system=system)

# Pattern 2: Process with custom parameter
def __init__(self, parent_pid, peer_pid=None, system=None):
    super().__init__(parent_pid, system=system)
    self.peer_pid = peer_pid

# Pattern 3: Process with multiple custom parameters
def __init__(self, parent_pid, server_pid, request_id=None, system=None):
    super().__init__(parent_pid, system=system)
    self.server_pid = server_pid
    self.request_id = request_id
```

---

### Issue: Timer Never Fires

**Symptoms:**
- Timer started but handler never called
- No timer expiry

**Causes and Solutions:**

#### 1. Not in the correct state

```python
# PROBLEM
async def start_handler(self, signal):
    self.start_timer(MyTimer.create(), 5000)
    await self.next_state(self.state_wrong)  # BUG: No handler here!

def _init_state_machine(self):
    # Handler in state_waiting, but we transitioned to state_wrong
    self._event(self.state_waiting, MyTimer, self.timer_handler)

# SOLUTION
async def start_handler(self, signal):
    self.start_timer(MyTimer.create(), 5000)
    await self.next_state(self.state_waiting)  # Correct state
```

#### 2. Timer instance mismatch when stopping

```python
# PROBLEM
self.timer = MyTimer.create()
self.start_timer(self.timer, 5000)
# Later...
self.stop_timer(MyTimer.create())  # BUG: Different instance!

# SOLUTION
self.timer = MyTimer.create()
self.start_timer(self.timer, 5000)
# Later...
self.stop_timer(self.timer)  # Same instance
```

#### 3. Timer not registered in FSM

```python
# PROBLEM
def _init_state_machine(self):
    # BUG: Forgot to register timer handler
    self._event(start, SdlStartSignal, self.start_handler)
    self._done()

# SOLUTION
def _init_state_machine(self):
    self._event(start, SdlStartSignal, self.start_handler)
    self._event(self.state_waiting, MyTimer, self.timer_handler)  # Add this!
    self._done()
```

---

### Issue: AttributeError on `signal.src()`

**Symptoms:**
```python
AttributeError: 'NoneType' object has no attribute...
```

**Cause:** `signal.src()` returns `None` if source not set

**Solution:** Always check for None

```python
# PROBLEM
async def handler(self, signal):
    await self.output(response, signal.src())  # May be None!

# SOLUTION
async def handler(self, signal):
    src = signal.src()
    if src:  # Check before using
        await self.output(response, src)
    else:
        SdlLogger.warning("Signal has no source")
```

---

### Issue: System Doesn't Stop

**Symptoms:**
- `SdlSystem.stop()` called but program hangs
- Event loop continues running

**Causes and Solutions:**

#### 1. Not awaiting `SdlSystem.run()`

```python
# PROBLEM
async def main():
    system = SdlSystem()
    await MyProcess.create(None, system=system)
    system.run()  # BUG: Not awaited!

# SOLUTION
async def main():
    system = SdlSystem()
    await MyProcess.create(None, system=system)
    await system.run()  # Must await!
```

#### 2. Process doesn't call `SdlSystem.stop()`

```python
# PROBLEM
async def done_handler(self, signal):
    # BUG: Forgot to stop system
    pass

# SOLUTION
async def done_handler(self, signal):
    SdlLogger.info("Work complete, stopping system")
    self._system.stop()
```

---

### Issue: Import Errors

**Symptoms:**
```python
ModuleNotFoundError: No module named 'pysdl'
```

**Solutions:**

#### 1. Set PYTHONPATH

```bash
export PYTHONPATH=/path/to/async_sdl_python:$PYTHONPATH
```

#### 2. Install package

```bash
cd /path/to/async_sdl_python
pip install -e .
```

#### 3. Verify installation

```bash
python -c "import pysdl; print('Success')"
```

---

## Debugging Tips

### Enable Verbose Logging

PySDL automatically logs process creation, state transitions, and signal delivery.

**Check logs for:**
- `Created`: Process creation
- `State`: State transitions
- `SdlSig`: Signal delivery
- `SdlSig-NA`: Signal not delivered (no handler)

### Add Custom Logging

```python
from pysdl import SdlLogger

async def handler(self, signal):
    SdlLogger.info(f"Handler called with: {signal.data}")
    SdlLogger.info(f"Current state: {self.current_state().name()}")
    SdlLogger.info(f"Signal type: {signal.name()}")
```

### Inspect Process Registry

```python
# Check what processes are registered
SdlLogger.info(f"Registered processes: {list(self._system.proc_map.keys())}")
```

### Inspect Timer Map

```python
# Check active timers
SdlLogger.info(f"Active timers: {self._system.timer_map}")
```

### Verify State Machine

```python
def _init_state_machine(self):
    SdlLogger.info("Initializing state machine")
    self._event(start, SdlStartSignal, self.start_handler)
    SdlLogger.info("Registered start handler")
    self._event(self.state_idle, MySignal, self.idle_handler)
    SdlLogger.info("Registered idle handler")
    self._done()
    SdlLogger.info("State machine complete")
```

### Use Python Debugger

```python
async def handler(self, signal):
    import pdb; pdb.set_trace()  # Drop into debugger
    await self.output(response, signal.src())
```

### Check Signal Delivery

```python
async def output_wrapper(self, signal, dst):
    """Wrapper to debug signal sending."""
    SdlLogger.info(f"Sending {signal.name()} to {dst}")
    result = await self.output(signal, dst)
    SdlLogger.info(f"Send result: {result}")
    return result
```

---

## Performance Troubleshooting

### Issue: Slow Signal Processing

**Symptoms:**
- Signals take a long time to process
- System seems sluggish

**Causes and Solutions:**

#### 1. Blocking operations in handlers

```python
# PROBLEM
async def handler(self, signal):
    time.sleep(5)  # BUG: Blocks event loop!

# SOLUTION
async def handler(self, signal):
    await asyncio.sleep(5)  # Non-blocking
```

#### 2. CPU-intensive operations

```python
# PROBLEM
async def handler(self, signal):
    # CPU-intensive work blocks event loop
    result = heavy_computation()

# SOLUTION
async def handler(self, signal):
    # Delegate to executor or separate process
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, heavy_computation)
```

#### 3. Long-running handlers

```python
# PROBLEM
async def handler(self, signal):
    for i in range(1000000):
        # Long loop blocks other handlers
        process_item(i)

# SOLUTION
async def handler(self, signal):
    for i in range(1000000):
        process_item(i)
        if i % 1000 == 0:
            await asyncio.sleep(0)  # Yield periodically
```

---

### Issue: High Memory Usage

**Causes and Solutions:**

#### 1. Not stopping processes

```python
# PROBLEM
async def create_temporary_process(self):
    temp = await TempProcess.create(self.pid())
    # BUG: Never stopped, accumulates in proc_map

# SOLUTION
async def create_temporary_process(self):
    temp = await TempProcess.create(self.pid())
    # Stop when done
    await temp.stop()
```

#### 2. Orphaned timers

```python
# PROBLEM
self.start_timer(MyTimer.create(), 5000)
# BUG: Process stops but timer remains in timer_map

# SOLUTION
# Timers automatically cleaned up when process unregisters
# But explicitly stop if needed:
self.stop_timer(self.my_timer)
await self.stop()
```

#### 3. Large signal queues

**Solution:** Ensure processes are responsive and handle signals promptly.

---

### Issue: Timer Drift

**Symptoms:**
- Timers expire later than expected
- Increasing inaccuracy over time

**Causes:**
- Event loop iterations take time
- Handlers block event loop

**Solutions:**

1. **Keep handlers fast:** Don't block in handlers
2. **Use short timer intervals:** More accurate for short durations
3. **Yield regularly:** Use `await asyncio.sleep(0)` in loops

---

## FAQ

### Q: Can I use threading with PySDL?

**A:** PySDL is designed for asyncio, not threading. All operations should be async. If you need threading for CPU-bound work, use `loop.run_in_executor()`.

```python
async def handler(self, signal):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, cpu_bound_function)
```

---

### Q: How do I share data between processes?

**A:** Don't share mutable state. Use signals to communicate.

```python
# WRONG: Shared mutable state
class GlobalData:
    counter = 0  # Don't do this!

# RIGHT: Message passing
class CounterSignal(SdlSignal):
    pass

async def handler(self, signal):
    self.counter += 1  # Process-local state
    await self.output(CounterSignal.create(data=self.counter), other_pid)
```

---

### Q: Can I have multiple SdlSystem instances?

**A:** Yes, in v1.0.0+. `SdlSystem` is now instance-based.

```python
# Create multiple independent systems
system1 = SdlSystem()
system2 = SdlSystem()

# Each has its own processes, timers, etc.
await Process1.create(None, system=system1)
await Process2.create(None, system=system2)

# Run them independently
await asyncio.gather(system1.run(), system2.run())
```

---

### Q: How do I test PySDL processes?

**A:** Create test processes with isolated system instances, send signals, verify state transitions.

```python
import pytest
from pysdl import SdlSystem

@pytest.fixture
def sdl_system():
    return SdlSystem()

@pytest.mark.asyncio
async def test_my_process(sdl_system):
    # Create process with system instance
    process = await MyProcess.create(None, system=sdl_system)

    # Send signal
    await process.input(MySignal.create())

    # Verify state
    assert process.current_state().name() == "expected_state"

    # Clean up (optional - each test gets fresh system)
    sdl_system.unregister(process)
```

---

### Q: How do I implement request-response pattern?

**A:** Use correlation IDs in signal data.

```python
class Request(SdlSignal):
    pass

class Response(SdlSignal):
    pass

# Client
async def send_request(self):
    request_id = generate_unique_id()
    request = Request.create(data={"req_id": request_id})
    await self.output(request, server_pid)
    self.pending_requests[request_id] = time()

async def handle_response(self, signal):
    req_id = signal.data.get("req_id")
    if req_id in self.pending_requests:
        # Match response to request
        del self.pending_requests[req_id]
```

---

### Q: Can I modify a signal after sending it?

**A:** Don't. Treat signals as immutable once sent.

```python
# WRONG
signal = MySignal.create(data={"count": 1})
await self.output(signal, pid1)
signal.data["count"] = 2  # Don't modify!
await self.output(signal, pid2)

# RIGHT
await self.output(MySignal.create(data={"count": 1}), pid1)
await self.output(MySignal.create(data={"count": 2}), pid2)
```

---

### Q: How do I handle errors in handlers?

**A:** Use try-except blocks.

```python
async def handler(self, signal):
    try:
        result = await risky_operation()
    except ValueError as e:
        SdlLogger.warning(f"Error: {e}")
        await self.output(ErrorSignal.create(), signal.src())
    except Exception as e:
        SdlLogger.warning(f"Unexpected error: {e}")
        await self.stop()
```

---

## Error Messages

PySDL raises specific exceptions defined in `pysdl/exceptions.py`. All exceptions inherit from `SdlError`.

### ValidationError: "Process creation requires a system instance"

**Meaning:** Attempted to create a process without providing a `SdlSystem` instance

**Solution:** Always pass `system=` parameter when creating processes

```python
# WRONG
process = await MyProcess.create(parent_pid, config)

# RIGHT
system = SdlSystem()
process = await MyProcess.create(parent_pid, config, system=system)
```

---

### ValidationError: "signal must be an instance of SdlSignal"

**Meaning:** Tried to send something that's not a signal

**Solution:** Only send SdlSignal instances

```python
# WRONG
await self.output("message", pid)
await self.output({"data": "value"}, pid)

# RIGHT
await self.output(MessageSignal.create(data="message"), pid)
```

---

### ProcessNotFoundError

**Meaning:** Attempted to send a signal to a process that doesn't exist in the registry

**Causes:**
- Process was never created
- Process was stopped/unregistered
- Wrong PID used

**Solution:**
```python
# Check if process exists before sending
if dst_pid in self._system.proc_map:
    await self.output(signal, dst_pid)
else:
    SdlLogger.warning(f"Process {dst_pid} not found")
```

---

### SignalDeliveryError

**Meaning:** Signal failed to be delivered to the destination process

**Causes:**
- Process doesn't exist
- Queue error
- System issue

**Solution:**
- Verify destination PID is correct
- Check process is running
- Review logs for specific error details

---

### StateTransitionError

**Meaning:** Invalid state transition attempted or no handler defined for signal in current state

**Example error message:**
```
Invalid state transition: no handler for signal 'MySignal' in state 'idle'
```

**Solution:**
```python
# Option 1: Register handler for current state
def _init_state_machine(self):
    self._event(self.state_idle, MySignal, self.handler)

# Option 2: Transition to correct state first
async def start_handler(self, signal):
    await self.next_state(self.state_ready)  # State with handler
```

---

### TimerError: "Timer {timer} was not active"

**Meaning:** Attempted to stop a timer that isn't running

**Causes:**
- Timer already expired
- Timer was never started
- Wrong timer instance used

**Solution:**
```python
# Keep reference to timer instance
self.my_timer = MyTimer.create()
self.start_timer(self.my_timer, 5000)

# Stop using same instance
self.stop_timer(self.my_timer)  # Must be same instance!
```

---

### Log Message: "SdlSig-NA"

**Meaning:** Signal Not Acknowledged - signal delivered but no handler found

**This is a log message (not an exception) that appears when:**
- Signal sent to non-existent process
- Process exists but has no handler for signal in current state
- Signal type not registered in FSM

**Solution:**
1. Check destination PID exists
2. Verify process is in correct state for the signal
3. Verify handler is registered in `_init_state_machine()`

```python
# Debugging SdlSig-NA issues
async def handler(self, signal):
    SdlLogger.info(f"Current state: {self.current_state().name()}")
    SdlLogger.info(f"Sending {signal.name()} to {dst_pid}")
    await self.output(signal, dst_pid)
    # Check logs for SdlSig-NA message
```

---

### TypeError: `__init__()` got an unexpected keyword argument 'system'

**Meaning:** Custom `__init__()` doesn't accept required `system=` parameter

**Solution:** See [Issue: TypeError - __init__() doesn't accept system= parameter](#issue-typeerror---__init__-doesnt-accept-system-parameter)

---

## Best Practices

### 1. Always Use `create()` for Processes

```python
# CORRECT
system = SdlSystem()
process = await MyProcess.create(parent_pid, config, system=system)

# INCORRECT
process = MyProcess(parent_pid, config, system=system)  # Not registered!
```

---

### 2. Check for None in Signal Sources

```python
async def handler(self, signal):
    src = signal.src()
    if src:
        await self.output(response, src)
```

---

### 3. Name Handlers Descriptively

```python
# GOOD
async def idle_timeout_handler(self, signal):
    ...

# BAD
async def handler1(self, signal):
    ...
```

---

### 4. Keep Handlers Fast

```python
# GOOD
async def handler(self, signal):
    self.data = signal.data
    await self.next_state(self.state_done)

# BAD
async def handler(self, signal):
    time.sleep(10)  # Blocks event loop!
```

---

### 5. Use Type Hints

```python
# GOOD
async def handler(self, signal: SdlSignal) -> None:
    ...

# OK
async def handler(self, signal):
    ...
```

---

### 6. Log State Transitions

State transitions are automatically logged, but you can add context:

```python
async def handler(self, signal):
    SdlLogger.info(f"Processing {signal.data}")
    await self.next_state(self.state_processing)
```

---

### 7. Clean Up Resources

```python
async def stopping_handler(self, signal):
    # Clean up before stopping
    if hasattr(self, 'connection'):
        self.connection.close()
    self.stop_process()
```

---

### 8. Use Singleton for Services

```python
# Database, config, resource pools
class DatabaseService(SdlSingletonProcess):
    ...
```

---

### 9. Validate Signal Data

```python
async def handler(self, signal):
    if not signal.data or "required_field" not in signal.data:
        SdlLogger.warning("Invalid signal data")
        return

    # Process signal
    ...
```

---

### 10. Document State Machines

```python
def _init_state_machine(self):
    """
    State Machine:
      start: Initial state, transitions to idle
      idle: Waiting for work, transitions to working
      working: Processing work, transitions to idle or error
      error: Error state, transitions to idle after recovery
    """
    self._event(start, SdlStartSignal, self.start_handler)
    self._event(self.state_idle, WorkSignal, self.idle_work)
    # ...
    self._done()
```

---

## Getting Help

If you're still stuck:

1. **Check logs**: Enable verbose logging
2. **Read docs**: [API Reference](api_reference.md), [Architecture](architecture.md)
3. **Review examples**: [Examples](examples.md)
4. **File an issue**: Report bugs on GitHub
5. **Ask questions**: Use project discussions or issues

---

## Summary

Common issues:
- Handler not called → Check state and FSM registration
- Process not starting → Use `create()` not `__init__()`
- Timer not firing → Verify state and handler registration
- Performance issues → Avoid blocking, use async operations

Key debugging tools:
- SdlLogger for verbose logging
- Check proc_map and timer_map
- Use Python debugger
- Add custom logging

Best practices:
- Use factory methods
- Check for None
- Keep handlers fast
- Clean up resources
- Use type hints

For more information, see:
- [API Reference](api_reference.md)
- [Getting Started](getting_started.md)
- [Examples](examples.md)
