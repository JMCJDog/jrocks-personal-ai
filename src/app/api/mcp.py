"""MCP API Router - REST endpoints for MCP integration.

Provides HTTP access to MCP tools, resources, and LLM providers.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


# Request/Response Models
class ChatRequest(BaseModel):
    """Chat request with optional tool use."""
    message: str = Field(..., description="User message")
    use_tools: bool = Field(default=True, description="Enable tool use")
    provider: Optional[str] = Field(default=None, description="LLM provider override")
    system_prompt: Optional[str] = Field(default=None, description="System prompt")


class ChatResponse(BaseModel):
    """Chat response."""
    content: str
    provider: str
    tools_used: list[str] = Field(default_factory=list)


class ToolCallRequest(BaseModel):
    """Direct tool call request."""
    name: str = Field(..., description="Tool name")
    arguments: dict = Field(default_factory=dict, description="Tool arguments")


class ToolCallResponse(BaseModel):
    """Tool call response."""
    name: str
    result: str
    success: bool


class ProviderListResponse(BaseModel):
    """List of available providers."""
    providers: list[dict]


class ToolListResponse(BaseModel):
    """List of available tools."""
    tools: list[dict]


class ResourceListResponse(BaseModel):
    """List of available resources."""
    resources: list[dict]


# Create router
router = APIRouter(prefix="/api/mcp", tags=["mcp"])


# Lazy-loaded service
_mcp_service = None


def get_service():
    """Get or create MCP service."""
    global _mcp_service
    if _mcp_service is None:
        from ..mcp.service import MCPService
        _mcp_service = MCPService()
    return _mcp_service


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers():
    """List available LLM providers."""
    providers = [
        {
            "name": "claude",
            "display_name": "Anthropic Claude",
            "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            "requires_api_key": True,
        },
        {
            "name": "openai",
            "display_name": "OpenAI GPT",
            "models": ["gpt-4o", "gpt-4-turbo", "gpt-4"],
            "requires_api_key": True,
        },
        {
            "name": "gemini",
            "display_name": "Google Gemini",
            "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            "requires_api_key": True,
        },
        {
            "name": "ollama",
            "display_name": "Ollama (Local)",
            "models": ["llama3.2", "llama3.1", "mistral", "codellama"],
            "requires_api_key": False,
        },
    ]
    return ProviderListResponse(providers=providers)


@router.get("/tools", response_model=ToolListResponse)
async def list_tools():
    """List registered tools."""
    service = get_service()
    tools = []
    
    for tool in service._tool_registry.list_tools():
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
            "type": tool.tool_type.value,
        })
    
    return ToolListResponse(tools=tools)


@router.get("/resources", response_model=ResourceListResponse)
async def list_resources():
    """List registered resources."""
    service = get_service()
    resources = []
    
    for resource in service._resource_registry.list_resources():
        resources.append({
            "uri": resource.uri,
            "name": resource.name,
            "description": resource.description,
            "mime_type": resource.mime_type,
        })
    
    return ResourceListResponse(resources=resources)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message with optional tool use.
    
    The service will automatically handle tool calls and
    generate a complete response.
    """
    service = get_service()
    
    # Set provider if specified
    if request.provider:
        try:
            service.set_provider(request.provider)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {str(e)}")
    
    # Set system prompt if specified
    if request.system_prompt:
        service.add_system_message(request.system_prompt)
    
    try:
        response = await service.chat(
            request.message,
            use_tools=request.use_tools,
        )
        
        return ChatResponse(
            content=response,
            provider=service.provider.provider_type.value,
            tools_used=[],  # Could track this in service
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """Directly call a registered tool."""
    service = get_service()
    
    try:
        result = await service._tool_registry.call(
            request.name,
            **request.arguments
        )
        
        return ToolCallResponse(
            name=request.name,
            result=str(result),
            success=True,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Tool not found: {request.name}")
    except Exception as e:
        return ToolCallResponse(
            name=request.name,
            result=str(e),
            success=False,
        )


@router.post("/conversation/clear")
async def clear_conversation():
    """Clear the conversation history."""
    service = get_service()
    service.clear_conversation()
    return {"status": "cleared"}


@router.post("/provider/set")
async def set_provider(provider: str, api_key: Optional[str] = None):
    """Set the active LLM provider.
    
    Args:
        provider: Provider name (claude, openai, gemini, ollama).
        api_key: Optional API key.
    """
    service = get_service()
    
    try:
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        
        service.set_provider(provider, **kwargs)
        
        return {
            "status": "ok",
            "provider": provider,
            "model": service.provider.config.model,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
