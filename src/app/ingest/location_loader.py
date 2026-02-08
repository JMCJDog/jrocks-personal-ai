"""Location Loader - Ingest Google Location History (Records.json).

Parses the massive JSON file and stores it in a simplified SQLite database
optimized for heatmap rendering.
"""

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "data/locations.db"

class LocationLoader:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the locations database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    timestamp INTEGER PRIMARY KEY,
                    lat REAL NOT NULL,
                    lng REAL NOT NULL,
                    accuracy INTEGER
                )
            """)
            # Index for fast bounding-box queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lat ON locations(lat)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lng ON locations(lng)")
            conn.commit()

    def parse_timestamp(self, ts_val: Any) -> int:
        """Parse timestamp from typical Google formats."""
        if isinstance(ts_val, int):
            # Assume sorting milliseconds if year > 3000? No, usually ms.
            # Google uses timestampMs
            if ts_val > 1e11: # If > 1973 in seconds, likely ms
                return ts_val // 1000
            return ts_val
        elif isinstance(ts_val, str):
            try:
                # Try ISO format
                dt = datetime.fromisoformat(ts_val.replace('Z', '+00:00'))
                return int(dt.timestamp())
            except ValueError:
                # Try numeric string
                try:
                    return int(ts_val) // 1000
                except ValueError:
                    return 0
        return 0

    def ingest_file(self, file_path: str) -> int:
        """Ingest a Records.json file."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {path}")
            return 0

        logger.info(f"Loading {path} (this may take a while)...")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            logger.error("Invalid JSON file.")
            return 0
        except MemoryError:
            logger.error("File too large for memory. Please implement streaming.")
            return 0

        logger.info("Parsing locations...")
        
        # Handle 'locations' key (Records.json)
        raw_locations = data.get('locations', [])
        
        batch = []
        count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            for loc in raw_locations:
                if 'latitudeE7' not in loc or 'longitudeE7' not in loc:
                    continue

                lat = loc['latitudeE7'] / 1e7
                lng = loc['longitudeE7'] / 1e7
                acc = loc.get('accuracy', 0)
                ts = self.parse_timestamp(loc.get('timestampMs', loc.get('timestamp')))
                
                if ts == 0:
                    continue

                batch.append((ts, lat, lng, acc))
                
                if len(batch) >= 10000:
                    conn.executemany(
                        "INSERT OR IGNORE INTO locations (timestamp, lat, lng, accuracy) VALUES (?, ?, ?, ?)",
                        batch
                    )
                    count += len(batch)
                    batch = []
                    logger.info(f"Ingested {count} points...")
            
            if batch:
                conn.executemany(
                    "INSERT OR IGNORE INTO locations (timestamp, lat, lng, accuracy) VALUES (?, ?, ?, ?)",
                    batch
                )
                count += len(batch)

        logger.info(f"Ingestion complete. Total points: {count}")
        return count

if __name__ == "__main__":
    import sys
    loader = LocationLoader()
    
    # Check if a file was provided
    target_file = "data/Records.json"
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        
    loader.ingest_file(target_file)
