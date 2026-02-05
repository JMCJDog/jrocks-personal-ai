"""Location Processor - Process and analyze location history.

Handles ingestion of "Location data" (e.g., Google Search History/Location History,
GPX files) to build a map of visited places and movements.
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LocationPoint:
    """A single location data point."""
    
    latitude: float
    longitude: float
    timestamp: datetime
    accuracy: Optional[int] = None
    altitude: Optional[float] = None


@dataclass
class PlaceVisit:
    """A derived visit to a specific place."""
    
    name: Optional[str]
    address: Optional[str]
    start_time: datetime
    end_time: datetime
    coordinates: tuple[float, float]
    
    @property
    def duration(self) -> float:
        return (self.end_time - self.start_time).total_seconds()


class LocationProcessor:
    """Process location data from various sources."""
    
    def __init__(self) -> None:
        """Initialize the location processor."""
        pass
        
    def process_google_history(self, file_path: str | Path) -> list[LocationPoint]:
        """Process Google Location History (JSON).
        
        Args:
            file_path: Path to Location History.json
            
        Returns:
            List of LocationPoints
        """
        points = []
        path = Path(file_path)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            locations = data.get('locations', [])
            
            for loc in locations:
                # Google stores lat/lng as E7 integers
                lat = loc.get('latitudeE7', 0) / 1e7
                lng = loc.get('longitudeE7', 0) / 1e7
                timestamp_ms = int(loc.get('timestampMs', 0))
                accuracy = loc.get('accuracy')
                altitude = loc.get('altitude')
                
                points.append(LocationPoint(
                    latitude=lat,
                    longitude=lng,
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000.0),
                    accuracy=accuracy,
                    altitude=altitude
                ))
            
            logger.info(f"Processed {len(points)} location points from Google History")
            
        except Exception as e:
            logger.error(f"Error processing Google location history: {e}")
            
        return points
    
    def process_gpx(self, file_path: str | Path) -> list[LocationPoint]:
        """Process GPX file.
        
        Args:
            file_path: Path to .gpx file
            
        Returns:
            List of LocationPoints
        """
        # TODO: Implement gpxpy integration
        return []
