"""Scheduler for recurring chat history sync jobs.

Uses APScheduler for background job management with support for
different sync frequencies per provider.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

from .file_watcher import FileWatcher, ProcessingResult
from .sync_config import SyncConfig, SyncFrequency

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Status of a sync job."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncJob(BaseModel):
    """Represents a sync job execution."""
    
    id: str
    provider: str | None = None  # None means all providers
    status: JobStatus = JobStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    results: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    
    @property
    def duration_seconds(self) -> float | None:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def success_count(self) -> int:
        """Count of successfully processed files."""
        return sum(1 for r in self.results if r.get("success"))
    
    @property
    def failure_count(self) -> int:
        """Count of failed files."""
        return sum(1 for r in self.results if not r.get("success"))


class SyncScheduler:
    """Manages recurring sync jobs for chat history ingestion.
    
    Provides scheduling capabilities using APScheduler with support for:
    - Manual sync triggers
    - Hourly/daily scheduled syncs
    - Per-provider sync intervals
    """
    
    def __init__(
        self,
        sync_config: SyncConfig,
        on_conversations: Callable[[list], None] | None = None,
    ):
        """Initialize the scheduler.
        
        Args:
            sync_config: Sync configuration
            on_conversations: Callback for processed conversations
        """
        self.sync_config = sync_config
        self.on_conversations = on_conversations
        
        self._file_watcher = FileWatcher(
            sync_config=sync_config,
            on_process=on_conversations,
        )
        
        self._scheduler = None
        self._jobs: dict[str, SyncJob] = {}
        self._job_counter = 0
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID."""
        self._job_counter += 1
        return f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._job_counter}"
    
    def trigger_sync(self, provider: str | None = None) -> SyncJob:
        """Manually trigger a sync job.
        
        Args:
            provider: Optional specific provider to sync, or None for all
            
        Returns:
            The created SyncJob
        """
        job_id = self._generate_job_id()
        job = SyncJob(
            id=job_id,
            provider=provider,
            status=JobStatus.RUNNING,
            started_at=datetime.now(),
        )
        self._jobs[job_id] = job
        
        try:
            results = self._execute_sync(provider)
            
            job.results = [
                {
                    "file": str(r.file_path),
                    "success": r.success,
                    "provider": r.provider.value if r.provider else None,
                    "conversations": r.conversations_count,
                    "error": r.error,
                }
                for r in results
            ]
            job.status = JobStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Sync job {job_id} failed: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
        
        finally:
            job.completed_at = datetime.now()
        
        return job
    
    def _execute_sync(self, provider: str | None = None) -> list[ProcessingResult]:
        """Execute sync for specified provider(s).
        
        Args:
            provider: Optional specific provider, or None for all
            
        Returns:
            List of processing results
        """
        if provider:
            # Sync specific provider
            settings = self.sync_config.get_provider_settings(provider)
            results = []
            for watch_path in settings.watch_paths:
                results.extend(self._file_watcher.scan_directory(watch_path))
            return results
        else:
            # Sync all providers
            return self._file_watcher.scan_all()
    
    def get_job(self, job_id: str) -> SyncJob | None:
        """Get a job by ID.
        
        Args:
            job_id: The job ID
            
        Returns:
            The SyncJob or None if not found
        """
        return self._jobs.get(job_id)
    
    def get_recent_jobs(self, limit: int = 10) -> list[SyncJob]:
        """Get recently executed jobs.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of recent SyncJobs, newest first
        """
        jobs = sorted(
            self._jobs.values(),
            key=lambda j: j.started_at or datetime.min,
            reverse=True,
        )
        return jobs[:limit]
    
    def start_scheduled_jobs(self) -> None:
        """Start the background scheduler for recurring jobs.
        
        This requires APScheduler to be installed. If not available,
        logs a warning and continues without scheduling.
        """
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger
        except ImportError:
            logger.warning(
                "APScheduler not installed. Scheduled sync disabled. "
                "Install with: pip install apscheduler"
            )
            return
        
        self._scheduler = AsyncIOScheduler()
        
        for provider_name, settings in self.sync_config.providers.items():
            if not settings.enabled:
                continue
            
            if settings.frequency == SyncFrequency.HOURLY:
                self._scheduler.add_job(
                    self.trigger_sync,
                    trigger=IntervalTrigger(hours=1),
                    kwargs={"provider": provider_name},
                    id=f"sync_{provider_name}",
                )
                logger.info(f"Scheduled hourly sync for {provider_name}")
            
            elif settings.frequency == SyncFrequency.DAILY:
                self._scheduler.add_job(
                    self.trigger_sync,
                    trigger=CronTrigger(hour=2, minute=0),  # 2 AM daily
                    kwargs={"provider": provider_name},
                    id=f"sync_{provider_name}",
                )
                logger.info(f"Scheduled daily sync for {provider_name}")
        
        self._scheduler.start()
        logger.info("Sync scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown()
            logger.info("Sync scheduler stopped")
