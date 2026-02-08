"""Provider abstraction layer for multi-source AI chat history ingestion."""

from .base_provider import (
    ChatHistoryProvider,
    ChatMessage,
    ChatConversation,
    ProviderType,
)
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .ollama_provider import OllamaProvider
from .google_drive_provider import GoogleDriveProvider
from .google_photos_provider import GooglePhotosProvider


__all__ = [
    # Base classes
    "ChatHistoryProvider",
    "ChatMessage",
    "ChatConversation",
    "ProviderType",
    # Provider implementations
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "OllamaProvider",
    "GoogleDriveProvider",
    "GooglePhotosProvider",
]
