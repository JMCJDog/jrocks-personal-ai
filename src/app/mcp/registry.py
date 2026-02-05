"""Tool and Resource Registry - Centralized registration system.

Provides a scalable registry for MCP tools and resources
with discovery, validation, and lifecycle management.
"""

from typing import Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import inspect
import json

from .protocol import MCPTool, MCPResource, ToolType


@dataclass
class ToolMetrics:
    """Metrics for tool usage tracking."""
    
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0
    last_called: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.success_count / self.call_count
    
    @property
    def avg_duration_ms(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.total_duration_ms / self.call_count


class ToolRegistry:
    """Registry for MCP tools.
    
    Provides centralized tool management with:
    - Registration and discovery
    - Schema validation
    - Usage metrics
    - Lifecycle hooks
    
    Example:
        >>> registry = ToolRegistry()
        >>> @registry.tool("search", "Search the web")
        ... def search(query: str) -> str:
        ...     return f"Results for: {query}"
    """
    
    def __init__(self) -> None:
        """Initialize the registry."""
        self._tools: dict[str, MCPTool] = {}
        self._metrics: dict[str, ToolMetrics] = {}
        self._hooks: dict[str, list[Callable]] = {
            "before_call": [],
            "after_call": [],
            "on_error": [],
        }
    
    def register(
        self,
        name: str,
        description: str,
        handler: Callable,
        input_schema: Optional[dict] = None,
        tool_type: ToolType = ToolType.FUNCTION,
        requires_confirmation: bool = False,
    ) -> MCPTool:
        """Register a new tool.
        
        Args:
            name: Tool name.
            description: Tool description.
            handler: The function to execute.
            input_schema: JSON Schema for input parameters.
            tool_type: Type of tool.
            requires_confirmation: Whether user confirmation is needed.
        
        Returns:
            MCPTool: The registered tool.
        """
        # Auto-generate schema from function signature if not provided
        if input_schema is None:
            input_schema = self._generate_schema(handler)
        
        tool = MCPTool(
            name=name,
            description=description,
            handler=handler,
            tool_type=tool_type,
            input_schema=input_schema,
            requires_confirmation=requires_confirmation,
        )
        
        self._tools[name] = tool
        self._metrics[name] = ToolMetrics()
        
        return tool
    
    def tool(
        self,
        name: str,
        description: str,
        **kwargs
    ) -> Callable:
        """Decorator for registering tools.
        
        Args:
            name: Tool name.
            description: Tool description.
            **kwargs: Additional tool options.
        
        Returns:
            Callable: Decorator function.
        
        Example:
            >>> @registry.tool("greet", "Greet someone")
            ... def greet(name: str) -> str:
            ...     return f"Hello, {name}!"
        """
        def decorator(func: Callable) -> Callable:
            self.register(name, description, func, **kwargs)
            return func
        return decorator
    
    def get(self, name: str) -> Optional[MCPTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[MCPTool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_schemas(self, format: str = "openai") -> list[dict]:
        """Get tool schemas in provider format.
        
        Args:
            format: Schema format (openai, claude, generic).
        
        Returns:
            list: Tool schemas.
        """
        schemas = []
        for tool in self._tools.values():
            if format == "claude":
                schemas.append(tool.to_claude_schema())
            elif format == "openai":
                schemas.append(tool.to_openai_schema())
            else:
                schemas.append(tool.to_schema())
        return schemas
    
    async def call(self, name: str, **kwargs) -> Any:
        """Call a registered tool.
        
        Args:
            name: Tool name.
            **kwargs: Tool arguments.
        
        Returns:
            Tool execution result.
        """
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(f"Tool not found: {name}")
        
        metrics = self._metrics[name]
        start_time = datetime.now()
        
        # Before hooks
        for hook in self._hooks["before_call"]:
            hook(name, kwargs)
        
        try:
            result = await tool.execute(**kwargs)
            
            metrics.call_count += 1
            metrics.success_count += 1
            metrics.last_called = datetime.now()
            metrics.total_duration_ms += (datetime.now() - start_time).total_seconds() * 1000
            
            # After hooks
            for hook in self._hooks["after_call"]:
                hook(name, kwargs, result)
            
            return result
            
        except Exception as e:
            metrics.call_count += 1
            metrics.error_count += 1
            
            # Error hooks
            for hook in self._hooks["on_error"]:
                hook(name, kwargs, e)
            
            raise
    
    def get_metrics(self, name: str) -> Optional[ToolMetrics]:
        """Get metrics for a tool."""
        return self._metrics.get(name)
    
    def add_hook(self, event: str, hook: Callable) -> None:
        """Add a lifecycle hook.
        
        Args:
            event: Event name (before_call, after_call, on_error).
            hook: Hook function.
        """
        if event in self._hooks:
            self._hooks[event].append(hook)
    
    def _generate_schema(self, func: Callable) -> dict:
        """Generate JSON Schema from function signature.
        
        Args:
            func: The function to analyze.
        
        Returns:
            dict: JSON Schema for the function parameters.
        """
        sig = inspect.signature(func)
        hints = getattr(func, "__annotations__", {})
        
        properties = {}
        required = []
        
        for name, param in sig.parameters.items():
            if name in ("self", "cls"):
                continue
            
            prop = {"type": "string"}  # Default
            
            # Map Python types to JSON Schema
            hint = hints.get(name)
            if hint:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object",
                }
                json_type = type_map.get(hint, "string")
                prop["type"] = json_type
            
            properties[name] = prop
            
            if param.default is inspect.Parameter.empty:
                required.append(name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


class ResourceRegistry:
    """Registry for MCP resources.
    
    Manages resources that can be accessed by LLMs for context.
    
    Example:
        >>> registry = ResourceRegistry()
        >>> registry.register("file://docs/readme.md", "README", "Project docs")
    """
    
    def __init__(self) -> None:
        """Initialize the registry."""
        self._resources: dict[str, MCPResource] = {}
        self._loaders: dict[str, Callable] = {}
    
    def register(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str = "text/plain",
        content: Optional[str] = None,
        loader: Optional[Callable] = None,
    ) -> MCPResource:
        """Register a resource.
        
        Args:
            uri: Resource URI.
            name: Display name.
            description: Resource description.
            mime_type: MIME type.
            content: Static content.
            loader: Dynamic content loader function.
        
        Returns:
            MCPResource: The registered resource.
        """
        resource = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            content=content,
        )
        
        self._resources[uri] = resource
        
        if loader:
            self._loaders[uri] = loader
        
        return resource
    
    def get(self, uri: str) -> Optional[MCPResource]:
        """Get a resource by URI."""
        return self._resources.get(uri)
    
    def list_resources(self) -> list[MCPResource]:
        """Get all registered resources."""
        return list(self._resources.values())
    
    async def read(self, uri: str) -> str:
        """Read resource content.
        
        Args:
            uri: Resource URI.
        
        Returns:
            str: Resource content.
        """
        resource = self._resources.get(uri)
        if not resource:
            raise KeyError(f"Resource not found: {uri}")
        
        # If there's a dynamic loader, use it
        if uri in self._loaders:
            loader = self._loaders[uri]
            if inspect.iscoroutinefunction(loader):
                content = await loader(uri)
            else:
                content = loader(uri)
            resource.content = content
        
        return resource.content or ""
    
    def register_directory(
        self,
        base_uri: str,
        directory: str,
        pattern: str = "*",
    ) -> list[MCPResource]:
        """Register all files in a directory.
        
        Args:
            base_uri: Base URI prefix.
            directory: Directory path.
            pattern: Glob pattern for files.
        
        Returns:
            list: Registered resources.
        """
        from pathlib import Path
        
        resources = []
        dir_path = Path(directory)
        
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                uri = f"{base_uri}/{file_path.name}"
                resource = self.register(
                    uri=uri,
                    name=file_path.name,
                    description=f"File: {file_path.name}",
                    content=file_path.read_text(encoding="utf-8"),
                )
                resources.append(resource)
        
        return resources


# Global registries for convenience
_tool_registry: Optional[ToolRegistry] = None
_resource_registry: Optional[ResourceRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def get_resource_registry() -> ResourceRegistry:
    """Get the global resource registry."""
    global _resource_registry
    if _resource_registry is None:
        _resource_registry = ResourceRegistry()
    return _resource_registry
