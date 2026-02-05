"""MCP Protocol - Core types and message handling.

Implements the Model Context Protocol specification for
AI assistant communication with tools and resources.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid


class MessageType(str, Enum):
    """MCP message types."""
    
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class ToolType(str, Enum):
    """Types of tools available."""
    
    FUNCTION = "function"
    RETRIEVAL = "retrieval"
    CODE_EXECUTION = "code_execution"
    WEB_SEARCH = "web_search"


@dataclass
class MCPMessage:
    """A message in the MCP protocol.
    
    Follows the JSON-RPC 2.0 structure used by MCP.
    """
    
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[dict] = None
    result: Optional[Any] = None
    error: Optional[dict] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    @classmethod
    def request(cls, method: str, params: Optional[dict] = None) -> "MCPMessage":
        """Create a request message."""
        return cls(method=method, params=params or {})
    
    @classmethod
    def response(cls, id: str, result: Any) -> "MCPMessage":
        """Create a response message."""
        return cls(id=id, result=result)
    
    @classmethod
    def error_response(cls, id: str, code: int, message: str) -> "MCPMessage":
        """Create an error response."""
        return cls(id=id, error={"code": code, "message": message})
    
    @classmethod
    def notification(cls, method: str, params: Optional[dict] = None) -> "MCPMessage":
        """Create a notification (no response expected)."""
        return cls(id=None, method=method, params=params or {})
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = {"jsonrpc": self.jsonrpc}
        if self.id:
            d["id"] = self.id
        if self.method:
            d["method"] = self.method
        if self.params:
            d["params"] = self.params
        if self.result is not None:
            d["result"] = self.result
        if self.error:
            d["error"] = self.error
        return d
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, data: str) -> "MCPMessage":
        """Parse from JSON string."""
        return cls.from_dict(json.loads(data))
    
    @classmethod
    def from_dict(cls, data: dict) -> "MCPMessage":
        """Parse from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )


@dataclass
class MCPTool:
    """Definition of an MCP tool.
    
    Tools are functions that can be called by the LLM.
    """
    
    name: str
    description: str
    handler: Callable
    tool_type: ToolType = ToolType.FUNCTION
    input_schema: dict = field(default_factory=dict)
    output_schema: Optional[dict] = None
    requires_confirmation: bool = False
    metadata: dict = field(default_factory=dict)
    
    def to_schema(self) -> dict:
        """Convert to tool schema for LLM providers."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }
    
    def to_claude_schema(self) -> dict:
        """Convert to Claude's tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
    
    def to_openai_schema(self) -> dict:
        """Convert to OpenAI's function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }
    
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given arguments."""
        if asyncio.iscoroutinefunction(self.handler):
            return await self.handler(**kwargs)
        return self.handler(**kwargs)


@dataclass
class MCPResource:
    """A resource that can be accessed by the LLM.
    
    Resources provide context (documents, data, etc.) to the model.
    """
    
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    content: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
            "metadata": self.metadata,
        }


