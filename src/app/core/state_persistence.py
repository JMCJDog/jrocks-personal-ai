"""State Persistence Layer - Durable checkpointing for workflows.

Provides checkpoint save/restore functionality for long-running
multi-agent workflows, enabling recovery from failures.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, TypeVar, Generic
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import json
import uuid
import asyncio


@dataclass
class WorkflowCheckpoint:
    """A serializable snapshot of workflow state."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str = ""
    current_step: int = 0
    total_steps: int = 0
    status: str = "running"  # running, paused, completed, failed
    context: dict = field(default_factory=dict)
    task_results: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowCheckpoint":
        """Create from dictionary."""
        return cls(**data)
    
    def update(self, **kwargs) -> "WorkflowCheckpoint":
        """Update fields and refresh updated_at timestamp."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now().isoformat()
        return self


class StateStore(ABC):
    """Abstract base class for state storage backends."""
    
    @abstractmethod
    async def save(self, checkpoint: WorkflowCheckpoint) -> bool:
        """Save a checkpoint. Returns True on success."""
        pass
    
    @abstractmethod
    async def load(self, checkpoint_id: str) -> Optional[WorkflowCheckpoint]:
        """Load a checkpoint by ID."""
        pass
    
    @abstractmethod
    async def list_checkpoints(
        self, 
        workflow_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[WorkflowCheckpoint]:
        """List checkpoints with optional filtering."""
        pass
    
    @abstractmethod
    async def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint. Returns True on success."""
        pass
    
    @abstractmethod
    async def get_latest(
        self, 
        workflow_name: str,
    ) -> Optional[WorkflowCheckpoint]:
        """Get the most recent checkpoint for a workflow."""
        pass


class FileStateStore(StateStore):
    """File-based state storage using JSON files.
    
    Simple, portable, no external dependencies.
    Good for development and single-instance deployments.
    
    Example:
        >>> store = FileStateStore("/path/to/checkpoints")
        >>> await store.save(checkpoint)
        >>> loaded = await store.load(checkpoint.id)
    """
    
    def __init__(self, base_path: str | Path):
        """Initialize with base directory for checkpoint files.
        
        Args:
            base_path: Directory to store checkpoint files.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, checkpoint_id: str) -> Path:
        """Get file path for a checkpoint ID."""
        return self.base_path / f"{checkpoint_id}.json"
    
    async def save(self, checkpoint: WorkflowCheckpoint) -> bool:
        """Save checkpoint to JSON file."""
        try:
            path = self._get_path(checkpoint.id)
            data = checkpoint.to_dict()
            
            # Write atomically using temp file
            temp_path = path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(data, indent=2))
            temp_path.rename(path)
            
            return True
        except Exception as e:
            print(f"Failed to save checkpoint: {e}")
            return False
    
    async def load(self, checkpoint_id: str) -> Optional[WorkflowCheckpoint]:
        """Load checkpoint from JSON file."""
        try:
            path = self._get_path(checkpoint_id)
            if not path.exists():
                return None
            
            data = json.loads(path.read_text())
            return WorkflowCheckpoint.from_dict(data)
        except Exception as e:
            print(f"Failed to load checkpoint: {e}")
            return None
    
    async def list_checkpoints(
        self,
        workflow_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[WorkflowCheckpoint]:
        """List all checkpoints with optional filtering."""
        checkpoints = []
        
        for path in self.base_path.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                checkpoint = WorkflowCheckpoint.from_dict(data)
                
                # Apply filters
                if workflow_name and checkpoint.workflow_name != workflow_name:
                    continue
                if status and checkpoint.status != status:
                    continue
                
                checkpoints.append(checkpoint)
            except Exception:
                continue  # Skip corrupted files
        
        # Sort by updated_at descending
        checkpoints.sort(key=lambda c: c.updated_at, reverse=True)
        return checkpoints
    
    async def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint file."""
        try:
            path = self._get_path(checkpoint_id)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    async def get_latest(
        self,
        workflow_name: str,
    ) -> Optional[WorkflowCheckpoint]:
        """Get the most recent checkpoint for a workflow."""
        checkpoints = await self.list_checkpoints(workflow_name=workflow_name)
        return checkpoints[0] if checkpoints else None


