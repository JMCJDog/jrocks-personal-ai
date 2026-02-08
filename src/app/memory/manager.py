"""Memory Manager for JRock's Personal AI.

Handles persistent storage of chat sessions, messages, and episodic memories
using SQLite.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("data/jrock_chat_memory.db")

class MemoryManager:
    """Manages persistent chat memory."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize the database with schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read schema
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            logger.error(f"Schema file not found at {schema_path}")
            return
            
        with sqlite3.connect(self.db_path) as conn:
            with open(schema_path, "r") as f:
                conn.executescript(f.read())
            
            # Migration: Ensure processed column exists
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN processed INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass # Column exists

    def create_session(self, session_id: str, metadata: Optional[Dict] = None):
        """Create a new session."""
        created_at = datetime.now().isoformat()
        meta_json = json.dumps(metadata or {})
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id, created_at, metadata, processed) VALUES (?, ?, ?, 0)",
                (session_id, created_at, meta_json)
            )

    def get_unprocessed_sessions(self, limit: int = 10) -> List[Dict]:
        """Get sessions that haven't been optimized into memories."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM sessions WHERE processed = 0 ORDER BY created_at ASC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_session_processed(self, session_id: str):
        """Mark a session as formatted."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE sessions SET processed = 1 WHERE session_id = ?", (session_id,))

    def add_episodic_memory(self, content: str, embedding_id: Optional[str] = None, source_session_id: Optional[str] = None):
        """Add a synthesized memory."""
        created_at = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO episodic_memories (content, created_at, embedding_id, source_session_id) VALUES (?, ?, ?, ?)",
                (content, created_at, embedding_id, source_session_id)
            )

    def get_memories(self, limit: int = 20) -> List[str]:
        """Get recent memories."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT content FROM episodic_memories ORDER BY id DESC LIMIT ?", (limit,))
            return [row[0] for row in cursor.fetchall()]

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to a session."""
        timestamp = datetime.now().isoformat()
        meta_json = json.dumps(metadata or {})
        
        with sqlite3.connect(self.db_path) as conn:
            # Ensure session exists (just in case)
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id, created_at, metadata, processed) VALUES (?, ?, ?, 0)",
                (session_id, timestamp, "{}")
            )
            
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, timestamp, meta_json)
            )

    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get history for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT role, content, timestamp, metadata FROM messages WHERE session_id = ? ORDER BY id ASC", 
                (session_id,)
            ) 
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent sessions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

