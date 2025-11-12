# PySDL Examples

This document provides comprehensive examples demonstrating PySDL's features and common patterns.

## Table of Contents

1. [Ping-Pong Example](#ping-pong-example)
2. [Simple State Machine](#simple-state-machine)
3. [Timer-Based Workflow](#timer-based-workflow)
4. [Hierarchical Processes](#hierarchical-processes)
5. [Singleton Service](#singleton-service)
6. [Request-Response Pattern](#request-response-pattern)
7. [Emergency Stop with Star State](#emergency-stop-with-star-state)

---

## Ping-Pong Example

A classic example demonstrating two processes sending signals back and forth.

### Code

```python
import asyncio
from typing import Optional, Any
from pysdl import (
    SdlProcess, SdlSignal, SdlState, SdlSystem,
    SdlStartSignal, SdlStoppingSignal, SdlLogger
)
from pysdl.state import start


class PingPongProcess(SdlProcess):
    """Ping pong process: sends ping/pong signals between peers."""

    class PingSignal(SdlSignal):
        def dumpdata(self) -> Optional[str]:
            return "Ping"

    class PongSignal(SdlSignal):
        def dumpdata(self) -> Optional[str]:
            return "Pong"

    class StopSignal(SdlSignal):
        pass

    state_wait_ping = SdlState("wait_ping")
    state_wait_pong = SdlState("wait_pong")
    state_wait_stopping = SdlState("wait_stopping")

    _count: int = 0

    def __init__(self, parent_pid: Optional[str], config_data: Optional[Any] = None, system=None):
        super().__init__(parent_pid, config_data, system=system)
        self.peer_pid = config_data.get("peer_pid") if config_data else None

    async def start_StartTransition(self, signal: SdlSignal) -> None:
        """If peer exists, send ping and wait for pong, otherwise wait for ping."""
        if self.peer_pid is not None:
            await self.output(self.PingSignal.create(), self.peer_pid)
            await self.next_state(self.state_wait_pong)
        else:
            await self.next_state(self.state_wait_ping)

    async def wait_pong_PongSignal(self, signal: SdlSignal) -> None:
        """Received pong, send ping back."""
        src = signal.src()
        if src is not None:
            await self.output(self.PingSignal.create(), src)

    async def wait_ping_PingSignal(self, signal: SdlSignal) -> None:
        """Received ping, send pong back (or stop after 20)."""
        self._count += 1
        src = signal.src()
        if src is not None:
            if self._count == 20:
                # Stop after 20 pings
                await self.output(self.StopSignal.create(), src)
                await self.stop()
                await self.next_state(self.state_wait_stopping)
            else:
                await self.output(self.PongSignal.create(), src)

    async def wait_pong_StopSignal(self, signal: SdlSignal) -> None:
        """Received stop signal."""
        await self.stop()
        await self.next_state(self.state_wait_stopping)

    async def wait_stopping(self, signal: SdlSignal) -> None:
        """Handle stopping signal."""
        self.stop_process()
        self._system.stop()

    def _init_state_machine(self) -> None:
        self._event(start, SdlStartSignal, self.start_StartTransition)
        self._event(self.state_wait_ping, self.PingSignal, self.wait_ping_PingSignal)
        self._event(self.state_wait_pong, self.PongSignal, self.wait_pong_PongSignal)
        self._event(self.state_wait_pong, self.StopSignal, self.wait_pong_StopSignal)
        self._event(self.state_wait_stopping, SdlStoppingSignal, self.wait_stopping)
        self._done()


async def main():
    """Create two ping-pong processes."""
    # Create system instance
    system = SdlSystem()

    # Create processes with system
    p1 = await PingPongProcess.create(None, None, system=system)
    p2 = await PingPongProcess.create(None, {"peer_pid": p1.pid()}, system=system)

    # Run the system
    await system.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### What It Demonstrates

- **Bidirectional communication**: Processes sending signals back and forth
- **Counter state**: Tracking interactions (_count)
- **Termination**: Stopping processes after N iterations
- **Peer references**: Storing PIDs for communication

---

## Simple State Machine

A traffic light demonstrating state-dependent behavior.

### Code

```python
import asyncio
from pysdl import (
    SdlProcess, SdlSignal, SdlState, SdlTimer,
    SdlSystem, SdlStartSignal, SdlLogger
)
from pysdl.state import start


class TrafficLight(SdlProcess):
    """Traffic light cycling through Red -> Green -> Yellow -> Red."""

    class AutoTimer(SdlTimer):
        """Timer for automatic state changes."""
        pass

    state_red = SdlState("red")
    state_yellow = SdlState("yellow")
    state_green = SdlState("green")

    async def start_handler(self, signal):
        """Initialize to red."""
        SdlLogger.info("🔴 RED LIGHT")
        # Start 5-second timer
        self.start_timer(self.AutoTimer.create(), 5000)
        await self.next_state(self.state_red)

    async def red_timer(self, signal):
        """Red -> Green."""
        SdlLogger.info("🟢 GREEN LIGHT")
        self.start_timer(self.AutoTimer.create(), 5000)
        await self.next_state(self.state_green)

    async def green_timer(self, signal):
        """Green -> Yellow."""
        SdlLogger.info("🟡 YELLOW LIGHT")
        self.start_timer(self.AutoTimer.create(), 2000)  # Shorter yellow
        await self.next_state(self.state_yellow)

    async def yellow_timer(self, signal):
        """Yellow -> Red."""
        SdlLogger.info("🔴 RED LIGHT")
        self.start_timer(self.AutoTimer.create(), 5000)
        await self.next_state(self.state_red)

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_red, self.AutoTimer, self.red_timer)
        self._event(self.state_green, self.AutoTimer, self.green_timer)
        self._event(self.state_yellow, self.AutoTimer, self.yellow_timer)
        self._done()


async def main():
    """Run traffic light for 30 seconds."""
    # Create system instance
    system = SdlSystem()

    # Create traffic light
    light = await TrafficLight.create(None, system=system)

    # Run for 30 seconds then stop
    await asyncio.sleep(30)
    system.stop()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()
    loop.close()
```

### What It Demonstrates

- **Cyclic states**: Transitions forming a cycle
- **Automatic timers**: Self-triggering state changes
- **Different timer durations**: Yellow light is shorter
- **Emojis in logs**: Visual representation (optional)

---

## Timer-Based Workflow

A coffee maker with multiple timed stages.

### Code

```python
import asyncio
from pysdl import (
    SdlProcess, SdlSignal, SdlState, SdlTimer,
    SdlSystem, SdlStartSignal, SdlLogger
)
from pysdl.state import start


class CoffeeMaker(SdlProcess):
    """Multi-stage coffee brewing process."""

    class HeatingTimer(SdlTimer):
        """Water heating timer."""
        pass

    class BrewingTimer(SdlTimer):
        """Coffee brewing timer."""
        pass

    class WarmerTimer(SdlTimer):
        """Keep warm timer."""
        pass

    class BrewRequest(SdlSignal):
        """Request to brew coffee."""
        pass

    state_idle = SdlState("idle")
    state_heating = SdlState("heating")
    state_brewing = SdlState("brewing")
    state_ready = SdlState("ready")

    async def start_handler(self, signal):
        """Coffee maker initialized."""
        SdlLogger.info("☕ Coffee Maker Ready")
        await self.next_state(self.state_idle)

    async def idle_brew_request(self, signal):
        """Start brewing process."""
        SdlLogger.info("🌡️  Heating water...")
        self.start_timer(self.HeatingTimer.create(), 3000)  # 3 seconds
        await self.next_state(self.state_heating)

    async def heating_timer(self, signal):
        """Water heated, start brewing."""
        SdlLogger.info("💧 Brewing coffee...")
        self.start_timer(self.BrewingTimer.create(), 5000)  # 5 seconds
        await self.next_state(self.state_brewing)

    async def brewing_timer(self, signal):
        """Coffee ready, keep warm."""
        SdlLogger.info("✅ Coffee ready!")
        self.start_timer(self.WarmerTimer.create(), 10000)  # Keep warm 10s
        await self.next_state(self.state_ready)

    async def ready_warmer_timer(self, signal):
        """Coffee cooled down."""
        SdlLogger.info("❄️  Coffee cooled, discarding")
        await self.next_state(self.state_idle)
        self._system.stop()

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_idle, self.BrewRequest, self.idle_brew_request)
        self._event(self.state_heating, self.HeatingTimer, self.heating_timer)
        self._event(self.state_brewing, self.BrewingTimer, self.brewing_timer)
        self._event(self.state_ready, self.WarmerTimer, self.ready_warmer_timer)
        self._done()


async def main():
    """Test coffee maker."""
    # Create system instance
    system = SdlSystem()

    # Create coffee maker
    coffee_maker = await CoffeeMaker.create(None, system=system)

    # Wait a moment then request brew
    await asyncio.sleep(1)
    await coffee_maker.input(CoffeeMaker.BrewRequest.create())

    # Run the system
    await system.run()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()
    loop.close()
```

### What It Demonstrates

- **Multi-stage workflow**: Sequential states with timers
- **Multiple timer types**: Different timers for each stage
- **Timer chaining**: Each timer triggers the next stage
- **Realistic timing**: Different durations for each stage

---

## Hierarchical Processes

Supervisor managing multiple worker processes.

### Code

```python
import asyncio
from typing import Optional, Any
from pysdl import (
    SdlProcess, SdlSignal, SdlState, SdlTimer,
    SdlSystem, SdlStartSignal, SdlLogger,
    SdlChildrenManager
)
from pysdl.state import start


class WorkSignal(SdlSignal):
    """Work assignment signal."""
    pass


class WorkDoneSignal(SdlSignal):
    """Work completion signal."""
    pass


class WorkerProcess(SdlProcess):
    """Worker process that performs work."""

    class WorkTimer(SdlTimer):
        """Simulates work duration."""
        pass

    state_idle = SdlState("idle")
    state_working = SdlState("working")

    async def start_handler(self, signal):
        """Worker ready."""
        SdlLogger.info(f"👷 Worker {self.pid()} ready")
        await self.next_state(self.state_idle)

    async def idle_work(self, signal):
        """Perform work."""
        SdlLogger.info(f"⚙️  Worker {self.pid()} working...")
        # Simulate work with 2-second timer
        self.start_timer(self.WorkTimer.create(), 2000)
        await self.next_state(self.state_working)

    async def working_timer(self, signal):
        """Work complete, notify supervisor."""
        SdlLogger.info(f"✅ Worker {self.pid()} done")
        parent = self.get_parent()
        if parent:
            await self.output(WorkDoneSignal.create(), parent)
        await self.next_state(self.state_idle)

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_idle, WorkSignal, self.idle_work)
        self._event(self.state_working, self.WorkTimer, self.working_timer)
        self._done()


class SupervisorProcess(SdlProcess):
    """Supervisor managing worker pool."""

    state_managing = SdlState("managing")

    def __init__(self, parent_pid: Optional[str], config_data: Optional[Any] = None, system=None):
        super().__init__(parent_pid, config_data, system=system)
        self.children = SdlChildrenManager()
        self.work_items = 10  # Total work to distribute
        self.work_completed = 0

    async def start_handler(self, signal):
        """Create worker pool."""
        SdlLogger.info("👔 Supervisor creating worker pool")

        # Create 3 workers
        for i in range(3):
            worker = await WorkerProcess.create(self.pid(), system=self._system)
            self.children.register(worker, worker_id=i, status="idle")
            SdlLogger.info(f"   Created worker {i}")

        await self.next_state(self.state_managing)

        # Distribute initial work
        await self.distribute_work()

    async def distribute_work(self):
        """Assign work to idle workers."""
        idle_workers = self.children.get_child_list_with_keys(status="idle")

        for worker in idle_workers:
            if self.work_items > 0:
                SdlLogger.info(f"📋 Assigning work to {worker['pid']}")
                await self.output(WorkSignal.create(), worker["pid"])
                self.children.set_keys_by_pid(worker["pid"], status="busy")
                self.work_items -= 1

    async def managing_work_done(self, signal):
        """Handle work completion."""
        self.work_completed += 1
        worker_pid = signal.src()

        SdlLogger.info(f"📊 Progress: {self.work_completed} completed, {self.work_items} remaining")

        # Mark worker as idle
        if worker_pid:
            self.children.set_keys_by_pid(worker_pid, status="idle")

        # Assign more work if available
        if self.work_items > 0:
            await self.distribute_work()
        elif self.work_completed >= 10:  # All work done
            SdlLogger.info("🎉 All work completed!")
            self._system.stop()

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_managing, WorkDoneSignal, self.managing_work_done)
        self._done()


async def main():
    """Run supervisor with workers."""
    # Create system instance
    system = SdlSystem()

    # Create supervisor
    await SupervisorProcess.create(None, None, system=system)

    # Run the system
    await system.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### What It Demonstrates

- **Parent-child relationships**: Workers created by supervisor
- **SdlChildrenManager**: Tracking children with metadata
- **Work distribution**: Dynamic work assignment
- **Status tracking**: Marking workers as idle/busy
- **Completion detection**: Stopping when all work done

---

## Singleton Service

Database connection pool as a singleton.

### Code

```python
import asyncio
from typing import Optional, Any
from pysdl import (
    SdlSingletonProcess, SdlProcess, SdlSignal, SdlState,
    SdlSystem, SdlStartSignal, SdlLogger, SdlRegistry
)
from pysdl.state import start


class QuerySignal(SdlSignal):
    """Database query signal."""
    pass


class ResultSignal(SdlSignal):
    """Query result signal."""
    pass


class DatabaseService(SdlSingletonProcess):
    """Singleton database service."""

    state_connected = SdlState("connected")

    async def start_handler(self, signal):
        """Connect to database."""
        SdlLogger.info("💾 Database Service: Connecting...")
        # Simulate connection
        self.connection = "DB_CONNECTION_HANDLE"
        SdlLogger.info("💾 Database Service: Connected!")

        # Register in name registry
        registry = SdlRegistry()
        registry.add("database", self.pid())

        await self.next_state(self.state_connected)

    async def connected_query(self, signal):
        """Handle query."""
        query = signal.data
        SdlLogger.info(f"💾 Database Service: Executing query: {query}")

        # Simulate query execution
        result = f"Result for: {query}"

        # Send result back
        src = signal.src()
        if src:
            response = ResultSignal.create(result)
            await self.output(response, src)

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_connected, QuerySignal, self.connected_query)
        self._done()


class ClientProcess(SdlProcess):
    """Client using database service."""

    state_waiting = SdlState("waiting")

    def __init__(self, parent_pid: Optional[str], config_data: Optional[Any] = None, system=None):
        super().__init__(parent_pid, config_data, system=system)
        self.client_id = config_data

    async def start_handler(self, signal):
        """Send query to database."""
        # Look up database service
        registry = SdlRegistry()
        db_pid = registry.get("database")

        if db_pid:
            SdlLogger.info(f"🔍 Client {self.client_id}: Sending query")
            query = QuerySignal.create(f"SELECT * FROM users WHERE id={self.client_id}")
            await self.output(query, db_pid)
            await self.next_state(self.state_waiting)
        else:
            SdlLogger.warning(f"❌ Client {self.client_id}: Database not found")

    async def waiting_result(self, signal):
        """Handle query result."""
        result = signal.data
        SdlLogger.info(f"📧 Client {self.client_id}: Received: {result}")

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_waiting, ResultSignal, self.waiting_result)
        self._done()


async def main():
    """Test singleton database service."""
    # Create system instance
    system = SdlSystem()

    # Create database service (singleton)
    db1 = await DatabaseService.create(None, system=system)

    # Try to create again (returns same instance)
    db2 = await DatabaseService.create(None, system=system)
    SdlLogger.info(f"Singleton check: {db1.pid() == db2.pid()}")  # True

    # Create multiple clients
    await ClientProcess.create(None, 1, system=system)
    await ClientProcess.create(None, 2, system=system)
    await ClientProcess.create(None, 3, system=system)

    # Run for a bit
    await asyncio.sleep(2)
    system.stop()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()
    loop.close()
```

### What It Demonstrates

- **Singleton pattern**: Only one database instance
- **SdlRegistry**: Name-based process lookup
- **Service pattern**: Centralized resource
- **Multiple clients**: Many processes using one service
- **Request-response**: Query and result signals

---

## Request-Response Pattern

Client-server with request correlation.

### Code

```python
import asyncio
import random
from typing import Optional, Any
from pysdl import (
    SdlProcess, SdlSignal, SdlState, SdlTimer,
    SdlSystem, SdlStartSignal, SdlLogger
)
from pysdl.state import start


class RequestSignal(SdlSignal):
    """Request with correlation ID."""
    pass


class ResponseSignal(SdlSignal):
    """Response with correlation ID."""
    pass


class ServerProcess(SdlProcess):
    """Server handling requests."""

    class ProcessingTimer(SdlTimer):
        """Simulates processing time."""
        pass

    state_idle = SdlState("idle")
    state_processing = SdlState("processing")

    def __init__(self, parent_pid: Optional[str], config_data: Optional[Any] = None, system=None):
        super().__init__(parent_pid, config_data, system=system)
        self.current_request = None

    async def start_handler(self, signal):
        """Server ready."""
        SdlLogger.info("🖥️  Server ready")
        await self.next_state(self.state_idle)

    async def idle_request(self, signal):
        """Handle incoming request."""
        request_id = signal.data.get("request_id")
        SdlLogger.info(f"🖥️  Server: Processing request {request_id}")

        # Save request info
        self.current_request = {
            "request_id": request_id,
            "client_pid": signal.src()
        }

        # Simulate processing with timer
        processing_time = random.randint(1000, 3000)
        self.start_timer(self.ProcessingTimer.create(), processing_time)
        await self.next_state(self.state_processing)

    async def processing_timer(self, signal):
        """Processing complete, send response."""
        if self.current_request:
            request_id = self.current_request["request_id"]
            client_pid = self.current_request["client_pid"]

            SdlLogger.info(f"🖥️  Server: Responding to request {request_id}")

            response = ResponseSignal.create({
                "request_id": request_id,
                "result": f"Result for request {request_id}"
            })

            if client_pid:
                await self.output(response, client_pid)

        await self.next_state(self.state_idle)

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_idle, RequestSignal, self.idle_request)
        self._event(self.state_processing, self.ProcessingTimer, self.processing_timer)
        self._done()


class ClientProcess(SdlProcess):
    """Client sending requests."""

    class TimeoutTimer(SdlTimer):
        """Request timeout."""
        pass

    state_waiting = SdlState("waiting")

    def __init__(self, parent_pid: Optional[str], config_data: Optional[Any] = None, system=None):
        super().__init__(parent_pid, config_data, system=system)
        self.server_pid = config_data.get("server_pid") if config_data else None
        self.request_id = random.randint(1000, 9999)

    async def start_handler(self, signal):
        """Send request to server."""
        SdlLogger.info(f"📱 Client: Sending request {self.request_id}")

        request = RequestSignal.create({"request_id": self.request_id})
        await self.output(request, self.server_pid)

        # Start timeout timer
        self.start_timer(self.TimeoutTimer.create(), 5000)
        await self.next_state(self.state_waiting)

    async def waiting_response(self, signal):
        """Handle response."""
        response_data = signal.data
        request_id = response_data.get("request_id")
        result = response_data.get("result")

        if request_id == self.request_id:
            SdlLogger.info(f"📱 Client: Received response: {result}")
            # Stop timeout timer (would need to save timer reference)
        else:
            SdlLogger.warning(f"📱 Client: Wrong request ID: {request_id}")

    async def waiting_timeout(self, signal):
        """Handle timeout."""
        SdlLogger.warning(f"📱 Client: Request {self.request_id} timed out!")

    def _init_state_machine(self):
        self._event(start, SdlStartSignal, self.start_handler)
        self._event(self.state_waiting, ResponseSignal, self.waiting_response)
        self._event(self.state_waiting, self.TimeoutTimer, self.waiting_timeout)
        self._done()


async def main():
    """Test request-response pattern."""
    # Create system instance
    system = SdlSystem()

    # Create server
    server = await ServerProcess.create(None, None, system=system)

    # Create multiple clients
    await ClientProcess.create(None, {"server_pid": server.pid()}, system=system)
    await ClientProcess.create(None, {"server_pid": server.pid()}, system=system)
    await ClientProcess.create(None, {"server_pid": server.pid()}, system=system)

    # Run for 10 seconds
    await asyncio.sleep(10)
    system.stop()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()
    loop.close()
```

### What It Demonstrates

- **Request correlation**: Matching responses to requests via ID
- **Timeout handling**: Client-side timeout for requests
- **Simulated processing**: Random processing times
- **Multiple concurrent requests**: Several clients

---

## Emergency Stop with Star State

This example shows how to use star state handlers for safety-critical operations.

```python
import asyncio
from pysdl.process import SdlProcess
from pysdl.signal import SdlSignal
from pysdl.state import SdlState, star, start
from pysdl.system import SdlSystem
from pysdl.system_signals import SdlStartSignal


class EmergencyStopSignal(SdlSignal):
    """Emergency stop signal."""
    pass


class StartWorkSignal(SdlSignal):
    """Start working signal."""
    pass


class MotorController(SdlProcess):
    """Motor controller with emergency stop from any state."""

    state_idle = SdlState("idle")
    state_running = SdlState("running")
    state_stopping = SdlState("stopping")

    def _init_state_machine(self):
        # Star state: emergency stop works from ANY state
        self._event(star, EmergencyStopSignal, self.emergency_stop)

        # Normal state transitions
        self._event(start, SdlStartSignal, self.start_StartTransition)
        self._event(self.state_idle, StartWorkSignal, self.start_work)

        self._done()

    async def start_StartTransition(self, signal):
        """Initial transition to idle."""
        await self.next_state(self.state_idle)

    async def start_work(self, signal):
        """Start the motor."""
        print("Motor starting...")
        await self.next_state(self.state_running)

    async def emergency_stop(self, signal):
        """Emergency stop - works from ANY state!"""
        print(f"EMERGENCY STOP from state: {self.current_state()}")
        await self.next_state(self.state_stopping)
        # Perform emergency shutdown procedures
        self._system.stop()


async def main():
    # Create system
    system = SdlSystem()

    # Create motor controller
    motor = await MotorController.create(None, system=system)

    # Start working
    start_signal = StartWorkSignal.create()
    start_signal.set_dst(motor.pid())
    await system.output(start_signal)

    # Emergency stop (works from any state!)
    emergency = EmergencyStopSignal.create()
    emergency.set_dst(motor.pid())
    await system.output(emergency)

    # Run system
    await system.run()
    print("System stopped safely")


if __name__ == "__main__":
    asyncio.run(main())
```

**Output**:
```
Motor starting...
EMERGENCY STOP from state: running
System stopped safely
```

Key features:
- Emergency stop handler registered with `star` state
- Works from idle, running, or any other state
- Safety-critical operations guaranteed to execute
- Clean separation between normal flow and emergency handling

### What It Demonstrates

- **Star state matching**: Handler works regardless of current state
- **Safety-critical patterns**: Emergency operations that must always work
- **Priority matching**: Star handlers have lower priority than exact matches
- **Real-world use case**: Industrial control system safety

---

## Summary

These examples demonstrate:

- Process communication patterns
- State machine design
- Timer usage
- Process hierarchies
- Singleton services
- Request-response patterns
- Star wildcard matching
- Real-world scenarios

For more information:
- **API Reference**: [api_reference.md](api_reference.md)
- **Architecture**: [architecture.md](architecture.md)
- **Tutorial**: [getting_started.md](getting_started.md)
