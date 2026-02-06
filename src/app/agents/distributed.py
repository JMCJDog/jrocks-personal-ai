"""Distributed Execution Support - Task queues for horizontal scaling.

Provides infrastructure for distributing agent workloads across
multiple workers, enabling horizontal scaling of the multi-agent swarm.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import uuid
import json
import time


class TaskPriority(Enum):
    """Priority levels for queued tasks."""
    
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskState(Enum):
    """State of a queued task."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class QueuedTask:
    """A task in the distributed queue."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    payload: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    state: TaskState = TaskState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "payload": self.payload,
            "priority": self.priority.value,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "worker_id": self.worker_id,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "QueuedTask":
        """Create from dictionary."""
        task = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            payload=data.get("payload", {}),
            priority=TaskPriority(data.get("priority", 1)),
            state=TaskState(data.get("state", "pending")),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            result=data.get("result"),
            error=data.get("error"),
            worker_id=data.get("worker_id"),
            metadata=data.get("metadata", {}),
        )
        
        if data.get("created_at"):
            task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        
        return task


class TaskQueue(ABC):
    """Abstract base class for task queues."""
    
    @abstractmethod
    async def enqueue(self, task: QueuedTask) -> bool:
        """Add a task to the queue."""
        pass
    
    @abstractmethod
    async def dequeue(self, worker_id: str) -> Optional[QueuedTask]:
        """Get the next task for processing."""
        pass
    
    @abstractmethod
    async def complete(self, task_id: str, result: Any) -> bool:
        """Mark a task as completed."""
        pass
    
    @abstractmethod
    async def fail(self, task_id: str, error: str) -> bool:
        """Mark a task as failed."""
        pass
    
    @abstractmethod
    async def get_status(self, task_id: str) -> Optional[QueuedTask]:
        """Get the status of a task."""
        pass
    
    @abstractmethod
    async def get_pending_count(self) -> int:
        """Get the number of pending tasks."""
        pass


class InMemoryTaskQueue(TaskQueue):
    """In-memory task queue implementation.
    
    Good for development and single-instance deployments.
    For production, use Redis-backed implementation.
    
    Example:
        >>> queue = InMemoryTaskQueue()
        >>> task = QueuedTask(name="process", payload={"data": "..."})
        >>> await queue.enqueue(task)
        >>> next_task = await queue.dequeue("worker-1")
    """
    
    def __init__(self):
        """Initialize the queue."""
        self._pending: list[QueuedTask] = []
        self._processing: dict[str, QueuedTask] = {}
        self._completed: dict[str, QueuedTask] = {}
        self._lock = asyncio.Lock()
    
    async def enqueue(self, task: QueuedTask) -> bool:
        """Add a task to the queue."""
        async with self._lock:
            # Insert based on priority (higher priority first)
            insert_idx = 0
            for i, t in enumerate(self._pending):
                if task.priority.value > t.priority.value:
                    insert_idx = i
                    break
                insert_idx = i + 1
            
            self._pending.insert(insert_idx, task)
            return True
    
    async def dequeue(self, worker_id: str) -> Optional[QueuedTask]:
        """Get the next task for processing."""
        async with self._lock:
            if not self._pending:
                return None
            
            task = self._pending.pop(0)
            task.state = TaskState.RUNNING
            task.started_at = datetime.now()
            task.worker_id = worker_id
            
            self._processing[task.id] = task
            return task
    
    async def complete(self, task_id: str, result: Any) -> bool:
        """Mark a task as completed."""
        async with self._lock:
            if task_id not in self._processing:
                return False
            
            task = self._processing.pop(task_id)
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            
            self._completed[task_id] = task
            return True
    
    async def fail(self, task_id: str, error: str) -> bool:
        """Mark a task as failed."""
        async with self._lock:
            if task_id not in self._processing:
                return False
            
            task = self._processing.pop(task_id)
            task.error = error
            
            # Retry if under limit
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.state = TaskState.RETRYING
                task.worker_id = None
                self._pending.append(task)
            else:
                task.state = TaskState.FAILED
                task.completed_at = datetime.now()
                self._completed[task_id] = task
            
            return True
    
    async def get_status(self, task_id: str) -> Optional[QueuedTask]:
        """Get the status of a task."""
        async with self._lock:
            if task_id in self._processing:
                return self._processing[task_id]
            if task_id in self._completed:
                return self._completed[task_id]
            for task in self._pending:
                if task.id == task_id:
                    return task
            return None
    
    async def get_pending_count(self) -> int:
        """Get the number of pending tasks."""
        async with self._lock:
            return len(self._pending)
    
    async def get_stats(self) -> dict:
        """Get queue statistics."""
        async with self._lock:
            return {
                "pending": len(self._pending),
                "processing": len(self._processing),
                "completed": len(self._completed),
            }


# Type for task handlers
TaskHandler = Callable[[QueuedTask], Awaitable[Any]]


@dataclass
class WorkerConfig:
    """Configuration for a worker."""
    
    worker_id: str = field(default_factory=lambda: f"worker-{uuid.uuid4().hex[:8]}")
    poll_interval_seconds: float = 1.0
    max_tasks_per_batch: int = 1
    idle_timeout_seconds: float = 60.0


class TaskWorker:
    """Worker that processes tasks from a queue.
    
    Example:
        >>> async def handler(task: QueuedTask) -> Any:
        ...     return await process_agent_request(task.payload)
        >>> 
        >>> worker = TaskWorker(queue, handler)
        >>> await worker.start()
    """
    
    def __init__(
        self,
        queue: TaskQueue,
        handler: TaskHandler,
        config: Optional[WorkerConfig] = None,
    ):
        """Initialize worker.
        
        Args:
            queue: Task queue to poll.
            handler: Function to process tasks.
            config: Worker configuration.
        """
        self.queue = queue
        self.handler = handler
        self.config = config or WorkerConfig()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._tasks_processed = 0
        self._tasks_failed = 0
    
    @property
    def worker_id(self) -> str:
        """Get worker ID."""
        return self.config.worker_id
    
    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running
    
    async def start(self) -> None:
        """Start the worker loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run())
        print(f"Worker {self.worker_id} started")
    
    async def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print(f"Worker {self.worker_id} stopped")
    
    async def _run(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                task = await self.queue.dequeue(self.worker_id)
                
                if task is None:
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue
                
                try:
                    result = await self.handler(task)
                    await self.queue.complete(task.id, result)
                    self._tasks_processed += 1
                except Exception as e:
                    await self.queue.fail(task.id, str(e))
                    self._tasks_failed += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(self.config.poll_interval_seconds)
    
    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            "worker_id": self.worker_id,
            "running": self._running,
            "tasks_processed": self._tasks_processed,
            "tasks_failed": self._tasks_failed,
        }


