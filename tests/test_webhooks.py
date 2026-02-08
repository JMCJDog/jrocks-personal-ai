"""Tests for the webhooks module.

Covers event types, signature verification, registry, dispatcher,
and receiver components.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.app.webhooks.models import (
    WebhookEvent,
    WebhookEventType,
    WebhookConfig,
    WebhookDelivery,
)
from src.app.webhooks.security import (
    generate_signature,
    verify_signature,
    generate_webhook_headers,
)
from src.app.webhooks.registry import WebhookRegistry
from src.app.webhooks.dispatcher import WebhookDispatcher
from src.app.webhooks.receiver import WebhookReceiver


# ============================================================================
# Model Tests
# ============================================================================

class TestWebhookModels:
    """Tests for webhook Pydantic models."""
    
    def test_webhook_event_creation(self):
        """Test creating a basic webhook event."""
        event = WebhookEvent(
            event_type=WebhookEventType.AGENT_COMPLETED,
            payload={"agent_id": "123", "result": "success"}
        )
        
        assert event.event_type == WebhookEventType.AGENT_COMPLETED
        assert event.payload["agent_id"] == "123"
        assert event.id is not None
        assert event.timestamp is not None
        assert event.source == "jrocks-personal-ai"
    
    def test_webhook_event_serialization(self):
        """Test that events serialize to JSON correctly."""
        event = WebhookEvent(
            event_type=WebhookEventType.CHAT_MESSAGE_SENT,
            payload={"message": "Hello!"}
        )
        
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        
        assert data["event_type"] == "chat.message.sent"
        assert data["payload"]["message"] == "Hello!"
        assert "timestamp" in data
    
    def test_webhook_config_defaults(self):
        """Test webhook config with default values."""
        config = WebhookConfig(
            name="Test Webhook",
            url="https://example.com/webhook"
        )
        
        assert config.enabled is True
        assert config.events == []
        assert config.max_retries == 3
        assert config.id is not None


# ============================================================================
# Security Tests
# ============================================================================

class TestWebhookSecurity:
    """Tests for HMAC signature generation and verification."""
    
    def test_generate_signature_deterministic(self):
        """Test that signature generation is deterministic."""
        payload = '{"test": true}'
        secret = "my-secret-key"
        timestamp = 1234567890
        
        sig1, ts1 = generate_signature(payload, secret, timestamp)
        sig2, ts2 = generate_signature(payload, secret, timestamp)
        
        assert sig1 == sig2
        assert ts1 == ts2 == timestamp
    
    def test_verify_signature_valid(self):
        """Test successful signature verification."""
        payload = '{"test": true}'
        secret = "my-secret-key"
        timestamp = int(time.time())
        
        signature, _ = generate_signature(payload, secret, timestamp)
        
        assert verify_signature(payload, signature, secret, timestamp) is True
    
    def test_verify_signature_invalid(self):
        """Test signature verification with wrong secret."""
        payload = '{"test": true}'
        timestamp = int(time.time())
        
        signature, _ = generate_signature(payload, "correct-secret", timestamp)
        
        assert verify_signature(payload, signature, "wrong-secret", timestamp) is False
    
    def test_verify_signature_expired(self):
        """Test signature verification rejects old timestamps."""
        payload = '{"test": true}'
        secret = "my-secret-key"
        old_timestamp = int(time.time()) - 600  # 10 minutes ago
        
        signature, _ = generate_signature(payload, secret, old_timestamp)
        
        # Should fail due to age (default max_age is 300 seconds)
        assert verify_signature(payload, signature, secret, old_timestamp) is False
    
    def test_generate_webhook_headers(self):
        """Test header generation for outbound webhooks."""
        payload = '{"event": "test"}'
        secret = "secret123"
        
        headers = generate_webhook_headers(payload, secret)
        
        assert headers["Content-Type"] == "application/json"
        assert "X-Webhook-Signature" in headers
        assert "X-Webhook-Timestamp" in headers
        assert headers["User-Agent"] == "JRocksPersonalAI-Webhook/1.0"


# ============================================================================
# Registry Tests
# ============================================================================

class TestWebhookRegistry:
    """Tests for webhook registry operations."""
    
    def test_register_and_get(self):
        """Test registering and retrieving a webhook."""
        registry = WebhookRegistry()
        
        config = WebhookConfig(
            name="Test",
            url="https://example.com/hook"
        )
        
        registered = registry.register(config)
        retrieved = registry.get(registered.id)
        
        assert retrieved is not None
        assert retrieved.name == "Test"
        assert str(retrieved.url) == "https://example.com/hook"
    
    def test_unregister(self):
        """Test removing a webhook."""
        registry = WebhookRegistry()
        
        config = WebhookConfig(name="Test", url="https://example.com")
        registered = registry.register(config)
        
        assert registry.unregister(registered.id) is True
        assert registry.get(registered.id) is None
        assert registry.unregister(registered.id) is False
    
    def test_get_for_event_with_subscription(self):
        """Test filtering webhooks by event type."""
        registry = WebhookRegistry()
        
        # Subscribes to specific event
        registry.register(WebhookConfig(
            name="Agent Hook",
            url="https://example.com/agent",
            events=[WebhookEventType.AGENT_COMPLETED]
        ))
        
        # Subscribes to all events (empty list)
        registry.register(WebhookConfig(
            name="All Events",
            url="https://example.com/all",
            events=[]
        ))
        
        # Different event
        registry.register(WebhookConfig(
            name="Chat Hook",
            url="https://example.com/chat",
            events=[WebhookEventType.CHAT_MESSAGE_SENT]
        ))
        
        agent_hooks = registry.get_for_event(WebhookEventType.AGENT_COMPLETED)
        
        assert len(agent_hooks) == 2  # Agent Hook + All Events
        names = {h.name for h in agent_hooks}
        assert "Agent Hook" in names
        assert "All Events" in names
    
    def test_disabled_webhooks_excluded(self):
        """Test that disabled webhooks are not returned."""
        registry = WebhookRegistry()
        
        registry.register(WebhookConfig(
            name="Enabled",
            url="https://example.com/enabled",
            enabled=True
        ))
        
        registry.register(WebhookConfig(
            name="Disabled",
            url="https://example.com/disabled",
            enabled=False
        ))
        
        hooks = registry.get_for_event(WebhookEventType.AGENT_COMPLETED)
        
        assert len(hooks) == 1
        assert hooks[0].name == "Enabled"


# ============================================================================
# Receiver Tests
# ============================================================================

class TestWebhookReceiver:
    """Tests for inbound webhook processing."""
    
    @pytest.mark.asyncio
    async def test_process_with_handler(self):
        """Test processing an event with a registered handler."""
        receiver = WebhookReceiver()
        handled = []
        
        async def my_handler(event_type: str, payload: dict):
            handled.append((event_type, payload))
        
        receiver.register_handler("test.event", my_handler)
        
        result = await receiver.process(
            event_type="test.event",
            payload={"data": "value"}
        )
        
        assert result["status"] == "success"
        assert len(handled) == 1
        assert handled[0][0] == "test.event"
    
    @pytest.mark.asyncio
    async def test_process_unhandled_event(self):
        """Test processing an event with no handler."""
        receiver = WebhookReceiver()
        
        result = await receiver.process(
            event_type="unknown.event",
            payload={}
        )
        
        assert result["status"] == "unhandled"
    
    @pytest.mark.asyncio
    async def test_deduplication(self):
        """Test that duplicate events are rejected."""
        receiver = WebhookReceiver()
        call_count = 0
        
        async def handler(event_type: str, payload: dict):
            nonlocal call_count
            call_count += 1
        
        receiver.register_handler("test.event", handler)
        
        # First call
        await receiver.process(
            event_type="test.event",
            payload={},
            idempotency_key="unique-key-123"
        )
        
        # Duplicate call
        result = await receiver.process(
            event_type="test.event",
            payload={},
            idempotency_key="unique-key-123"
        )
        
        assert result["status"] == "duplicate"
        assert call_count == 1


# ============================================================================
# Dispatcher Tests
# ============================================================================

class TestWebhookDispatcher:
    """Tests for outbound webhook dispatching."""
    
    @pytest.mark.asyncio
    async def test_dispatch_success(self):
        """Test successful webhook dispatch."""
        dispatcher = WebhookDispatcher()
        
        # Mock the registry
        with patch('src.app.webhooks.dispatcher.get_registry') as mock_registry:
            mock_config = WebhookConfig(
                name="Test",
                url="https://example.com/webhook"
            )
            mock_registry.return_value.get_for_event.return_value = [mock_config]
            
            # Mock HTTP client
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = "OK"
                
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                
                event = WebhookEvent(
                    event_type=WebhookEventType.AGENT_COMPLETED,
                    payload={"test": True}
                )
                
                deliveries = await dispatcher.dispatch(event)
                
                assert len(deliveries) == 1
                assert deliveries[0].status == "success"
    
    @pytest.mark.asyncio
    async def test_dispatch_with_retry(self):
        """Test that failed deliveries are retried."""
        dispatcher = WebhookDispatcher(max_retries=2, base_delay_seconds=0.1)
        
        with patch('src.app.webhooks.dispatcher.get_registry') as mock_registry:
            mock_config = WebhookConfig(
                name="Failing",
                url="https://example.com/fail",
                max_retries=2
            )
            mock_registry.return_value.get_for_event.return_value = [mock_config]
            
            call_count = 0
            
            async def failing_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_response.text = "Server Error"
                return mock_response
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.post = failing_post
                
                event = WebhookEvent(
                    event_type=WebhookEventType.SYSTEM_ERROR,
                    payload={}
                )
                
                deliveries = await dispatcher.dispatch(event)
                
                # Should have retried (1 initial + 2 retries = 3 attempts)
                assert call_count == 3
                assert deliveries[0].status == "failed"
                assert deliveries[0].attempts == 3
