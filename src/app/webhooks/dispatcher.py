"""Outbound webhook dispatcher.

Sends webhook events to registered endpoints with retry logic,
exponential backoff, and circuit breaker integration.
"""

import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx

from .models import WebhookEvent, WebhookConfig, WebhookDelivery
from .security import generate_webhook_headers
from .registry import get_registry
from ..agents.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Dispatches webhook events to registered endpoints.
    
    Features:
    - Async HTTP delivery with configurable timeout
    - Exponential backoff retry on failure
    - Circuit breaker per endpoint to prevent cascade failures
    - Delivery tracking and logging
    
    Example:
        dispatcher = WebhookDispatcher()
        event = WebhookEvent(
            event_type=WebhookEventType.AGENT_COMPLETED,
            payload={"agent_id": "123", "result": "success"}
        )
        await dispatcher.dispatch(event)
    """
    
    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
    ):
        """Initialize dispatcher.
        
        Args:
            timeout_seconds: HTTP request timeout.
            max_retries: Maximum retry attempts per delivery.
            base_delay_seconds: Base delay for exponential backoff.
        """
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.base_delay = base_delay_seconds
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._deliveries: List[WebhookDelivery] = []
    
    def _get_circuit_breaker(self, webhook_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for a webhook endpoint."""
        if webhook_id not in self._circuit_breakers:
            config = CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout_seconds=60,
            )
            self._circuit_breakers[webhook_id] = CircuitBreaker(
                name=f"webhook_{webhook_id}",
                config=config
            )
        return self._circuit_breakers[webhook_id]
    
    async def dispatch(self, event: WebhookEvent) -> List[WebhookDelivery]:
        """Dispatch an event to all subscribed webhooks.
        
        Args:
            event: The webhook event to dispatch.
            
        Returns:
            List of delivery records for each webhook.
        """
        registry = get_registry()
        webhooks = registry.get_for_event(event.event_type)
        
        if not webhooks:
            logger.debug(f"No webhooks registered for event: {event.event_type}")
            return []
        
        # Dispatch to all subscribed webhooks concurrently
        tasks = [
            self._deliver_to_webhook(event, webhook)
            for webhook in webhooks
        ]
        
        deliveries = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log errors
        results = []
        for i, delivery in enumerate(deliveries):
            if isinstance(delivery, Exception):
                logger.error(f"Delivery failed: {delivery}")
            else:
                results.append(delivery)
        
        return results
    
    async def _deliver_to_webhook(
        self,
        event: WebhookEvent,
        webhook: WebhookConfig
    ) -> WebhookDelivery:
        """Deliver an event to a specific webhook with retry.
        
        Args:
            event: The event to deliver.
            webhook: The webhook configuration.
            
        Returns:
            Delivery record with status.
        """
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_id=event.id,
            status="pending"
        )
        
        circuit_breaker = self._get_circuit_breaker(webhook.id)
        
        # Use webhook-specific retry config or defaults
        max_retries = webhook.max_retries or self.max_retries
        
        for attempt in range(max_retries + 1):
            delivery.attempts = attempt + 1
            delivery.last_attempt_at = datetime.utcnow()
            
            try:
                # Check circuit breaker
                if circuit_breaker.is_open:
                    if not circuit_breaker._should_attempt_reset():
                        raise CircuitBreakerError(
                            circuit_breaker.name,
                            circuit_breaker._last_failure_time + timedelta(
                                seconds=circuit_breaker.config.timeout_seconds
                            )
                        )
                
                # Attempt delivery
                success = await self._send_webhook(event, webhook, delivery)
                
                if success:
                    delivery.status = "success"
                    circuit_breaker.record_success()
                    logger.info(
                        f"Webhook delivered: {event.event_type} -> {webhook.name} "
                        f"(attempt {attempt + 1})"
                    )
                    break
                else:
                    raise Exception(f"Delivery failed with status {delivery.response_status}")
                    
            except CircuitBreakerError as e:
                delivery.status = "failed"
                delivery.error_message = str(e)
                logger.warning(f"Circuit breaker open for webhook {webhook.name}: {e}")
                break
                
            except Exception as e:
                circuit_breaker.record_failure(e)
                delivery.error_message = str(e)
                
                if attempt < max_retries:
                    # Calculate exponential backoff delay
                    delay = self.base_delay * (2 ** attempt)
                    delivery.status = "retrying"
                    delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
                    
                    logger.warning(
                        f"Webhook delivery failed for {webhook.name}, "
                        f"retrying in {delay}s (attempt {attempt + 1}/{max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                else:
                    delivery.status = "failed"
                    logger.error(
                        f"Webhook delivery failed after {max_retries + 1} attempts "
                        f"for {webhook.name}: {e}"
                    )
        
        self._deliveries.append(delivery)
        return delivery
    
    async def _send_webhook(
        self,
        event: WebhookEvent,
        webhook: WebhookConfig,
        delivery: WebhookDelivery
    ) -> bool:
        """Send HTTP POST to webhook endpoint.
        
        Args:
            event: The event to send.
            webhook: The webhook configuration.
            delivery: The delivery record to update.
            
        Returns:
            True if successful (2xx status), False otherwise.
        """
        payload = event.model_dump_json()
        
        # Build headers with optional signature
        headers = {"Content-Type": "application/json"}
        if webhook.secret:
            headers.update(generate_webhook_headers(payload, webhook.secret))
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                str(webhook.url),
                content=payload,
                headers=headers
            )
            
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000]  # Truncate response
            
            return 200 <= response.status_code < 300
    
    def get_recent_deliveries(self, limit: int = 100) -> List[WebhookDelivery]:
        """Get recent delivery records.
        
        Args:
            limit: Maximum number of records to return.
            
        Returns:
            List of recent deliveries, newest first.
        """
        return sorted(
            self._deliveries[-limit:],
            key=lambda d: d.last_attempt_at or datetime.min,
            reverse=True
        )


# Global dispatcher instance
_dispatcher: Optional[WebhookDispatcher] = None


def get_dispatcher() -> WebhookDispatcher:
    """Get the global webhook dispatcher instance."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = WebhookDispatcher()
    return _dispatcher
