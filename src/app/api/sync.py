"""API endpoints for chat history sync operations.

Provides endpoints for:
- Triggering manual sync operations
- Checking sync status and history
- Uploading export files directly
"""

import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..ingest.providers import (
    AnthropicProvider,
    ChatConversation,
    GoogleProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderType,
)
from ..ingest.sync import SyncConfig, SyncScheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])

# Initialize scheduler (in production, this would be a singleton)
_sync_config = SyncConfig.default()
_scheduler = SyncScheduler(_sync_config)


# Request/Response Models
class SyncTriggerRequest(BaseModel):
    """Request to trigger a sync operation."""
    
    provider: str | None = Field(
        default=None,
        description="Specific provider to sync, or null for all providers"
    )


class SyncTriggerResponse(BaseModel):
    """Response from sync trigger."""
    
    job_id: str
    status: str
    provider: str | None
    success_count: int
    failure_count: int
    duration_seconds: float | None


class SyncStatusResponse(BaseModel):
    """Response for sync status check."""
    
    job_id: str
    status: str
    provider: str | None
    started_at: str | None
    completed_at: str | None
    success_count: int
    failure_count: int
    results: list[dict[str, Any]]


class SyncHistoryResponse(BaseModel):
    """Response for sync history."""
    
    jobs: list[SyncStatusResponse]


class UploadResponse(BaseModel):
    """Response from file upload."""
    
    success: bool
    provider: str | None
    conversations_count: int
    conversation_ids: list[str]
    error: str | None = None


# Endpoints
@router.post("/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(request: SyncTriggerRequest) -> SyncTriggerResponse:
    """Manually trigger a sync operation.
    
    Args:
        request: Sync trigger parameters
        
    Returns:
        Sync job status
    """
    job = _scheduler.trigger_sync(provider=request.provider)
    
    return SyncTriggerResponse(
        job_id=job.id,
        status=job.status.value,
        provider=job.provider,
        success_count=job.success_count,
        failure_count=job.failure_count,
        duration_seconds=job.duration_seconds,
    )


@router.get("/status/{job_id}", response_model=SyncStatusResponse)
async def get_sync_status(job_id: str) -> SyncStatusResponse:
    """Get status of a sync job.
    
    Args:
        job_id: The job ID to check
        
    Returns:
        Current job status
    """
    job = _scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return SyncStatusResponse(
        job_id=job.id,
        status=job.status.value,
        provider=job.provider,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        success_count=job.success_count,
        failure_count=job.failure_count,
        results=job.results,
    )


@router.get("/history", response_model=SyncHistoryResponse)
async def get_sync_history(limit: int = 10) -> SyncHistoryResponse:
    """Get recent sync job history.
    
    Args:
        limit: Maximum number of jobs to return
        
    Returns:
        List of recent sync jobs
    """
    jobs = _scheduler.get_recent_jobs(limit=limit)
    
    return SyncHistoryResponse(
        jobs=[
            SyncStatusResponse(
                job_id=job.id,
                status=job.status.value,
                provider=job.provider,
                started_at=job.started_at.isoformat() if job.started_at else None,
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                success_count=job.success_count,
                failure_count=job.failure_count,
                results=job.results,
            )
            for job in jobs
        ]
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_export(file: UploadFile = File(...)) -> UploadResponse:
    """Upload an export file for direct processing.
    
    Supports ZIP and JSON files from any supported provider.
    The provider is auto-detected from file contents.
    
    Args:
        file: The export file to process
        
    Returns:
        Processing result with conversation IDs
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    
    # Determine file extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".zip", ".json", ".jsonl"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Use .zip, .json, or .jsonl"
        )
    
    # Save to temp file
    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        # Detect provider
        providers = [
            OpenAIProvider(),
            AnthropicProvider(),
            GoogleProvider(),
            OllamaProvider(),
        ]
        
        detected_provider = None
        for provider in providers:
            if provider.can_parse(tmp_path):
                detected_provider = provider
                break
        
        if not detected_provider:
            return UploadResponse(
                success=False,
                provider=None,
                conversations_count=0,
                conversation_ids=[],
                error="Could not detect provider from file contents",
            )
        
        # Parse conversations
        conversations = detected_provider.parse(tmp_path)
        
        # TODO: Store conversations in vector store
        # For now, just return the count
        
        return UploadResponse(
            success=True,
            provider=detected_provider.provider_type.value,
            conversations_count=len(conversations),
            conversation_ids=[c.id for c in conversations],
        )
        
    except Exception as e:
        logger.error(f"Error processing upload: {e}")
        return UploadResponse(
            success=False,
            provider=None,
            conversations_count=0,
            conversation_ids=[],
            error=str(e),
        )
    
    finally:
        # Cleanup temp file
        tmp_path.unlink(missing_ok=True)


@router.get("/providers")
async def list_providers() -> dict[str, Any]:
    """List available chat history providers and their status.
    
    Returns:
        Provider information and configuration status
    """
    providers_info = []
    
    for provider_type in ProviderType:
        if provider_type == ProviderType.UNKNOWN:
            continue
        
        settings = _sync_config.get_provider_settings(provider_type.value)
        
        providers_info.append({
            "name": provider_type.value,
            "enabled": settings.enabled,
            "watch_paths": [str(p) for p in settings.watch_paths],
            "frequency": settings.frequency.value,
            "file_patterns": settings.file_patterns,
        })
    
    return {
        "providers": providers_info,
        "default_watch_path": str(_sync_config.default_watch_path),
    }
