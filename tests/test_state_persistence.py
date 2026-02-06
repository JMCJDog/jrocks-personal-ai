"""Tests for the state persistence module."""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from app.core.state_persistence import (
    WorkflowCheckpoint,
    FileStateStore,
    CheckpointManager,
)


class TestWorkflowCheckpoint:
    """Tests for WorkflowCheckpoint dataclass."""
    
    def test_create_checkpoint(self):
        """Test creating a checkpoint."""
        checkpoint = WorkflowCheckpoint(
            workflow_name="test_workflow",
            total_steps=5,
        )
        
        assert checkpoint.workflow_name == "test_workflow"
        assert checkpoint.total_steps == 5
        assert checkpoint.current_step == 0
        assert checkpoint.status == "running"
        assert len(checkpoint.id) > 0
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        checkpoint = WorkflowCheckpoint(
            workflow_name="test",
            total_steps=3,
            context={"key": "value"},
        )
        
        data = checkpoint.to_dict()
        
        assert data["workflow_name"] == "test"
        assert data["total_steps"] == 3
        assert data["context"] == {"key": "value"}
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "test-id",
            "workflow_name": "restored",
            "current_step": 2,
            "total_steps": 5,
            "status": "running",
            "context": {"restored": True},
            "task_results": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": {},
        }
        
        checkpoint = WorkflowCheckpoint.from_dict(data)
        
        assert checkpoint.id == "test-id"
        assert checkpoint.workflow_name == "restored"
        assert checkpoint.current_step == 2
    
    def test_update(self):
        """Test updating checkpoint fields."""
        checkpoint = WorkflowCheckpoint(workflow_name="test")
        original_time = checkpoint.updated_at
        
        checkpoint.update(current_step=3, status="paused")
        
        assert checkpoint.current_step == 3
        assert checkpoint.status == "paused"
        assert checkpoint.updated_at != original_time


class TestFileStateStore:
    """Tests for FileStateStore."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)
    
    @pytest.fixture
    def store(self, temp_dir):
        """Create a store with temp directory."""
        return FileStateStore(temp_dir)
    
    @pytest.mark.asyncio
    async def test_save_and_load(self, store):
        """Test saving and loading a checkpoint."""
        checkpoint = WorkflowCheckpoint(
            workflow_name="test_save",
            total_steps=10,
        )
        
        success = await store.save(checkpoint)
        assert success
        
        loaded = await store.load(checkpoint.id)
        assert loaded is not None
        assert loaded.id == checkpoint.id
        assert loaded.workflow_name == "test_save"
    
    @pytest.mark.asyncio
    async def test_load_nonexistent(self, store):
        """Test loading a non-existent checkpoint."""
        loaded = await store.load("nonexistent-id")
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_list_checkpoints(self, store):
        """Test listing checkpoints."""
        # Create multiple checkpoints
        for i in range(3):
            cp = WorkflowCheckpoint(workflow_name=f"workflow_{i}")
            await store.save(cp)
        
        all_checkpoints = await store.list_checkpoints()
        assert len(all_checkpoints) == 3
    
    @pytest.mark.asyncio
    async def test_list_with_filter(self, store):
        """Test listing with workflow filter."""
        await store.save(WorkflowCheckpoint(workflow_name="alpha"))
        await store.save(WorkflowCheckpoint(workflow_name="beta"))
        await store.save(WorkflowCheckpoint(workflow_name="alpha"))
        
        alpha_only = await store.list_checkpoints(workflow_name="alpha")
        assert len(alpha_only) == 2
    
    @pytest.mark.asyncio
    async def test_delete(self, store):
        """Test deleting a checkpoint."""
        checkpoint = WorkflowCheckpoint(workflow_name="to_delete")
        await store.save(checkpoint)
        
        result = await store.delete(checkpoint.id)
        assert result is True
        
        loaded = await store.load(checkpoint.id)
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_get_latest(self, store):
        """Test getting the latest checkpoint."""
        cp1 = WorkflowCheckpoint(workflow_name="my_workflow")
        await store.save(cp1)
        
        await asyncio.sleep(0.01)  # Ensure different timestamp
        
        cp2 = WorkflowCheckpoint(workflow_name="my_workflow")
        await store.save(cp2)
        
        latest = await store.get_latest("my_workflow")
        assert latest is not None
        assert latest.id == cp2.id


class TestCheckpointManager:
    """Tests for CheckpointManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create a manager with temp store."""
        store = FileStateStore(temp_dir)
        return CheckpointManager(store)
    
    def test_create(self, manager):
        """Test creating a checkpoint."""
        checkpoint = manager.create(
            workflow_name="new_workflow",
            total_steps=5,
            context={"initial": True},
        )
        
        assert checkpoint.workflow_name == "new_workflow"
        assert checkpoint.total_steps == 5
        assert checkpoint.context["initial"] is True
    
    @pytest.mark.asyncio
    async def test_checkpoint_progress(self, manager):
        """Test checkpointing progress."""
        checkpoint = manager.create("progress_test", total_steps=3)
        
        # Checkpoint step 1
        await manager.checkpoint(
            checkpoint,
            step=1,
            result={"output": "step1"},
        )
        
        assert checkpoint.current_step == 1
        assert len(checkpoint.task_results) == 1
    
    @pytest.mark.asyncio
    async def test_complete(self, manager):
        """Test completing a checkpoint."""
        checkpoint = manager.create("complete_test", total_steps=2)
        await manager.complete(checkpoint)
        
        assert checkpoint.status == "completed"
    
    @pytest.mark.asyncio
    async def test_fail(self, manager):
        """Test failing a checkpoint."""
        checkpoint = manager.create("fail_test", total_steps=2)
        await manager.fail(checkpoint, "Something went wrong")
        
        assert checkpoint.status == "failed"
        assert checkpoint.metadata["error"] == "Something went wrong"
    
    @pytest.mark.asyncio
    async def test_get_resumable(self, manager):
        """Test getting a resumable checkpoint."""
        checkpoint = manager.create("resumable_test", total_steps=5)
        await manager.checkpoint(checkpoint, step=2)
        
        resumable = await manager.get_resumable("resumable_test")
        
        assert resumable is not None
        assert resumable.current_step == 2
