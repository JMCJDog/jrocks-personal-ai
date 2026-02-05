"""Anthropic/Claude chat history provider.

Parses chat exports from Claude in the following formats:
- ZIP archive from data export
- JSON conversation files
"""

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .base_provider import (
    ChatConversation,
    ChatHistoryProvider,
    ChatMessage,
    ProviderType,
)


class AnthropicProvider(ChatHistoryProvider):
    """Parser for Anthropic Claude chat exports.
    
    Claude exports typically contain:
    - conversations.json: All conversation data
    - User metadata and settings
    """
    
    provider_type = ProviderType.ANTHROPIC
    
    def get_supported_formats(self) -> list[str]:
        """Supported file formats for Claude exports."""
        return [".zip", ".json"]
    
    def can_parse(self, path: Path) -> bool:
        """Check if path contains a Claude export.
        
        Args:
            path: Path to check
            
        Returns:
            True if this looks like a Claude export
        """
        if path.suffix == ".zip":
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    names = zf.namelist()
                    # Look for Claude-specific files
                    return any(
                        "conversation" in n.lower() or "claude" in n.lower()
                        for n in names
                    )
            except zipfile.BadZipFile:
                return False
        elif path.suffix == ".json":
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Check for Claude conversation structure
                    if isinstance(data, list) and len(data) > 0:
                        first = data[0]
                        return "uuid" in first or "chat_messages" in first
                    elif isinstance(data, dict):
                        return "conversations" in data or "chat_messages" in data
            except (json.JSONDecodeError, KeyError):
                return False
        return False
    
    def parse(self, path: Path) -> list[ChatConversation]:
        """Parse Claude export into conversations.
        
        Args:
            path: Path to ZIP or JSON file
            
        Returns:
            List of parsed conversations
        """
        if path.suffix == ".zip":
            return self._parse_zip(path)
        elif path.suffix == ".json":
            return self._parse_json(path)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")
    
    def _parse_zip(self, path: Path) -> list[ChatConversation]:
        """Extract and parse conversations from ZIP archive."""
        with zipfile.ZipFile(path, "r") as zf:
            # Find the conversations file
            conv_file = None
            for name in zf.namelist():
                if "conversation" in name.lower() and name.endswith(".json"):
                    conv_file = name
                    break
            
            if not conv_file:
                raise ValueError("No conversations file found in Claude export")
            
            with zf.open(conv_file) as f:
                data = json.load(f)
        
        return self._normalize_conversations(data)
    
    def _parse_json(self, path: Path) -> list[ChatConversation]:
        """Parse conversations from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._normalize_conversations(data)
    
    def _normalize_conversations(
        self, data: list[dict[str, Any]] | dict[str, Any]
    ) -> list[ChatConversation]:
        """Convert Claude format to normalized ChatConversation objects."""
        # Handle both list and dict formats
        if isinstance(data, dict):
            conv_list = data.get("conversations", [data])
        else:
            conv_list = data
        
        conversations = []
        
        for conv_data in conv_list:
            messages = self._extract_messages(conv_data)
            
            # Parse timestamps - Claude may use ISO format or Unix timestamps
            created = conv_data.get("created_at") or conv_data.get("created")
            updated = conv_data.get("updated_at") or conv_data.get("updated")
            
            created_dt = self._parse_timestamp(created)
            updated_dt = self._parse_timestamp(updated)
            
            conversation = ChatConversation(
                id=conv_data.get("uuid", conv_data.get("id", "")),
                provider=ProviderType.ANTHROPIC,
                title=conv_data.get("name") or conv_data.get("title"),
                messages=messages,
                created_at=created_dt or datetime.now(),
                updated_at=updated_dt or datetime.now(),
                metadata={
                    "project_uuid": conv_data.get("project_uuid"),
                    "account_uuid": conv_data.get("account_uuid"),
                },
            )
            conversations.append(conversation)
        
        return conversations
    
    def _extract_messages(self, conv_data: dict[str, Any]) -> list[ChatMessage]:
        """Extract messages from Claude conversation data."""
        messages = []
        msg_list = conv_data.get("chat_messages", [])
        
        for msg_data in msg_list:
            sender = msg_data.get("sender", "")
            
            # Map Claude roles to standard roles
            if sender == "human":
                role = "user"
            elif sender == "assistant":
                role = "assistant"
            else:
                continue
            
            # Claude stores content in 'text' or 'content' field
            text_content = msg_data.get("text", "") or msg_data.get("content", "")
            
            # Handle structured content (list of content blocks)
            if isinstance(text_content, list):
                text_parts = []
                for block in text_content:
                    if isinstance(block, str):
                        text_parts.append(block)
                    elif isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                text_content = "\n".join(text_parts)
            
            if not text_content.strip():
                continue
            
            created = msg_data.get("created_at") or msg_data.get("timestamp")
            
            messages.append(ChatMessage(
                role=role,
                content=text_content,
                timestamp=self._parse_timestamp(created),
                model=msg_data.get("model"),
                attachments=msg_data.get("attachments", []) or [],
                metadata={
                    "uuid": msg_data.get("uuid"),
                },
            ))
        
        return messages
    
    def _parse_timestamp(self, ts: str | int | float | None) -> datetime | None:
        """Parse timestamp from various formats."""
        if ts is None:
            return None
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts)
        if isinstance(ts, str):
            try:
                # Try ISO format
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
