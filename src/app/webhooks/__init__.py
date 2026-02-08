"""Webhooks module for inbound/outbound webhook handling.

Provides a scalable, provider-agnostic webhooks framework with:
- Inbound webhook receivers with signature verification
- Outbound webhook dispatching with retry and circuit breaker
- Extensible event types and handler registry
"""

from .router import router
from .models import WebhookEvent, WebhookEventType, WebhookConfig
from .dispatcher import WebhookDispatcher
from .receiver import WebhookReceiver
from .registry import WebhookRegistry

__all__ = [
    "router",
    "WebhookEvent",
    "WebhookEventType", 
    "WebhookConfig",
    "WebhookDispatcher",
    "WebhookReceiver",
    "WebhookRegistry",
]
