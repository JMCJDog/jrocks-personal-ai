"""Inbound webhook receiver.

Handles incoming webhook requests with signature verification,
event routing, and deduplication.
"""

import logging
from typing import Callable, Dict, Optional, Any, Awaitable, Set
from datetime import datetime

from .models import InboundWebhookPayload
from .security import verify_signature

logger = logging.getLogger(__name__)

# Type for webhook handlers
WebhookHandler = Callable[[str, Dict[str, Any]], Awaitable[None]]


class WebhookReceiver:
    """Receives and processes inbound webhook requests.
    
    Features:
    - HMAC signature verification
    - Event routing to registered handlers
    - Idempotency key tracking for deduplication
    
    Example:
        receiver = WebhookReceiver()
        
        @receiver.handler("github.push")
        async def handle_push(event_type: str, payload: dict):
            print(f"Received push: {payload}")
        
        # Process incoming request
        await receiver.process(
            event_type="github.push",
            payload={"ref": "refs/heads/main"},
            signature="abc123",
            timestamp=1234567890,
            secret="my-secret"
        )
    """
    
    def __init__(self, dedup_window_size: int = 1000):
        """Initialize receiver.
        
        Args:
            dedup_window_size: Max number of idempotency keys to track.
        """
        self._handlers: Dict[str, WebhookHandler] = {}
        self._default_handler: Optional[WebhookHandler] = None
        self._processed_keys: Set[str] = set()
        self._dedup_window_size = dedup_window_size
    
    def handler(self, event_type: str):
        """Decorator to register a handler for an event type.
        
        Args:
            event_type: The event type to handle.
            
        Example:
            @receiver.handler("user.created")
            async def handle_user_created(event_type, payload):
                ...
        """
        def decorator(func: WebhookHandler) -> WebhookHandler:
            self._handlers[event_type] = func
            logger.info(f"Registered handler for event: {event_type}")
            return func
        return decorator
    
    def set_default_handler(self, handler: WebhookHandler):
        """Set a default handler for unrecognized event types.
        
        Args:
            handler: The handler function.
        """
        self._default_handler = handler
        logger.info("Set default webhook handler")
    
    def register_handler(self, event_type: str, handler: WebhookHandler):
        """Register a handler function for an event type.
        
        Args:
            event_type: The event type to handle.
            handler: The handler function.
        """
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for event: {event_type}")
    
    async def process(
        self,
        event_type: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
        timestamp: Optional[int] = None,
        secret: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        raw_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process an incoming webhook request.
        
        Args:
            event_type: The type of event.
            payload: The event payload.
            signature: Optional HMAC signature for verification.
            timestamp: Optional timestamp for signature verification.
            secret: Optional secret for signature verification.
            idempotency_key: Optional key for deduplication.
            raw_body: Raw request body for signature verification.
            
        Returns:
            Dict with processing result status.
            
        Raises:
            ValueError: If signature verification fails.
        """
        # Signature verification (if provided)
        if signature and timestamp and secret and raw_body:
            if not verify_signature(raw_body, signature, secret, timestamp):
                logger.warning(f"Invalid signature for webhook event: {event_type}")
                raise ValueError("Invalid webhook signature")
        
        # Deduplication check
        if idempotency_key:
            if idempotency_key in self._processed_keys:
                logger.info(f"Duplicate webhook ignored: {idempotency_key}")
                return {
                    "status": "duplicate",
                    "message": "Event already processed",
                    "idempotency_key": idempotency_key
                }
            
            # Track this key
            self._processed_keys.add(idempotency_key)
            
            # Trim old keys if over limit
            if len(self._processed_keys) > self._dedup_window_size:
                # Remove oldest (arbitrary since set is unordered)
                self._processed_keys.pop()
        
        # Find and invoke handler
        handler = self._handlers.get(event_type, self._default_handler)
        
        if handler is None:
            logger.warning(f"No handler for webhook event: {event_type}")
            return {
                "status": "unhandled",
                "message": f"No handler for event type: {event_type}",
                "event_type": event_type
            }
        
        try:
            await handler(event_type, payload)
            logger.info(f"Processed webhook event: {event_type}")
            return {
                "status": "success",
                "message": "Event processed successfully",
                "event_type": event_type
            }
        except Exception as e:
            logger.error(f"Error processing webhook {event_type}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "event_type": event_type
            }
    
    def get_registered_handlers(self) -> Dict[str, str]:
        """Get list of registered event handlers.
        
        Returns:
            Dict mapping event types to handler function names.
        """
        return {
            event_type: handler.__name__
            for event_type, handler in self._handlers.items()
        }


# Global receiver instance
_receiver: Optional[WebhookReceiver] = None


def get_receiver() -> WebhookReceiver:
    """Get the global webhook receiver instance."""
    global _receiver
    if _receiver is None:
        _receiver = WebhookReceiver()
    return _receiver
