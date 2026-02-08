"""Webhook configuration registry.

Stores and manages webhook endpoint configurations.
Initial implementation uses in-memory storage; can be extended
to persist to database.
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

from .models import WebhookConfig, WebhookEventType

logger = logging.getLogger(__name__)


class WebhookRegistry:
    """In-memory registry for webhook configurations.
    
    Manages webhook endpoint registrations and provides
    lookup by ID or event type.
    
    Example:
        registry = WebhookRegistry()
        config = WebhookConfig(
            name="My Webhook",
            url="https://example.com/webhook",
            events=[WebhookEventType.AGENT_COMPLETED]
        )
        registry.register(config)
        
        # Get webhooks for a specific event
        webhooks = registry.get_for_event(WebhookEventType.AGENT_COMPLETED)
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._webhooks: Dict[str, WebhookConfig] = {}
    
    def register(self, config: WebhookConfig) -> WebhookConfig:
        """Register a new webhook configuration.
        
        Args:
            config: The webhook configuration to register.
            
        Returns:
            The registered configuration (with generated ID if not set).
        """
        self._webhooks[config.id] = config
        logger.info(f"Registered webhook '{config.name}' ({config.id}) for URL: {config.url}")
        return config
    
    def unregister(self, webhook_id: str) -> bool:
        """Remove a webhook registration.
        
        Args:
            webhook_id: The ID of the webhook to remove.
            
        Returns:
            True if removed, False if not found.
        """
        if webhook_id in self._webhooks:
            config = self._webhooks.pop(webhook_id)
            logger.info(f"Unregistered webhook '{config.name}' ({webhook_id})")
            return True
        return False
    
    def get(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Get a webhook configuration by ID.
        
        Args:
            webhook_id: The ID of the webhook.
            
        Returns:
            The configuration if found, None otherwise.
        """
        return self._webhooks.get(webhook_id)
    
    def get_all(self) -> List[WebhookConfig]:
        """Get all registered webhooks.
        
        Returns:
            List of all webhook configurations.
        """
        return list(self._webhooks.values())
    
    def get_for_event(self, event_type: WebhookEventType) -> List[WebhookConfig]:
        """Get all webhooks subscribed to a specific event type.
        
        Args:
            event_type: The event type to filter by.
            
        Returns:
            List of webhook configurations subscribed to this event.
        """
        results = []
        for config in self._webhooks.values():
            if not config.enabled:
                continue
            # Empty events list means subscribed to all
            if not config.events or event_type in config.events:
                results.append(config)
        return results
    
    def update(self, webhook_id: str, **updates) -> Optional[WebhookConfig]:
        """Update a webhook configuration.
        
        Args:
            webhook_id: The ID of the webhook to update.
            **updates: Fields to update.
            
        Returns:
            Updated configuration if found, None otherwise.
        """
        config = self._webhooks.get(webhook_id)
        if not config:
            return None
        
        # Create updated config
        config_dict = config.model_dump()
        config_dict.update(updates)
        updated = WebhookConfig(**config_dict)
        self._webhooks[webhook_id] = updated
        
        logger.info(f"Updated webhook '{updated.name}' ({webhook_id})")
        return updated
    
    def set_enabled(self, webhook_id: str, enabled: bool) -> bool:
        """Enable or disable a webhook.
        
        Args:
            webhook_id: The ID of the webhook.
            enabled: Whether to enable or disable.
            
        Returns:
            True if updated, False if not found.
        """
        result = self.update(webhook_id, enabled=enabled)
        return result is not None
    
    def clear(self) -> int:
        """Remove all webhook registrations.
        
        Returns:
            Number of webhooks removed.
        """
        count = len(self._webhooks)
        self._webhooks.clear()
        logger.info(f"Cleared {count} webhook registrations")
        return count


# Global singleton registry instance
_registry: Optional[WebhookRegistry] = None


def get_registry() -> WebhookRegistry:
    """Get the global webhook registry instance.
    
    Returns:
        The singleton WebhookRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = WebhookRegistry()
    return _registry
