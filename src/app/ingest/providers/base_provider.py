"""Abstract base class for chat history providers.

Defines the interface for parsing and normalizing chat exports from
different AI providers (OpenAI, Anthropic, Google, Ollama, etc.).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported AI chat providers."""
    
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    UNKNOWN = "unknown"


class ChatMessage(BaseModel):
    """Normalized chat message from any provider.
    
    Attributes:
        role: Message author role (user, assistant, system)
        content: The message text content
        timestamp: When the message was sent (if available)
        model: The AI model used for assistant responses
        attachments: List of file paths or URLs for any attachments
        metadata: Provider-specific additional data
    """
    
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime | None = None
    model: str | None = None
    attachments: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatConversation(BaseModel):
    """Normalized conversation containing multiple messages.
    
    Attributes:
        id: Unique identifier for this conversation
        provider: The source provider (openai, anthropic, etc.)
        title: Conversation title or summary
        messages: Ordered list of messages in the conversation
        created_at: When the conversation started
        updated_at: When the conversation was last updated
        metadata: Provider-specific additional data
    """
    
    id: str
    provider: ProviderType
    title: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    @property
    def message_count(self) -> int:
        """Total number of messages in the conversation."""
        return len(self.messages)
    
    @property
    def user_message_count(self) -> int:
        """Number of user messages."""
        return sum(1 for m in self.messages if m.role == "user")
    
    def to_text(self) -> str:
        """Convert conversation to plain text format for embedding."""
        lines = []
        if self.title:
            lines.append(f"# {self.title}\n")
        for msg in self.messages:
            prefix = "User" if msg.role == "user" else "Assistant"
            lines.append(f"**{prefix}**: {msg.content}\n")
        return "\n".join(lines)


class ChatHistoryProvider(ABC):
    """Abstract base class for chat history providers.
    
    Implementations must provide methods to:
    - Detect if a file/path belongs to this provider
    - Parse the export format into normalized structures
    - Extract metadata specific to the provider
    """
    
    provider_type: ProviderType = ProviderType.UNKNOWN
    
    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        """Check if this provider can parse the given file or directory.
        
        Args:
            path: Path to the export file or directory
            
        Returns:
            True if this provider can handle the export format
        """
        pass
    
    @abstractmethod
    def parse(self, path: Path) -> list[ChatConversation]:
        """Parse an export file/directory into normalized conversations.
        
        Args:
            path: Path to the export file or extracted directory
            
        Returns:
            List of parsed and normalized conversations
            
        Raises:
            ValueError: If the export format is invalid
            FileNotFoundError: If required files are missing
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """Get list of supported file extensions/formats.
        
        Returns:
            List of supported extensions (e.g., ['.zip', '.json', '.html'])
        """
        pass
    
    def extract_metadata(self, path: Path) -> dict[str, Any]:
        """Extract provider-specific metadata from export.
        
        Override in subclasses for provider-specific metadata extraction.
        
        Args:
            path: Path to the export
            
        Returns:
            Dictionary of metadata
        """
        return {
            "provider": self.provider_type.value,
            "source_path": str(path),
            "imported_at": datetime.now().isoformat(),
        }
