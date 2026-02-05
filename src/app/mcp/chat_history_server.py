"""Chat History MCP Server.

Exposes chat history retrieval and sync capabilities as MCP tools
for the multi-agent system to use.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from ..mcp.protocol import MCPServer, MCPTool, MCPResource, ToolType
from ..ingest.providers import (
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    OllamaProvider,
    ChatConversation,
    ProviderType,
)
from ..ingest.sync import SyncScheduler, SyncConfig

logger = logging.getLogger(__name__)


class ChatHistoryMCPServer(MCPServer):
    """MCP Server providing chat history sync tools.
    
    Enables agents to retrieve and ingest chat history from
    external AI providers (OpenAI, Anthropic, Google, Ollama).
    
    Example:
        >>> server = ChatHistoryMCPServer()
        >>> tools = server.get_tools()
        >>> result = await server.call_tool("sync_all_providers", {})
    """
    
    def __init__(self) -> None:
        """Initialize the Chat History MCP Server."""
        super().__init__(
            name="chat_history",
            version="1.0.0"
        )
        
        self._sync_config = SyncConfig.default()
        self._scheduler = SyncScheduler(self._sync_config)
        self._last_sync: dict[str, datetime] = {}
        self._sync_results: list[dict[str, Any]] = []
        
        # Register all tools
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all chat history tools."""
        
        # Sync all providers
        self.register_tool(MCPTool(
            name="sync_all_providers",
            description="Sync chat history from all configured AI providers (OpenAI, Anthropic, Google, Ollama). "
                       "Retrieves new conversations and ingests them into the personal AI memory.",
            handler=self._sync_all_providers,
            tool_type=ToolType.FUNCTION,
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ))
        
        # Sync specific provider
        self.register_tool(MCPTool(
            name="sync_provider",
            description="Sync chat history from a specific AI provider.",
            handler=self._sync_provider,
            tool_type=ToolType.FUNCTION,
            input_schema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["openai", "anthropic", "google", "ollama"],
                        "description": "The provider to sync from",
                    },
                },
                "required": ["provider"],
            },
        ))
        
        # Get sync status
        self.register_tool(MCPTool(
            name="get_sync_status",
            description="Get the current sync status including last sync times and results.",
            handler=self._get_sync_status,
            tool_type=ToolType.FUNCTION,
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ))
        
        # Ingest conversations to memory
        self.register_tool(MCPTool(
            name="ingest_conversations",
            description="Process and ingest retrieved conversations into the personal AI memory and vector store.",
            handler=self._ingest_conversations,
            tool_type=ToolType.FUNCTION,
            input_schema={
                "type": "object",
                "properties": {
                    "conversation_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "IDs of conversations to ingest",
                    },
                },
                "required": ["conversation_ids"],
            },
        ))
        
        # Get recent conversations
        self.register_tool(MCPTool(
            name="get_recent_conversations",
            description="Get recently synced conversations from a specific provider.",
            handler=self._get_recent_conversations,
            tool_type=ToolType.FUNCTION,
            input_schema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["openai", "anthropic", "google", "ollama", "all"],
                        "description": "The provider to get conversations from",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of conversations to return",
                        "default": 10,
                    },
                },
                "required": [],
            },
        ))
    
    async def _sync_all_providers(self, **kwargs) -> dict[str, Any]:
        """Sync from all configured providers.
        
        Returns:
            Sync results with counts per provider
        """
        logger.info("Starting sync from all providers")
        results = {}
        
        for provider_type in ProviderType:
            if provider_type == ProviderType.UNKNOWN:
                continue
            
            try:
                result = await self._sync_provider(provider=provider_type.value)
                results[provider_type.value] = result
            except Exception as e:
                logger.error(f"Error syncing {provider_type.value}: {e}")
                results[provider_type.value] = {"error": str(e)}
        
        self._sync_results.append({
            "timestamp": datetime.now().isoformat(),
            "results": results,
        })
        
        return {
            "success": True,
            "providers_synced": list(results.keys()),
            "results": results,
            "synced_at": datetime.now().isoformat(),
        }
    
    async def _sync_provider(self, provider: str, **kwargs) -> dict[str, Any]:
        """Sync from a specific provider.
        
        Args:
            provider: Provider name (openai, anthropic, google, ollama)
            
        Returns:
            Sync result for the provider
        """
        logger.info(f"Syncing from {provider}")
        
        job = self._scheduler.trigger_sync(provider=provider)
        
        self._last_sync[provider] = datetime.now()
        
        return {
            "provider": provider,
            "job_id": job.id,
            "status": job.status.value,
            "success_count": job.success_count,
            "failure_count": job.failure_count,
            "synced_at": datetime.now().isoformat(),
        }
    
    async def _get_sync_status(self, **kwargs) -> dict[str, Any]:
        """Get current sync status.
        
        Returns:
            Status for all providers with last sync times
        """
        status = {}
        
        for provider_type in ProviderType:
            if provider_type == ProviderType.UNKNOWN:
                continue
            
            provider = provider_type.value
            settings = self._sync_config.get_provider_settings(provider)
            
            status[provider] = {
                "enabled": settings.enabled,
                "frequency": settings.frequency.value,
                "last_sync": self._last_sync.get(provider, {}).isoformat() 
                            if provider in self._last_sync else None,
                "watch_paths": [str(p) for p in settings.watch_paths],
            }
        
        recent_jobs = self._scheduler.get_recent_jobs(limit=5)
        
        return {
            "providers": status,
            "recent_jobs": [
                {
                    "id": j.id,
                    "status": j.status.value,
                    "provider": j.provider,
                    "success": j.success_count,
                    "failures": j.failure_count,
                }
                for j in recent_jobs
            ],
        }
    
    async def _ingest_conversations(
        self, 
        conversation_ids: list[str],
        **kwargs
    ) -> dict[str, Any]:
        """Ingest conversations into personal AI memory.
        
        Args:
            conversation_ids: IDs of conversations to ingest
            
        Returns:
            Ingestion result
        """
        # TODO: Integrate with embedding pipeline and consciousness
        # For now, return placeholder
        logger.info(f"Ingesting {len(conversation_ids)} conversations")
        
        return {
            "success": True,
            "conversations_ingested": len(conversation_ids),
            "message": "Conversations queued for ingestion into memory",
        }
    
    async def _get_recent_conversations(
        self,
        provider: str = "all",
        limit: int = 10,
        **kwargs
    ) -> dict[str, Any]:
        """Get recent conversations.
        
        Args:
            provider: Provider filter or "all"
            limit: Maximum results
            
        Returns:
            List of recent conversations
        """
        # TODO: Query from vector store
        # For now, return placeholder
        return {
            "provider": provider,
            "limit": limit,
            "conversations": [],
            "message": "Query pending vector store integration",
        }


# Singleton instance
_chat_history_server: Optional[ChatHistoryMCPServer] = None


def get_chat_history_server() -> ChatHistoryMCPServer:
    """Get or create the Chat History MCP Server singleton."""
    global _chat_history_server
    if _chat_history_server is None:
        _chat_history_server = ChatHistoryMCPServer()
    return _chat_history_server
