import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DriveMetadataDB:
    """Manages the SQLite database for Google Drive metadata."""
    
    def __init__(self, db_path: str = "data/drive_index.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def _init_db(self):
        """Initialize the database schema."""
        with self._get_conn() as conn:
            # Main table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS drive_files (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT,
                    mime_type TEXT,
                    modified_time TEXT,
                    parent_id TEXT,
                    starred INTEGER DEFAULT 0,
                    description TEXT,
                    last_indexed TEXT
                )
            """)
            
            # Indexes for common lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_parent_id ON drive_files(parent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON drive_files(name)")
            
            # Full Text Search (FTS5) for powerful keyword search
            # Check if FTS5 is supported
            try:
                conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS drive_files_fts USING fts5(name, path, description, id UNINDEXED)")
            except sqlite3.OperationalError:
                logger.warning("FTS5 not supported. Search will be slower.")

    def upsert_file(self, file_data: Dict[str, Any]):
        """Insert or update a file record."""
        with self._get_conn() as conn:
            now = datetime.now().isoformat()
            
            # 1. Update main table
            conn.execute("""
                INSERT OR REPLACE INTO drive_files 
                (id, name, path, mime_type, modified_time, parent_id, starred, description, last_indexed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_data['id'],
                file_data['name'],
                file_data.get('path', ''),
                file_data.get('mimeType', ''),
                file_data.get('modifiedTime', ''),
                file_data.get('parents', [None])[0] if file_data.get('parents') else None,
                1 if file_data.get('starred') else 0,
                file_data.get('description', ''),
                now
            ))
            
            # 2. Update FTS index
            try:
                # Remove existing FTS entry if any (to avoid duplicates, though FTS doesn't enforce PK effectively the same way)
                conn.execute("DELETE FROM drive_files_fts WHERE id = ?", (file_data['id'],))
                conn.execute("""
                    INSERT INTO drive_files_fts (name, path, description, id)
                    VALUES (?, ?, ?, ?)
                """, (
                    file_data['name'],
                    file_data.get('path', ''),
                    file_data.get('description', ''),
                    file_data['id']
                ))
            except sqlite3.OperationalError:
                pass # FTS missing

    def search_files(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search files by keyword (name, path, description)."""
        results = []
        with self._get_conn() as conn:
            try:
                # Try FTS search first
                cursor = conn.execute("""
                    SELECT f.* FROM drive_files f
                    JOIN drive_files_fts s ON f.id = s.id
                    WHERE drive_files_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, limit))
                results = [dict(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                # Fallback to LIKE
                like_query = f"%{query}%"
                cursor = conn.execute("""
                    SELECT * FROM drive_files 
                    WHERE name LIKE ? OR description LIKE ? OR path LIKE ?
                    LIMIT ?
                """, (like_query, like_query, like_query, limit))
                results = [dict(row) for row in cursor.fetchall()]
                
        return results

    def get_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM drive_files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_stats(self) -> Dict[str, int]:
        with self._get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM drive_files").fetchone()[0]
            return {"total_files": count}