class WorkerPool:
    """Pool of workers for parallel task processing.
    
    Example:
        >>> pool = WorkerPool(queue, handler, worker_count=4)
        >>> await pool.start()
        >>> # ... later
        >>> await pool.stop()
    """
    
    def __init__(
        self,
        queue: TaskQueue,
        handler: TaskHandler,
        worker_count: int = 3,
        config: Optional[WorkerConfig] = None,
    ):
        """Initialize worker pool.
        
        Args:
            queue: Task queue to use.
            handler: Task handler function.
            worker_count: Number of workers to spawn.
            config: Base configuration for workers.
        """
        self.queue = queue
        self.handler = handler
        self.worker_count = worker_count
        self.base_config = config or WorkerConfig()
        self._workers: list[TaskWorker] = []
    
    async def start(self) -> None:
        """Start all workers."""
        for i in range(self.worker_count):
            config = WorkerConfig(
                worker_id=f"{self.base_config.worker_id}-{i}",
                poll_interval_seconds=self.base_config.poll_interval_seconds,
                max_tasks_per_batch=self.base_config.max_tasks_per_batch,
            )
            worker = TaskWorker(self.queue, self.handler, config)
            await worker.start()
            self._workers.append(worker)
        
        print(f"Worker pool started with {self.worker_count} workers")
    
    async def stop(self) -> None:
        """Stop all workers."""
        for worker in self._workers:
            await worker.stop()
        self._workers.clear()
        print("Worker pool stopped")
    
    async def scale(self, new_count: int) -> None:
        """Scale the number of workers.
        
        Args:
            new_count: New number of workers.
        """
        current = len(self._workers)
        
        if new_count > current:
            # Add workers
            for i in range(current, new_count):
                config = WorkerConfig(
                    worker_id=f"{self.base_config.worker_id}-{i}",
                    poll_interval_seconds=self.base_config.poll_interval_seconds,
                )
                worker = TaskWorker(self.queue, self.handler, config)
                await worker.start()
                self._workers.append(worker)
        elif new_count < current:
            # Remove workers
            while len(self._workers) > new_count:
                worker = self._workers.pop()
                await worker.stop()
        
        self.worker_count = new_count
    
    def get_stats(self) -> dict:
        """Get pool statistics."""
        return {
            "worker_count": len(self._workers),
            "workers": [w.get_stats() for w in self._workers],
            "total_processed": sum(w._tasks_processed for w in self._workers),
            "total_failed": sum(w._tasks_failed for w in self._workers),
        }