class MCPServer(ABC):
    """Abstract MCP server that exposes tools and resources.
    
    Subclass this to create custom MCP servers.
    
    Example:
        >>> class MyServer(MCPServer):
        ...     def get_tools(self) -> list[MCPTool]:
        ...         return [MCPTool(...)]
    """
    
    def __init__(self, name: str, version: str = "1.0.0") -> None:
        """Initialize the server.
        
        Args:
            name: Server name.
            version: Server version.
        """
        self.name = name
        self.version = version
        self._tools: dict[str, MCPTool] = {}
        self._resources: dict[str, MCPResource] = {}
    
    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool with the server."""
        self._tools[tool.name] = tool
    
    def register_resource(self, resource: MCPResource) -> None:
        """Register a resource with the server."""
        self._resources[resource.uri] = resource
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_resource(self, uri: str) -> Optional[MCPResource]:
        """Get a resource by URI."""
        return self._resources.get(uri)
    
    @abstractmethod
    def get_tools(self) -> list[MCPTool]:
        """Return all available tools."""
        pass
    
    @abstractmethod
    def get_resources(self) -> list[MCPResource]:
        """Return all available resources."""
        pass
    
    async def handle_message(self, message: MCPMessage) -> MCPMessage:
        """Handle an incoming MCP message.
        
        Args:
            message: The incoming message.
        
        Returns:
            MCPMessage: The response.
        """
        method = message.method
        
        if method == "initialize":
            return self._handle_initialize(message)
        elif method == "tools/list":
            return self._handle_tools_list(message)
        elif method == "tools/call":
            return await self._handle_tool_call(message)
        elif method == "resources/list":
            return self._handle_resources_list(message)
        elif method == "resources/read":
            return self._handle_resource_read(message)
        else:
            return MCPMessage.error_response(
                message.id, -32601, f"Method not found: {method}"
            )
    
    def _handle_initialize(self, message: MCPMessage) -> MCPMessage:
        """Handle initialization request."""
        return MCPMessage.response(message.id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
            "capabilities": {
                "tools": {},
                "resources": {},
            }
        })
    
    def _handle_tools_list(self, message: MCPMessage) -> MCPMessage:
        """Handle tools/list request."""
        tools = [t.to_schema() for t in self.get_tools()]
        return MCPMessage.response(message.id, {"tools": tools})
    
    async def _handle_tool_call(self, message: MCPMessage) -> MCPMessage:
        """Handle tools/call request."""
        params = message.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        tool = self.get_tool(tool_name)
        if not tool:
            return MCPMessage.error_response(
                message.id, -32602, f"Tool not found: {tool_name}"
            )
        
        try:
            result = await tool.execute(**arguments)
            return MCPMessage.response(message.id, {
                "content": [{"type": "text", "text": str(result)}]
            })
        except Exception as e:
            return MCPMessage.error_response(
                message.id, -32603, f"Tool execution failed: {str(e)}"
            )
    
    def _handle_resources_list(self, message: MCPMessage) -> MCPMessage:
        """Handle resources/list request."""
        resources = [r.to_dict() for r in self.get_resources()]
        return MCPMessage.response(message.id, {"resources": resources})
    
    def _handle_resource_read(self, message: MCPMessage) -> MCPMessage:
        """Handle resources/read request."""
        params = message.params or {}
        uri = params.get("uri")
        
        resource = self.get_resource(uri)
        if not resource:
            return MCPMessage.error_response(
                message.id, -32602, f"Resource not found: {uri}"
            )
        
        return MCPMessage.response(message.id, {
            "contents": [{
                "uri": resource.uri,
                "mimeType": resource.mime_type,
                "text": resource.content,
            }]
        })


class MCPClient:
    """Client for connecting to MCP servers.
    
    Provides a unified interface for consuming MCP services.
    
    Example:
        >>> client = MCPClient()
        >>> tools = await client.list_tools()
        >>> result = await client.call_tool("search", {"query": "..."})
    """
    
    def __init__(self, transport: Optional["Transport"] = None) -> None:
        """Initialize the client.
        
        Args:
            transport: Transport layer for communication.
        """
        self.transport = transport
        self._initialized = False
        self._server_info: Optional[dict] = None
    
    async def initialize(self) -> dict:
        """Initialize connection with the server."""
        if self.transport is None:
            raise RuntimeError("Transport not configured")
        
        message = MCPMessage.request("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {
                "name": "JRocksAI-Client",
                "version": "1.0.0"
            }
        })
        
        response = await self.transport.send(message)
        self._server_info = response.result
        self._initialized = True
        return self._server_info
    
    async def list_tools(self) -> list[dict]:
        """Get list of available tools from the server."""
        message = MCPMessage.request("tools/list")
        response = await self.transport.send(message)
        return response.result.get("tools", [])
    
    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Call a tool on the server.
        
        Args:
            name: Tool name.
            arguments: Tool arguments.
        
        Returns:
            Tool execution result.
        """
        message = MCPMessage.request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        response = await self.transport.send(message)
        
        if response.error:
            raise RuntimeError(f"Tool error: {response.error}")
        
        content = response.result.get("content", [])
        if content and content[0].get("type") == "text":
            return content[0].get("text")
        return response.result
    
    async def list_resources(self) -> list[dict]:
        """Get list of available resources."""
        message = MCPMessage.request("resources/list")
        response = await self.transport.send(message)
        return response.result.get("resources", [])
    
    async def read_resource(self, uri: str) -> str:
        """Read a resource's content.
        
        Args:
            uri: Resource URI.
        
        Returns:
            Resource content.
        """
        message = MCPMessage.request("resources/read", {"uri": uri})
        response = await self.transport.send(message)
        
        contents = response.result.get("contents", [])
        if contents:
            return contents[0].get("text", "")
        return ""


# Import asyncio for async execution
import asyncio
