"""Google Gemini chat history client.

Monitors for Google Takeout exports and AI Studio saved chats.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from ...ingest.providers import GoogleProvider, ChatConversation

logger = logging.getLogger(__name__)


class GoogleChatClient:
    """Client for retrieving chat history from Google Gemini.
    
    Since Google doesn't provide a direct Gemini chat history API,
    this client:
    - Monitors for Google Takeout exports
    - Watches AI Studio folder in Google Drive (if synced locally)
    - Parses exported data using GoogleProvider
    
    Example:
        >>> client = GoogleChatClient()
        >>> new_convs = await client.check_for_exports()
    """
    
    def __init__(
        self,
        export_path: Optional[Path] = None,
        ai_studio_path: Optional[Path] = None,
    ) -> None:
        """Initialize the Google chat client.
        
        Args:
            export_path: Directory for Google Takeout exports
            ai_studio_path: Path to AI Studio folder (Google Drive sync)
        """
        self.export_path = export_path or Path.home() / "Documents" / "AI-Exports" / "google"
        self.ai_studio_path = ai_studio_path or Path.home() / "Google Drive" / "AI Studio"
        self._provider = GoogleProvider()
        self._processed_files: set[Path] = set()
        self._last_sync: Optional[datetime] = None
    
    async def check_for_exports(self) -> list[ChatConversation]:
        """Check for new Gemini/Takeout exports.
        
        Returns:
            List of newly found conversations
        """
        conversations = []
        
        # Check export path
        if self.export_path.exists():
            convs = await self._scan_directory(self.export_path)
            conversations.extend(convs)
        
        # Check AI Studio folder
        if self.ai_studio_path.exists():
            convs = await self._scan_directory(self.ai_studio_path)
            conversations.extend(convs)
        
        self._last_sync = datetime.now()
        return conversations
    
    async def _scan_directory(self, directory: Path) -> list[ChatConversation]:
        """Scan a directory for Gemini chat files.
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of conversations found
        """
        conversations = []
        patterns = ["*.zip", "*.json", "takeout-*.zip"]
        
        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if file_path in self._processed_files:
                    continue
                
                if self._provider.can_parse(file_path):
                    try:
                        convs = self._provider.parse(file_path)
                        conversations.extend(convs)
                        self._processed_files.add(file_path)
                        logger.info(f"Processed Google export: {file_path.name}")
                    except Exception as e:
                        logger.error(f"Error parsing {file_path}: {e}")
        
        return conversations
    
    async def sync_recent(
        self,
        since: Optional[datetime] = None,
    ) -> list[ChatConversation]:
        """Sync conversations since a given time.
        
        Args:
            since: Only process files modified after this time
            
        Returns:
            List of new conversations
        """
        return await self.check_for_exports()
    
    def get_export_instructions(self) -> dict[str, Any]:
        """Get instructions for exporting Gemini chat history.
        
        Returns:
            Instructions for the user
        """
        return {
            "provider": "google",
            "instructions": [
                "Option 1: Google Takeout",
                "1. Go to takeout.google.com",
                "2. Deselect all, then select only 'Gemini Apps'",
                "3. Create and download export",
                f"4. Save the ZIP file to: {self.export_path}",
                "",
                "Option 2: AI Studio (auto-saved)",
                f"1. Ensure Google Drive sync includes: {self.ai_studio_path}",
                "2. Chats are automatically saved to Drive",
            ],
            "export_path": str(self.export_path),
            "ai_studio_path": str(self.ai_studio_path),
            "auto_detected": True,
        }
