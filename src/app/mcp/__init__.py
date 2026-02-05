"""MCP (Model Context Protocol) Integration Framework.

Provides a scalable, provider-agnostic interface for integrating
with best-in-class LLMs including Claude, GPT-4, Gemini, and local models.
"""

from .protocol import (
    MCPClient,
    MCPServer,
    MCPMessage,
    MCPTool,
    MCPResource,
)
from .providers import (
    LLMProvider,
    ProviderConfig,
    ClaudeProvider,
    OpenAIProvider,
    GeminiProvider,
    OllamaProvider,
    get_provider,
)
from .registry import ToolRegistry, ResourceRegistry
from .transport import Transport, StdioTransport, SSETransport


__all__ = [
    # Protocol
    "MCPClient",
    "MCPServer",
    "MCPMessage",
    "MCPTool",
    "MCPResource",
    
    # Providers
    "LLMProvider",
    "ProviderConfig",
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "OllamaProvider",
    "get_provider",
    
    # Registry
    "ToolRegistry",
    "ResourceRegistry",
    
    # Transport
    "Transport",
    "StdioTransport",
    "SSETransport",
]
