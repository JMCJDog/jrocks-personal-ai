"""OpenAI/ChatGPT chat history provider.

Parses chat exports from ChatGPT in the following formats:
- ZIP archive containing conversations.json and chat.html
- Direct conversations.json file
- chat.html file
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


class OpenAIProvider(ChatHistoryProvider):
    """Parser for OpenAI ChatGPT chat exports.
    
    ChatGPT exports come as a ZIP file containing:
    - conversations.json: Structured conversation data
    - chat.html: Human-readable HTML version
    - user.json: User account information
    - message_feedback.json: Thumbs up/down feedback
    """
    
    provider_type = ProviderType.OPENAI
    
    def get_supported_formats(self) -> list[str]:
        """Supported file formats for ChatGPT exports."""
        return [".zip", ".json"]
    
    def can_parse(self, path: Path) -> bool:
        """Check if path contains a ChatGPT export.
        
        Args:
            path: Path to check
            
        Returns:
            True if this looks like a ChatGPT export
        """
        if path.suffix == ".zip":
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    return "conversations.json" in zf.namelist()
            except zipfile.BadZipFile:
                return False
        elif path.suffix == ".json":
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Check for ChatGPT conversation structure
                    if isinstance(data, list) and len(data) > 0:
                        return "mapping" in data[0] or "title" in data[0]
            except (json.JSONDecodeError, KeyError):
                return False
        return False
    
    def parse(self, path: Path) -> list[ChatConversation]:
        """Parse ChatGPT export into conversations.
        
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
            with zf.open("conversations.json") as f:
                data = json.load(f)
        return self._normalize_conversations(data)
    
    def _parse_json(self, path: Path) -> list[ChatConversation]:
        """Parse conversations from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._normalize_conversations(data)
    
    def _normalize_conversations(
        self, data: list[dict[str, Any]]
    ) -> list[ChatConversation]:
        """Convert ChatGPT format to normalized ChatConversation objects."""
        conversations = []
        
        for conv_data in data:
            messages = self._extract_messages(conv_data)
            
            # Parse timestamps
            create_time = conv_data.get("create_time")
            update_time = conv_data.get("update_time")
            
            conversation = ChatConversation(
                id=conv_data.get("id", conv_data.get("conversation_id", "")),
                provider=ProviderType.OPENAI,
                title=conv_data.get("title"),
                messages=messages,
                created_at=datetime.fromtimestamp(create_time) if create_time else datetime.now(),
                updated_at=datetime.fromtimestamp(update_time) if update_time else datetime.now(),
                metadata={
                    "model_slug": conv_data.get("default_model_slug"),
                    "plugin_ids": conv_data.get("plugin_ids", []),
                    "gizmo_id": conv_data.get("gizmo_id"),
                },
            )
            conversations.append(conversation)
        
        return conversations
    
    def _extract_messages(self, conv_data: dict[str, Any]) -> list[ChatMessage]:
        """Extract messages from ChatGPT conversation mapping."""
        messages = []
        mapping = conv_data.get("mapping", {})
        
        # ChatGPT uses a tree structure, we need to follow the chain
        for node_id, node in mapping.items():
            msg_data = node.get("message")
            if not msg_data:
                continue
            
            author = msg_data.get("author", {})
            role = author.get("role", "")
            
            # Skip system messages and tool calls for now
            if role not in ["user", "assistant"]:
                continue
            
            content = msg_data.get("content", {})
            parts = content.get("parts", [])
            text_content = " ".join(
                p for p in parts if isinstance(p, str)
            )
            
            if not text_content.strip():
                continue
            
            create_time = msg_data.get("create_time")
            
            messages.append(ChatMessage(
                role=role,
                content=text_content,
                timestamp=datetime.fromtimestamp(create_time) if create_time else None,
                model=msg_data.get("metadata", {}).get("model_slug"),
                metadata={
                    "message_id": msg_data.get("id"),
                    "status": msg_data.get("status"),
                },
            ))
        
        # Sort by timestamp
        messages.sort(key=lambda m: m.timestamp or datetime.min)
        return messages
