"""Anthropic/Claude chat history client.

Since Anthropic doesn't provide a direct API for historical chat export,
this client monitors for data exports and processes them automatically.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from ...ingest.providers import AnthropicProvider, ChatConversation

logger = logging.getLogger(__name__)


class AnthropicChatClient:
    """Client for retrieving chat history from Anthropic/Claude.
    
    Since Anthropic doesn't offer a direct chat history API,
    this client:
    - Monitors for data export files
    - Parses exported data using AnthropicProvider
    - Tracks what has been processed
    
    Example:
        >>> client = AnthropicChatClient()
        >>> new_convs = await client.check_for_exports()
    """
    
    def __init__(
        self,
        export_path: Optional[Path] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """Initialize the Anthropic chat client.
        
        Args:
            export_path: Directory to watch for exports
            api_key: Anthropic API key (for future API-based features)
        """
        self.export_path = export_path or Path.home() / "Documents" / "AI-Exports" / "anthropic"
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._provider = AnthropicProvider()
        self._processed_files: set[Path] = set()
        self._last_sync: Optional[datetime] = None
    
    async def check_for_exports(self) -> list[ChatConversation]:
        """Check for new Claude data exports.
        
        Returns:
            List of newly found conversations
        """
        conversations = []
        
        if not self.export_path.exists():
            logger.debug(f"Export path does not exist: {self.export_path}")
            return conversations
        
        # Look for export files
        patterns = ["*.zip", "*.json"]
        
        for pattern in patterns:
            for file_path in self.export_path.glob(pattern):
                if file_path in self._processed_files:
                    continue
                
                if self._provider.can_parse(file_path):
                    try:
                        convs = self._provider.parse(file_path)
                        conversations.extend(convs)
                        self._processed_files.add(file_path)
                        logger.info(f"Processed Claude export: {file_path.name}")
                    except Exception as e:
                        logger.error(f"Error parsing {file_path}: {e}")
        
        self._last_sync = datetime.now()
        return conversations
    
    async def sync_recent(
        self,
        since: Optional[datetime] = None,
    ) -> list[ChatConversation]:
        """Sync conversations since a given time.
        
        For Anthropic, this checks for new export files.
        
        Args:
            since: Only process files modified after this time
            
        Returns:
            List of new conversations
        """
        return await self.check_for_exports()
    
    def get_export_instructions(self) -> dict[str, Any]:
        """Get instructions for exporting Claude chat history.
        
        Returns:
            Instructions for the user
        """
        return {
            "provider": "anthropic",
            "instructions": [
                "1. Go to claude.ai/settings",
                "2. Click 'Privacy'",
                "3. Click 'Export data'",
                "4. Wait for email with download link",
                f"5. Save the ZIP file to: {self.export_path}",
            ],
            "export_path": str(self.export_path),
            "auto_detected": True,
        }
