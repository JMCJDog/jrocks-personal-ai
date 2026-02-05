"""Ollama local chat history provider.

Parses chat history from local Ollama conversations stored in:
- ~/.ollama/history (if available)
- Custom log directories
- JSON exports from Ollama-compatible UIs
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .base_provider import (
    ChatConversation,
    ChatHistoryProvider,
    ChatMessage,
    ProviderType,
)


class OllamaProvider(ChatHistoryProvider):
    """Parser for local Ollama chat history.
    
    Ollama doesn't have a standardized export format, so this provider
    supports common patterns from Ollama-compatible applications:
    - Open WebUI exports
    - Custom JSON chat logs
    - JSONL streaming logs
    """
    
    provider_type = ProviderType.OLLAMA
    
    def get_supported_formats(self) -> list[str]:
        """Supported file formats for Ollama exports."""
        return [".json", ".jsonl"]
    
    def can_parse(self, path: Path) -> bool:
        """Check if path contains Ollama chat data.
        
        Args:
            path: Path to check
            
        Returns:
            True if this looks like Ollama data
        """
        if path.suffix == ".jsonl":
            try:
                with open(path, "r", encoding="utf-8") as f:
                    first_line = f.readline()
                    data = json.loads(first_line)
                    # Check for Ollama-style message structure
                    return "model" in data or "prompt" in data or "response" in data
            except (json.JSONDecodeError, KeyError):
                return False
        elif path.suffix == ".json":
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Check for Open WebUI or similar export structure
                    if isinstance(data, dict):
                        return "chat" in data or "messages" in data or "history" in data
                    if isinstance(data, list) and len(data) > 0:
                        first = data[0]
                        return "model" in first or ("role" in first and "content" in first)
            except (json.JSONDecodeError, KeyError):
                return False
        return False
    
    def parse(self, path: Path) -> list[ChatConversation]:
        """Parse Ollama chat data into conversations.
        
        Args:
            path: Path to JSON or JSONL file
            
        Returns:
            List of parsed conversations
        """
        if path.suffix == ".jsonl":
            return self._parse_jsonl(path)
        elif path.suffix == ".json":
            return self._parse_json(path)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")
    
    def _parse_jsonl(self, path: Path) -> list[ChatConversation]:
        """Parse JSONL streaming log format."""
        messages = []
        current_model = None
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                # Handle streaming response entries
                if "model" in entry:
                    current_model = entry["model"]
                
                if "prompt" in entry:
                    messages.append(ChatMessage(
                        role="user",
                        content=entry["prompt"],
                        timestamp=self._parse_timestamp(entry.get("created_at")),
                        model=current_model,
                    ))
                
                if "response" in entry:
                    messages.append(ChatMessage(
                        role="assistant",
                        content=entry["response"],
                        timestamp=self._parse_timestamp(entry.get("created_at")),
                        model=current_model,
                    ))
        
        if not messages:
            return []
        
        # Create a single conversation from all messages
        return [ChatConversation(
            id=path.stem,
            provider=ProviderType.OLLAMA,
            title=f"Ollama session - {path.stem}",
            messages=messages,
            created_at=messages[0].timestamp or datetime.now(),
            updated_at=messages[-1].timestamp or datetime.now(),
            metadata={"source_file": str(path), "model": current_model},
        )]
    
    def _parse_json(self, path: Path) -> list[ChatConversation]:
        """Parse JSON chat export (Open WebUI style)."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return self._normalize_conversations(data, path.stem)
    
    def _normalize_conversations(
        self, data: dict[str, Any] | list[dict[str, Any]], source: str
    ) -> list[ChatConversation]:
        """Convert Ollama/Open WebUI format to normalized ChatConversation."""
        # Handle Open WebUI export format
        if isinstance(data, dict):
            if "chat" in data:
                return [self._parse_open_webui_chat(data["chat"], source)]
            if "messages" in data:
                return [self._parse_messages_format(data, source)]
            if "history" in data:
                return self._parse_history_format(data["history"], source)
        
        # Handle list of conversations
        if isinstance(data, list):
            # Check if it's a list of messages or list of conversations
            if data and "role" in data[0]:
                # List of messages - single conversation
                return [ChatConversation(
                    id=source,
                    provider=ProviderType.OLLAMA,
                    title=f"Ollama chat - {source}",
                    messages=self._parse_message_list(data),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )]
            else:
                # List of conversations
                return [
                    self._parse_messages_format(c, f"{source}_{i}")
                    for i, c in enumerate(data)
                ]
        
        return []
    
    def _parse_open_webui_chat(
        self, chat_data: dict[str, Any], source: str
    ) -> ChatConversation:
        """Parse Open WebUI chat export format."""
        messages = []
        history = chat_data.get("history", {})
        messages_data = history.get("messages", {})
        
        # Open WebUI stores messages as a dict with ids as keys
        for msg_id, msg in messages_data.items():
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if content.strip():
                messages.append(ChatMessage(
                    role=role,
                    content=content,
                    model=msg.get("model") or chat_data.get("models", [None])[0],
                    timestamp=self._parse_timestamp(msg.get("timestamp")),
                ))
        
        # Sort by timestamp if available
        messages.sort(key=lambda m: m.timestamp or datetime.min)
        
        return ChatConversation(
            id=chat_data.get("id", source),
            provider=ProviderType.OLLAMA,
            title=chat_data.get("title") or f"Ollama chat - {source}",
            messages=messages,
            created_at=self._parse_timestamp(chat_data.get("created_at")) or datetime.now(),
            updated_at=self._parse_timestamp(chat_data.get("updated_at")) or datetime.now(),
            metadata={
                "models": chat_data.get("models", []),
                "tags": chat_data.get("tags", []),
            },
        )
    
    def _parse_messages_format(
        self, data: dict[str, Any], source: str
    ) -> ChatConversation:
        """Parse simple messages array format."""
        messages = self._parse_message_list(data.get("messages", []))
        
        return ChatConversation(
            id=data.get("id", source),
            provider=ProviderType.OLLAMA,
            title=data.get("title") or f"Ollama chat - {source}",
            messages=messages,
            created_at=self._parse_timestamp(data.get("created_at")) or datetime.now(),
            updated_at=self._parse_timestamp(data.get("updated_at")) or datetime.now(),
            metadata={"model": data.get("model")},
        )
    
    def _parse_history_format(
        self, history: list[dict[str, Any]], source: str
    ) -> list[ChatConversation]:
        """Parse history list format."""
        conversations = []
        
        for idx, conv in enumerate(history):
            messages = self._parse_message_list(conv.get("messages", []))
            if messages:
                conversations.append(ChatConversation(
                    id=conv.get("id", f"{source}_{idx}"),
                    provider=ProviderType.OLLAMA,
                    title=conv.get("title"),
                    messages=messages,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                ))
        
        return conversations
    
    def _parse_message_list(self, msg_list: list[dict[str, Any]]) -> list[ChatMessage]:
        """Parse a list of message objects."""
        messages = []
        
        for msg in msg_list:
            role = msg.get("role", "user")
            if role not in ["user", "assistant", "system"]:
                continue
            
            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle content blocks
                content = " ".join(
                    c.get("text", str(c)) if isinstance(c, dict) else str(c)
                    for c in content
                )
            
            if content.strip():
                messages.append(ChatMessage(
                    role=role,
                    content=content,
                    model=msg.get("model"),
                    timestamp=self._parse_timestamp(msg.get("timestamp")),
                ))
        
        return messages
    
    def _parse_timestamp(self, ts: str | int | float | None) -> datetime | None:
        """Parse timestamp from various formats."""
        if ts is None:
            return None
        if isinstance(ts, (int, float)):
            # Handle milliseconds vs seconds
            if ts > 1e12:
                ts = ts / 1000
            return datetime.fromtimestamp(ts)
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
