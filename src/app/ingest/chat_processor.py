"""Chat/Message History Processor - Parse conversation exports.

Handles chat exports from various messaging platforms like WhatsApp,
Telegram, Discord, iMessage, and generic text-based chat logs.
"""

from pathlib import Path
from typing import Optional, Iterator
from dataclasses import dataclass, field
from datetime import datetime
import re
import json
import hashlib


@dataclass
class ChatMessage:
    """A single chat message."""
    
    sender: str
    content: str
    timestamp: Optional[datetime] = None
    is_me: bool = False
    message_type: str = "text"  # text, image, video, audio, file
    reactions: list[str] = field(default_factory=list)
    reply_to: Optional[str] = None
    
    @property
    def id(self) -> str:
        """Generate unique ID for this message."""
        hash_input = f"{self.sender}:{self.content[:50]}:{self.timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def to_text(self) -> str:
        """Convert to text for embedding."""
        timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M") if self.timestamp else ""
        return f"[{timestamp}] {self.sender}: {self.content}"


@dataclass
class ChatThread:
    """A conversation thread."""
    
    name: str
    platform: str
    participants: list[str] = field(default_factory=list)
    messages: list[ChatMessage] = field(default_factory=list)
    is_group: bool = False
    
    @property
    def message_count(self) -> int:
        return len(self.messages)
    
    @property
    def my_messages(self) -> list[ChatMessage]:
        """Get only messages from the user (is_me=True)."""
        return [m for m in self.messages if m.is_me]
    
    def to_text(self, max_messages: int = 100) -> str:
        """Convert thread to text for embedding."""
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        lines = [f"Chat: {self.name} ({self.platform})"]
        lines.extend(m.to_text() for m in recent)
        return "\n".join(lines)


