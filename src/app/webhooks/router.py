"""Webhook API routes.

FastAPI router providing endpoints for webhook management
and inbound webhook reception.
"""

from fastapi import APIRouter, HTTPException, Request, Header, BackgroundTasks
from typing import Optional, List
import logging

from .models import (
    WebhookConfig,
    WebhookEvent,
    WebhookEventType,
    WebhookRegistrationRequest,
    WebhookRegistrationResponse,
    WebhookListResponse,
    WebhookDelivery,
    InboundWebhookPayload,
)
from .registry import get_registry
from .dispatcher import get_dispatcher
from .receiver import get_receiver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ============================================================================
# Webhook Registration Endpoints
# ============================================================================

@router.post("/register", response_model=WebhookRegistrationResponse)
async def register_webhook(request: WebhookRegistrationRequest):
    """Register a new webhook endpoint.
    
    Creates a new webhook subscription that will receive events
    at the specified URL.
    """
    registry = get_registry()
    
    config = WebhookConfig(
        name=request.name,
        url=request.url,
        secret=request.secret,
        events=request.events,
        metadata=request.metadata,
    )
    
    registered = registry.register(config)
    
    return WebhookRegistrationResponse(
        id=registered.id,
        name=registered.name,
        url=str(registered.url),
        events=registered.events,
        enabled=registered.enabled,
        created_at=registered.created_at,
    )


@router.get("/", response_model=WebhookListResponse)
async def list_webhooks():
    """List all registered webhooks."""
    registry = get_registry()
    webhooks = registry.get_all()
    
    return WebhookListResponse(
        webhooks=webhooks,
        total=len(webhooks)
    )


@router.get("/{webhook_id}", response_model=WebhookConfig)
async def get_webhook(webhook_id: str):
    """Get a specific webhook by ID."""
    registry = get_registry()
    config = registry.get(webhook_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return config


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook registration."""
    registry = get_registry()
    
    if not registry.unregister(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"status": "success", "message": "Webhook deleted"}


@router.post("/{webhook_id}/enable")
async def enable_webhook(webhook_id: str):
    """Enable a webhook."""
    registry = get_registry()
    
    if not registry.set_enabled(webhook_id, True):
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"status": "success", "message": "Webhook enabled"}


@router.post("/{webhook_id}/disable")
async def disable_webhook(webhook_id: str):
    """Disable a webhook."""
    registry = get_registry()
    
    if not registry.set_enabled(webhook_id, False):
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"status": "success", "message": "Webhook disabled"}


# ============================================================================
# Webhook Dispatch Endpoints
# ============================================================================

@router.post("/dispatch", response_model=List[WebhookDelivery])
async def dispatch_event(event: WebhookEvent, background_tasks: BackgroundTasks):
    """Manually dispatch a webhook event to all subscribers.
    
    Useful for testing or triggering custom events.
    """
    dispatcher = get_dispatcher()
    deliveries = await dispatcher.dispatch(event)
    return deliveries


@router.post("/test/{webhook_id}")
async def test_webhook(webhook_id: str):
    """Send a test event to a specific webhook.
    
    Sends a test ping event to verify the webhook is configured correctly.
    """
    registry = get_registry()
    config = registry.get(webhook_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Create test event
    test_event = WebhookEvent(
        event_type=WebhookEventType.CUSTOM,
        payload={
            "test": True,
            "message": "This is a test webhook from JRock's Personal AI",
            "webhook_id": webhook_id,
        }
    )
    
    dispatcher = get_dispatcher()
    deliveries = await dispatcher.dispatch(test_event)
    
    if deliveries and deliveries[0].status == "success":
        return {"status": "success", "message": "Test webhook delivered"}
    else:
        error = deliveries[0].error_message if deliveries else "Unknown error"
        raise HTTPException(status_code=502, detail=f"Test webhook failed: {error}")


@router.get("/deliveries/recent", response_model=List[WebhookDelivery])
async def get_recent_deliveries(limit: int = 50):
    """Get recent webhook delivery attempts.
    
    Returns the most recent delivery records for monitoring.
    """
    dispatcher = get_dispatcher()
    return dispatcher.get_recent_deliveries(limit=limit)


# ============================================================================
# Inbound Webhook Receiver Endpoint
# ============================================================================

@router.post("/receive/{source}")
async def receive_webhook(
    source: str,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    x_webhook_timestamp: Optional[str] = Header(None),
):
    """Receive an inbound webhook from an external source.
    
    This is a generic endpoint for receiving webhooks from various
    providers (GitHub, Stripe, etc.). The source path parameter
    identifies the provider.
    
    Args:
        source: The webhook source identifier (e.g., "github", "stripe").
    """
    receiver = get_receiver()
    
    # Parse body
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")
    
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Extract event type from payload (provider-specific logic can be added)
    event_type = f"{source}.{payload.get('type', payload.get('event', 'unknown'))}"
    
    # Parse timestamp if provided
    timestamp = None
    if x_webhook_timestamp:
        try:
            timestamp = int(x_webhook_timestamp)
        except ValueError:
            pass
    
    # Process the webhook
    # Note: Secret should be looked up based on source in production
    result = await receiver.process(
        event_type=event_type,
        payload=payload,
        signature=x_webhook_signature,
        timestamp=timestamp,
        raw_body=body_str,
        idempotency_key=payload.get("idempotency_key"),
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


# ============================================================================
# Event Types Endpoint
# ============================================================================

@router.get("/event-types")
async def list_event_types():
    """List all available webhook event types."""
    return {
        "event_types": [
            {"value": e.value, "name": e.name}
            for e in WebhookEventType
        ]
    }
