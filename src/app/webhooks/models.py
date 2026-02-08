"""Webhook data models and event types.

Defines Pydantic schemas for webhook events, configurations,
and response models used throughout the webhooks framework.
"""

from enum import Enum
from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
import uuid


class WebhookEventType(str, Enum):
    """Extensible webhook event types."""
    
    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    
    # Chat events
    CHAT_MESSAGE_RECEIVED = "chat.message.received"
    CHAT_MESSAGE_SENT = "chat.message.sent"
    
    # Ingest events
    INGEST_STARTED = "ingest.started"
    INGEST_COMPLETED = "ingest.completed"
    INGEST_FAILED = "ingest.failed"
    
    # System events
    SYSTEM_HEALTH_CHANGED = "system.health.changed"
    SYSTEM_ERROR = "system.error"
    
    # Custom/generic
    CUSTOM = "custom"


class WebhookEvent(BaseModel):
    """Base webhook event model."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: WebhookEventType
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    idempotency_key: Optional[str] = None
    source: str = "jrocks-personal-ai"
    version: str = "1.0"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebhookConfig(BaseModel):
    """Configuration for a registered webhook endpoint."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Human-readable name for this webhook")
    url: HttpUrl = Field(..., description="Endpoint URL to receive webhooks")
    secret: Optional[str] = Field(None, description="Shared secret for HMAC signature")
    events: List[WebhookEventType] = Field(
        default_factory=list,
        description="Event types to subscribe to (empty = all)"
    )
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: int = 5


class WebhookDelivery(BaseModel):
    """Record of a webhook delivery attempt."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    webhook_id: str
    event_id: str
    status: str  # "pending", "success", "failed", "retrying"
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None


class WebhookRegistrationRequest(BaseModel):
    """Request to register a new webhook."""
    
    name: str
    url: HttpUrl
    secret: Optional[str] = None
    events: List[WebhookEventType] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WebhookRegistrationResponse(BaseModel):
    """Response after registering a webhook."""
    
    id: str
    name: str
    url: str
    events: List[WebhookEventType]
    enabled: bool
    created_at: datetime
    message: str = "Webhook registered successfully"


class InboundWebhookPayload(BaseModel):
    """Generic inbound webhook payload."""
    
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None
    source: Optional[str] = None


class WebhookListResponse(BaseModel):
    """Response containing list of webhooks."""
    
    webhooks: List[WebhookConfig]
    total: int