class DistributedCoordinator:
    """Coordinator that uses distributed task queue.
    
    Wraps the standard AgentCoordinator to use task queues
    for horizontal scaling.
    
    Example:
        >>> from app.agents import AgentCoordinator
        >>> 
        >>> queue = InMemoryTaskQueue()
        >>> coordinator = AgentCoordinator()
        >>> distributed = DistributedCoordinator(coordinator, queue)
        >>> 
        >>> # Submit work
        >>> task_id = await distributed.submit("Research AI")
        >>> 
        >>> # Check result later
        >>> result = await distributed.get_result(task_id)
    """
    
    def __init__(
        self,
        coordinator: Any,  # AgentCoordinator
        queue: TaskQueue,
        worker_count: int = 3,
    ):
        """Initialize distributed coordinator.
        
        Args:
            coordinator: The AgentCoordinator to use.
            queue: Task queue for distribution.
            worker_count: Number of worker processes.
        """
        self.coordinator = coordinator
        self.queue = queue
        self.pool: Optional[WorkerPool] = None
        self.worker_count = worker_count
    
    async def start(self) -> None:
        """Start the distributed coordinator."""
        self.pool = WorkerPool(
            self.queue,
            self._handle_task,
            worker_count=self.worker_count,
        )
        await self.pool.start()
    
    async def stop(self) -> None:
        """Stop the distributed coordinator."""
        if self.pool:
            await self.pool.stop()
    
    async def _handle_task(self, task: QueuedTask) -> Any:
        """Handle a queued task using the coordinator."""
        request = task.payload.get("request", "")
        context = task.payload.get("context", {})
        
        result = await self.coordinator.execute(request, context)
        return {
            "content": result.content,
            "success": result.success,
            "agents_used": result.agents_used,
        }
    
    async def submit(
        self,
        request: str,
        context: Optional[dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """Submit a request for distributed processing.
        
        Args:
            request: The user request.
            context: Optional context.
            priority: Task priority.
        
        Returns:
            str: Task ID for tracking.
        """
        task = QueuedTask(
            name="coordinator.execute",
            payload={
                "request": request,
                "context": context or {},
            },
            priority=priority,
        )
        
        await self.queue.enqueue(task)
        return task.id
    
    async def get_result(
        self,
        task_id: str,
        timeout_seconds: float = 30.0,
    ) -> Optional[dict]:
        """Get the result of a submitted task.
        
        Args:
            task_id: Task ID from submit().
            timeout_seconds: Max time to wait.
        
        Returns:
            Result dict or None if not ready/failed.
        """
        start = time.time()
        
        while time.time() - start < timeout_seconds:
            task = await self.queue.get_status(task_id)
            
            if task is None:
                return None
            
            if task.state == TaskState.COMPLETED:
                return task.result
            
            if task.state == TaskState.FAILED:
                return {"error": task.error, "success": False}
            
            await asyncio.sleep(0.5)
        
        return None
    
    async def get_stats(self) -> dict:
        """Get distributed coordinator statistics."""
        queue_stats = await self.queue.get_stats() if hasattr(self.queue, 'get_stats') else {}
        pool_stats = self.pool.get_stats() if self.pool else {}
        
        return {
            "queue": queue_stats,
            "pool": pool_stats,
        }
