"""MCP Service - Unified integration layer.

Provides a high-level service that combines all MCP components
for easy integration with the rest of the application.
"""

from typing import Optional, Any, Callable
from dataclasses import dataclass, field

from .protocol import MCPServer, MCPClient, MCPTool, MCPResource, MCPMessage
from .providers import LLMProvider, ProviderConfig, get_provider, ProviderType, ProviderMessage
from .registry import ToolRegistry, ResourceRegistry, get_tool_registry, get_resource_registry
from .transport import Transport, create_transport


@dataclass
class MCPServiceConfig:
    """Configuration for the MCP service."""
    
    default_provider: ProviderType = ProviderType.OLLAMA
    provider_config: Optional[ProviderConfig] = None
    enable_tools: bool = True
    enable_resources: bool = True
    max_tool_calls: int = 10  # Maximum tool calls per request


class MCPService:
    """High-level MCP integration service.
    
    Provides a unified interface for:
    - LLM provider management
    - Tool registration and execution
    - Resource management
    - Multi-turn conversations with tool use
    
    Example:
        >>> service = MCPService()
        >>> service.register_tool("search", "Search web", search_fn)
        >>> response = await service.chat("Find info about Python")
    """
    
    def __init__(self, config: Optional[MCPServiceConfig] = None) -> None:
        """Initialize the MCP service.
        
        Args:
            config: Service configuration.
        """
        self.config = config or MCPServiceConfig()
        self._provider: Optional[LLMProvider] = None
        self._tool_registry = get_tool_registry()
        self._resource_registry = get_resource_registry()
        self._conversation: list[ProviderMessage] = []
    
    @property
    def provider(self) -> LLMProvider:
        """Get or create the LLM provider."""
        if self._provider is None:
            self._provider = get_provider(
                self.config.default_provider,
                **(self.config.provider_config.__dict__ if self.config.provider_config else {})
            )
        return self._provider
    
    def set_provider(
        self,
        provider_type: str | ProviderType,
        **kwargs
    ) -> LLMProvider:
        """Set the LLM provider.
        
        Args:
            provider_type: Provider type.
            **kwargs: Provider configuration.
        
        Returns:
            LLMProvider: The configured provider.
        """
        self._provider = get_provider(provider_type, **kwargs)
        return self._provider
    
    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable,
        **kwargs
    ) -> MCPTool:
        """Register a tool.
        
        Args:
            name: Tool name.
            description: Tool description.
            handler: Tool function.
            **kwargs: Additional tool options.
        
        Returns:
            MCPTool: The registered tool.
        """
        return self._tool_registry.register(name, description, handler, **kwargs)
    
    def tool(self, name: str, description: str, **kwargs) -> Callable:
        """Decorator for registering tools.
        
        Args:
            name: Tool name.
            description: Tool description.
        
        Returns:
            Callable: Decorator.
        """
        return self._tool_registry.tool(name, description, **kwargs)
    
    def register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        **kwargs
    ) -> MCPResource:
        """Register a resource.
        
        Args:
            uri: Resource URI.
            name: Resource name.
            description: Resource description.
        
        Returns:
            MCPResource: The registered resource.
        """
        return self._resource_registry.register(uri, name, description, **kwargs)
    
    def add_system_message(self, content: str) -> None:
        """Add a system message to the conversation.
        
        Args:
            content: System message content.
        """
        self._conversation.insert(0, ProviderMessage(role="system", content=content))
    
    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self._conversation.clear()
    
    async def chat(
        self,
        message: str,
        use_tools: bool = True,
        stream: bool = False,
    ) -> str:
        """Send a message and get a response.
        
        Handles tool calls automatically if enabled.
        
        Args:
            message: User message.
            use_tools: Whether to enable tool use.
            stream: Whether to stream the response.
        
        Returns:
            str: The assistant's response.
        """
        # Add user message
        self._conversation.append(ProviderMessage(role="user", content=message))
        
        # Get tools in provider format
        tools = None
        if use_tools and self.config.enable_tools:
            provider_type = self.provider.provider_type
            format_map = {
                ProviderType.CLAUDE: "claude",
                ProviderType.OPENAI: "openai",
            }
            tools = self._tool_registry.get_schemas(format_map.get(provider_type, "generic"))
        
        # Generate response
        if stream:
            content = ""
            async for chunk in self.provider.stream(self._conversation, tools):
                content += chunk
            response_content = content
            tool_calls = []
        else:
            response = await self.provider.complete(self._conversation, tools)
            response_content = response.content
            tool_calls = response.tool_calls
        
        # Handle tool calls
        if tool_calls and use_tools:
            response_content = await self._handle_tool_calls(
                tool_calls, response_content
            )
        
        # Add assistant response
        self._conversation.append(ProviderMessage(
            role="assistant",
            content=response_content
        ))
        
        return response_content
    
    async def _handle_tool_calls(
        self,
        tool_calls: list[dict],
        initial_response: str,
    ) -> str:
        """Handle tool calls in a response.
        
        Args:
            tool_calls: List of tool calls from the model.
            initial_response: Initial model response.
        
        Returns:
            str: Final response after tool execution.
        """
        tool_results = []
        
        for call in tool_calls[:self.config.max_tool_calls]:
            name = call.get("name")
            arguments = call.get("arguments", {})
            
            # Parse arguments if string
            if isinstance(arguments, str):
                import json
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            
            try:
                result = await self._tool_registry.call(name, **arguments)
                tool_results.append({
                    "name": name,
                    "result": str(result),
                    "success": True,
                })
            except Exception as e:
                tool_results.append({
                    "name": name,
                    "result": f"Error: {str(e)}",
                    "success": False,
                })
        
        # Add tool results to conversation
        for result in tool_results:
            self._conversation.append(ProviderMessage(
                role="tool",
                content=f"Tool {result['name']}: {result['result']}",
                name=result["name"],
            ))
        
        # Get follow-up response
        response = await self.provider.complete(self._conversation)
        return response.content
    
    async def complete_with_context(
        self,
        message: str,
        resource_uris: list[str],
    ) -> str:
        """Complete with resource context.
        
        Args:
            message: User message.
            resource_uris: URIs of resources to include.
        
        Returns:
            str: Response.
        """
        # Load resources
        context_parts = []
        for uri in resource_uris:
            try:
                content = await self._resource_registry.read(uri)
                resource = self._resource_registry.get(uri)
                context_parts.append(f"## {resource.name}\n{content}")
            except Exception:
                continue
        
        # Build context-enhanced message
        if context_parts:
            context = "\n\n".join(context_parts)
            enhanced_message = f"Context:\n{context}\n\nQuestion: {message}"
        else:
            enhanced_message = message
        
        return await self.chat(enhanced_message, use_tools=True)


# Global service instance
_service: Optional[MCPService] = None


def get_mcp_service() -> MCPService:
    """Get the global MCP service."""
    global _service
    if _service is None:
        _service = MCPService()
    return _service


def configure_mcp(
    provider: str = "ollama",
    **kwargs
) -> MCPService:
    """Configure the global MCP service.
    
    Args:
        provider: LLM provider type.
        **kwargs: Provider configuration.
    
    Returns:
        MCPService: Configured service.
    """
    global _service
    _service = MCPService()
    _service.set_provider(provider, **kwargs)
    return _service
