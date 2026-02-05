"""Chat History Sync Agent.

Autonomous agent responsible for managing chat history synchronization
from external providers using the Chat History MCP Server.
"""

import logging
import json
from typing import Optional, Any
from datetime import datetime

from .base import BaseAgent, AgentConfig, AgentResponse, AgentCapability
from ..mcp.chat_history_server import get_chat_history_server

logger = logging.getLogger(__name__)


class ChatHistorySyncAgent(BaseAgent):
    """Agent that manages chat history synchronization."""
    
    def _default_config(self) -> AgentConfig:
        return AgentConfig(
            name="ChatSyncAgent",
            description="Manages synchronization of chat history from external AI providers.",
            capabilities=[
                AgentCapability.API_INTEGRATION,
                AgentCapability.FILE_OPERATIONS,
            ],
            model_name="llama3.2",
            temperature=0.3,  # Lower temperature for reliable tool use
            system_prompt="""You are the Chat History Sync Agent.
            Your responsibility is to ensure JROCK's personal AI has the latest
            conversations from all external providers (OpenAI, Anthropic, Google, Ollama).
            
            You interface with the Chat History MCP Server to triggering syncs,
            monitor status, and ingest new conversations into memory.
            """
        )

    def process(
        self,
        message: str,
        context: Optional[dict] = None
    ) -> AgentResponse:
        """Process requests related to chat sync.
        
        Args:
            message: User command or scheduled trigger.
            context: Additional context.
            
        Returns:
            AgentResponse with sync results.
        """
        message_lower = message.lower()
        server = get_chat_history_server()
        
        try:
            # Handle different intents
            if "status" in message_lower:
                return self._handle_status(server)
            
            elif "sync" in message_lower:
                provider = None
                if "openai" in message_lower:
                    provider = "openai"
                elif "claude" in message_lower or "anthropic" in message_lower:
                    provider = "anthropic"
                elif "gemini" in message_lower or "google" in message_lower:
                    provider = "google"
                elif "ollama" in message_lower:
                    provider = "ollama"
                
                return self._handle_sync(server, provider)
            
            else:
                return AgentResponse(
                    agent_name=self.name,
                    content="I can help you sync chat history or check sync status. "
                           "Try saying 'sync all chats' or 'check sync status'.",
                    success=False
                )
                
        except Exception as e:
            logger.error(f"Error in ChatSyncAgent: {e}")
            return AgentResponse(
                agent_name=self.name,
                content=f"An error occurred: {str(e)}",
                success=False,
                reasoning=str(e)
            )

    def _handle_status(self, server: Any) -> AgentResponse:
        """Handle status check request."""
        # Note: In a real async agent, we'd await this
        # For now we'll assume the server methods are sync or we're running in async context
        import asyncio
        status = asyncio.run(server._get_sync_status())
        
        content = "## Sync Status\n\n"
        
        for provider, info in status.get("providers", {}).items():
            last_sync = info.get("last_sync") or "Never"
            status_emoji = "🟢" if info.get("enabled") else "⚪"
            content += f"{status_emoji} **{provider.title()}**: Last sync: {last_sync}\n"
            
        return AgentResponse(
            agent_name=self.name,
            content=content,
            metadata={"raw_status": status}
        )

    def _handle_sync(self, server: Any, provider: Optional[str]) -> AgentResponse:
        """Handle sync request."""
        import asyncio
        
        if provider:
            result = asyncio.run(server._sync_provider(provider))
            msg = f"Triggered sync for {provider}. Job ID: {result.get('job_id')}"
        else:
            result = asyncio.run(server._sync_all_providers())
            msg = "Triggered sync for all providers."
            
        return AgentResponse(
            agent_name=self.name,
            content=msg,
            metadata={"result": result}
        )