class CheckpointManager:
    """High-level checkpoint management for coordinators.
    
    Provides convenient methods for checkpointing workflow progress,
    resuming from failures, and cleaning up old checkpoints.
    
    Example:
        >>> manager = CheckpointManager(FileStateStore("./checkpoints"))
        >>> 
        >>> # During workflow execution
        >>> cp = manager.create("my_workflow", total_steps=5)
        >>> await manager.checkpoint(cp, step=1, result={"data": "..."})
        >>> 
        >>> # After crash, resume
        >>> cp = await manager.get_resumable("my_workflow")
        >>> if cp:
        ...     resume_from = cp.current_step
    """
    
    def __init__(
        self,
        store: StateStore,
        auto_cleanup: bool = True,
        max_age_hours: int = 24,
    ):
        """Initialize checkpoint manager.
        
        Args:
            store: Storage backend for checkpoints.
            auto_cleanup: Whether to auto-delete old completed checkpoints.
            max_age_hours: Max age for completed checkpoints before cleanup.
        """
        self.store = store
        self.auto_cleanup = auto_cleanup
        self.max_age_hours = max_age_hours
    
    def create(
        self,
        workflow_name: str,
        total_steps: int,
        context: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> WorkflowCheckpoint:
        """Create a new checkpoint for a workflow.
        
        Args:
            workflow_name: Name of the workflow.
            total_steps: Total number of steps in workflow.
            context: Initial context data.
            metadata: Additional metadata.
        
        Returns:
            WorkflowCheckpoint: The created checkpoint.
        """
        return WorkflowCheckpoint(
            workflow_name=workflow_name,
            total_steps=total_steps,
            context=context or {},
            metadata=metadata or {},
        )
    
    async def checkpoint(
        self,
        checkpoint: WorkflowCheckpoint,
        step: int,
        result: Optional[dict] = None,
        context_update: Optional[dict] = None,
    ) -> bool:
        """Save progress at a specific step.
        
        Args:
            checkpoint: The checkpoint to update.
            step: Current step number.
            result: Result from the current step.
            context_update: Updates to merge into context.
        
        Returns:
            bool: True if saved successfully.
        """
        checkpoint.current_step = step
        
        if result:
            checkpoint.task_results.append({
                "step": step,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            })
        
        if context_update:
            checkpoint.context.update(context_update)
        
        checkpoint.updated_at = datetime.now().isoformat()
        
        return await self.store.save(checkpoint)
    
    async def complete(self, checkpoint: WorkflowCheckpoint) -> bool:
        """Mark a checkpoint as completed.
        
        Args:
            checkpoint: The checkpoint to complete.
        
        Returns:
            bool: True if saved successfully.
        """
        checkpoint.status = "completed"
        checkpoint.updated_at = datetime.now().isoformat()
        return await self.store.save(checkpoint)
    
    async def fail(
        self, 
        checkpoint: WorkflowCheckpoint, 
        error: str,
    ) -> bool:
        """Mark a checkpoint as failed.
        
        Args:
            checkpoint: The checkpoint that failed.
            error: Error message.
        
        Returns:
            bool: True if saved successfully.
        """
        checkpoint.status = "failed"
        checkpoint.metadata["error"] = error
        checkpoint.updated_at = datetime.now().isoformat()
        return await self.store.save(checkpoint)
    
    async def get_resumable(
        self,
        workflow_name: str,
    ) -> Optional[WorkflowCheckpoint]:
        """Get a checkpoint that can be resumed.
        
        Args:
            workflow_name: Name of the workflow.
        
        Returns:
            WorkflowCheckpoint or None if no resumable checkpoint exists.
        """
        checkpoints = await self.store.list_checkpoints(
            workflow_name=workflow_name,
            status="running",
        )
        return checkpoints[0] if checkpoints else None
    
    async def cleanup_old(self) -> int:
        """Delete old completed/failed checkpoints.
        
        Returns:
            int: Number of checkpoints deleted.
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=self.max_age_hours)
        deleted = 0
        
        for status in ["completed", "failed"]:
            checkpoints = await self.store.list_checkpoints(status=status)
            for cp in checkpoints:
                try:
                    cp_time = datetime.fromisoformat(cp.updated_at)
                    if cp_time < cutoff:
                        if await self.store.delete(cp.id):
                            deleted += 1
                except Exception:
                    continue
        
        return deleted


# Default store instance (lazy initialization)
_default_store: Optional[FileStateStore] = None


def get_default_store(base_path: Optional[str] = None) -> FileStateStore:
    """Get or create the default state store.
    
    Args:
        base_path: Optional custom path. Uses ./checkpoints if not specified.
    
    Returns:
        FileStateStore: The default store instance.
    """
    global _default_store
    
    if _default_store is None:
        path = base_path or "./checkpoints"
        _default_store = FileStateStore(path)
    
    return _default_store