class ChatHistoryProcessor:
    """Process chat exports for personal AI training.
    
    Supports WhatsApp, Telegram, Discord, and generic text exports.
    
    Example:
        >>> processor = ChatHistoryProcessor(my_name="JROCK")
        >>> thread = processor.process_whatsapp("WhatsApp Chat with Alice.txt")
        >>> print(f"Found {len(thread.my_messages)} of my messages")
    """
    
    def __init__(
        self,
        my_name: str = "JROCK",
        my_aliases: Optional[list[str]] = None,
    ) -> None:
        """Initialize the chat processor.
        
        Args:
            my_name: Your name as it appears in chats.
            my_aliases: Alternative names/usernames to match.
        """
        self.my_name = my_name
        self.my_aliases = set(my_aliases or [])
        self.my_aliases.add(my_name)
        self.my_aliases.add(my_name.lower())
    
    def _is_me(self, sender: str) -> bool:
        """Check if a sender name matches the user."""
        sender_lower = sender.lower()
        return any(
            alias.lower() in sender_lower or sender_lower in alias.lower()
            for alias in self.my_aliases
        )
    
    def process_whatsapp(self, file_path: str | Path) -> ChatThread:
        """Process a WhatsApp chat export.
        
        Args:
            file_path: Path to the WhatsApp .txt export.
        
        Returns:
            ChatThread: Parsed chat thread.
        """
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        
        # Extract chat name from filename
        chat_name = path.stem.replace("WhatsApp Chat with ", "")
        
        thread = ChatThread(
            name=chat_name,
            platform="whatsapp",
        )
        
        # WhatsApp format: [DD/MM/YYYY, HH:MM:SS] Sender: Message
        # Or: MM/DD/YY, HH:MM - Sender: Message
        patterns = [
            r"\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*(?:AM|PM)?\]\s+([^:]+):\s+(.+?)(?=\n\[|$)",
            r"(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?:\s*(?:AM|PM))?)\s+-\s+([^:]+):\s+(.+?)(?=\n\d|$)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                for match in matches:
                    date_str, time_str, sender, message = match
                    sender = sender.strip()
                    
                    timestamp = self._parse_datetime(date_str, time_str)
                    
                    msg = ChatMessage(
                        sender=sender,
                        content=message.strip(),
                        timestamp=timestamp,
                        is_me=self._is_me(sender),
                    )
                    thread.messages.append(msg)
                    
                    if sender not in thread.participants:
                        thread.participants.append(sender)
                break
        
        thread.is_group = len(thread.participants) > 2
        return thread
    
    def process_telegram(self, export_path: str | Path) -> ChatThread:
        """Process a Telegram JSON export.
        
        Args:
            export_path: Path to the Telegram result.json file.
        
        Returns:
            ChatThread: Parsed chat thread.
        """
        path = Path(export_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        
        thread = ChatThread(
            name=data.get("name", "Telegram Chat"),
            platform="telegram",
        )
        
        messages = data.get("messages", [])
        for msg_data in messages:
            if msg_data.get("type") != "message":
                continue
            
            sender = msg_data.get("from", "Unknown")
            
            # Handle text that can be string or list
            text = msg_data.get("text", "")
            if isinstance(text, list):
                text = "".join(
                    part if isinstance(part, str) else part.get("text", "")
                    for part in text
                )
            
            if not text:
                continue
            
            timestamp = None
            date_str = msg_data.get("date")
            if date_str:
                try:
                    timestamp = datetime.fromisoformat(date_str)
                except ValueError:
                    pass
            
            msg = ChatMessage(
                sender=sender,
                content=text,
                timestamp=timestamp,
                is_me=self._is_me(sender),
            )
            thread.messages.append(msg)
            
            if sender not in thread.participants:
                thread.participants.append(sender)
        
        return thread
    
    def process_discord(self, export_path: str | Path) -> ChatThread:
        """Process a Discord channel export (JSON format).
        
        Args:
            export_path: Path to Discord export JSON.
        
        Returns:
            ChatThread: Parsed chat thread.
        """
        path = Path(export_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        
        channel_name = data.get("channel", {}).get("name", "Discord Chat")
        
        thread = ChatThread(
            name=channel_name,
            platform="discord",
        )
        
        for msg_data in data.get("messages", []):
            author = msg_data.get("author", {})
            sender = author.get("name") or author.get("nickname", "Unknown")
            content = msg_data.get("content", "")
            
            if not content:
                continue
            
            timestamp = None
            ts_str = msg_data.get("timestamp")
            if ts_str:
                try:
                    timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except ValueError:
                    pass
            
            msg = ChatMessage(
                sender=sender,
                content=content,
                timestamp=timestamp,
                is_me=self._is_me(sender),
            )
            thread.messages.append(msg)
            
            if sender not in thread.participants:
                thread.participants.append(sender)
        
        return thread
    
    def process_generic_text(
        self,
        file_path: str | Path,
        platform: str = "chat"
    ) -> ChatThread:
        """Process a generic text chat log.
        
        Attempts to parse common chat log formats.
        
        Args:
            file_path: Path to the text file.
            platform: Platform name to use.
        
        Returns:
            ChatThread: Parsed chat thread.
        """
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        
        thread = ChatThread(
            name=path.stem,
            platform=platform,
        )
        
        # Try common patterns
        # Pattern: [timestamp] sender: message
        # Pattern: sender: message
        # Pattern: <sender> message
        
        patterns = [
            r"\[([^\]]+)\]\s+([^:]+):\s+(.+)",
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+([^:]+):\s+(.+)",
            r"^([^:]+):\s+(.+)$",
            r"^<([^>]+)>\s+(.+)$",
        ]
        
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    groups = match.groups()
                    
                    if len(groups) == 3:
                        timestamp_str, sender, message = groups
                        timestamp = self._parse_datetime(timestamp_str)
                    elif len(groups) == 2:
                        sender, message = groups
                        timestamp = None
                    else:
                        continue
                    
                    msg = ChatMessage(
                        sender=sender.strip(),
                        content=message.strip(),
                        timestamp=timestamp,
                        is_me=self._is_me(sender.strip()),
                    )
                    thread.messages.append(msg)
                    
                    if sender.strip() not in thread.participants:
                        thread.participants.append(sender.strip())
                    break
        
        return thread
    
    def _parse_datetime(
        self,
        date_str: str,
        time_str: Optional[str] = None
    ) -> Optional[datetime]:
        """Parse various datetime formats.
        
        Args:
            date_str: Date string or combined datetime.
            time_str: Optional separate time string.
        
        Returns:
            datetime or None if parsing fails.
        """
        combined = f"{date_str} {time_str}" if time_str else date_str
        combined = combined.strip()
        
        formats = [
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%m/%d/%y, %I:%M %p",
            "%d/%m/%y, %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(combined, fmt)
            except ValueError:
                continue
        
        return None


def process_chat_export(
    file_path: str,
    platform: str = "auto",
    my_name: str = "JROCK"
) -> ChatThread:
    """Process a chat export file.
    
    Args:
        file_path: Path to the export.
        platform: Platform type or "auto" to detect.
        my_name: Your name for identifying your messages.
    
    Returns:
        ChatThread: Parsed chat thread.
    """
    processor = ChatHistoryProcessor(my_name=my_name)
    path = Path(file_path)
    
    if platform == "auto":
        if "whatsapp" in path.name.lower():
            platform = "whatsapp"
        elif path.suffix == ".json":
            content = path.read_text(encoding="utf-8")
            if "telegram" in content.lower():
                platform = "telegram"
            elif "discord" in content.lower():
                platform = "discord"
            else:
                platform = "generic"
        else:
            platform = "generic"
    
    if platform == "whatsapp":
        return processor.process_whatsapp(file_path)
    elif platform == "telegram":
        return processor.process_telegram(file_path)
    elif platform == "discord":
        return processor.process_discord(file_path)
    else:
        return processor.process_generic_text(file_path)
