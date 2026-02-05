"""Google Gemini chat history provider.

Parses chat exports from Google Gemini/Bard via Google Takeout:
- ZIP archive from Google Takeout containing Gemini activity
- JSON conversation files from AI Studio
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


class GoogleProvider(ChatHistoryProvider):
    """Parser for Google Gemini/Bard chat exports.
    
    Supports:
    - Google Takeout exports (ZIP with Gemini folder)
    - AI Studio exports (JSON files)
    """
    
    provider_type = ProviderType.GOOGLE
    
    def get_supported_formats(self) -> list[str]:
        """Supported file formats for Gemini exports."""
        return [".zip", ".json"]
    
    def can_parse(self, path: Path) -> bool:
        """Check if path contains a Gemini export.
        
        Args:
            path: Path to check
            
        Returns:
            True if this looks like a Gemini/Google export
        """
        if path.suffix == ".zip":
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    names = zf.namelist()
                    # Look for Google Takeout Gemini structure
                    return any(
                        "gemini" in n.lower() or "bard" in n.lower()
                        for n in names
                    )
            except zipfile.BadZipFile:
                return False
        elif path.suffix == ".json":
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Check for Gemini conversation structure
                    if isinstance(data, dict):
                        return "conversations" in data or "contents" in data
                    if isinstance(data, list) and len(data) > 0:
                        return "parts" in data[0] or "role" in data[0]
            except (json.JSONDecodeError, KeyError):
                return False
        return False
    
    def parse(self, path: Path) -> list[ChatConversation]:
        """Parse Gemini export into conversations.
        
        Args:
            path: Path to ZIP or JSON file
            
        Returns:
            List of parsed conversations
        """
        if path.suffix == ".zip":
            return self._parse_takeout_zip(path)
        elif path.suffix == ".json":
            return self._parse_json(path)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")
    
    def _parse_takeout_zip(self, path: Path) -> list[ChatConversation]:
        """Extract and parse conversations from Google Takeout ZIP."""
        conversations = []
        
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                # Find Gemini/Bard JSON files
                if ("gemini" in name.lower() or "bard" in name.lower()) and \
                   name.endswith(".json"):
                    with zf.open(name) as f:
                        try:
                            data = json.load(f)
                            convs = self._normalize_conversations(data, name)
                            conversations.extend(convs)
                        except json.JSONDecodeError:
                            continue
        
        return conversations
    
    def _parse_json(self, path: Path) -> list[ChatConversation]:
        """Parse conversations from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._normalize_conversations(data, path.name)
    
    def _normalize_conversations(
        self, data: dict[str, Any] | list[dict[str, Any]], source: str
    ) -> list[ChatConversation]:
        """Convert Gemini format to normalized ChatConversation objects."""
        # Handle AI Studio format (single conversation in contents array)
        if isinstance(data, dict) and "contents" in data:
            return [self._parse_ai_studio_format(data, source)]
        
        # Handle Takeout format (activity log structure)
        if isinstance(data, list):
            return self._parse_activity_log(data, source)
        
        # Handle conversations list
        if isinstance(data, dict) and "conversations" in data:
            return [
                self._parse_single_conversation(c)
                for c in data["conversations"]
            ]
        
        return []
    
    def _parse_ai_studio_format(
        self, data: dict[str, Any], source: str
    ) -> ChatConversation:
        """Parse AI Studio conversation format."""
        messages = []
        contents = data.get("contents", [])
        
        for content in contents:
            role = content.get("role", "user")
            # Map Gemini role names
            if role == "model":
                role = "assistant"
            
            parts = content.get("parts", [])
            text_parts = []
            for part in parts:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
            
            text_content = "\n".join(text_parts)
            if text_content.strip():
                messages.append(ChatMessage(
                    role=role,
                    content=text_content,
                    model=data.get("generationConfig", {}).get("model"),
                ))
        
        return ChatConversation(
            id=source.replace("/", "_").replace(".json", ""),
            provider=ProviderType.GOOGLE,
            title=data.get("title"),
            messages=messages,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"source_file": source},
        )
    
    def _parse_activity_log(
        self, data: list[dict[str, Any]], source: str
    ) -> list[ChatConversation]:
        """Parse Google activity log format from Takeout."""
        conversations = []
        
        for idx, activity in enumerate(data):
            messages = []
            
            # Activity entries typically have query and response
            query = activity.get("query") or activity.get("prompt")
            response = activity.get("response") or activity.get("answer")
            
            if query:
                messages.append(ChatMessage(
                    role="user",
                    content=query if isinstance(query, str) else str(query),
                    timestamp=self._parse_timestamp(activity.get("time")),
                ))
            
            if response:
                messages.append(ChatMessage(
                    role="assistant",
                    content=response if isinstance(response, str) else str(response),
                    timestamp=self._parse_timestamp(activity.get("time")),
                ))
            
            if messages:
                conv = ChatConversation(
                    id=f"{source}_{idx}",
                    provider=ProviderType.GOOGLE,
                    title=activity.get("title") or (query[:50] + "..." if query and len(query) > 50 else query),
                    messages=messages,
                    created_at=self._parse_timestamp(activity.get("time")) or datetime.now(),
                    updated_at=datetime.now(),
                    metadata={"products": activity.get("products", [])},
                )
                conversations.append(conv)
        
        return conversations
    
    def _parse_single_conversation(
        self, conv_data: dict[str, Any]
    ) -> ChatConversation:
        """Parse a single conversation object."""
        messages = []
        
        for msg in conv_data.get("messages", []):
            role = msg.get("role", "user")
            if role == "model":
                role = "assistant"
            
            content = msg.get("content", "") or msg.get("text", "")
            if content.strip():
                messages.append(ChatMessage(
                    role=role,
                    content=content,
                    timestamp=self._parse_timestamp(msg.get("timestamp")),
                ))
        
        return ChatConversation(
            id=conv_data.get("id", ""),
            provider=ProviderType.GOOGLE,
            title=conv_data.get("title"),
            messages=messages,
            created_at=self._parse_timestamp(conv_data.get("created")) or datetime.now(),
            updated_at=self._parse_timestamp(conv_data.get("updated")) or datetime.now(),
        )
    
    def _parse_timestamp(self, ts: str | int | float | None) -> datetime | None:
        """Parse timestamp from various formats."""
        if ts is None:
            return None
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts)
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
