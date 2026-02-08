"""Photo Service - High-level service for photo search and recognition.

Combines Google Photos provider with VisionProcessor for finding photos
containing specific people and adding photo context to AI memory.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .providers.google_photos_provider import GooglePhotosProvider
from .vision import VisionProcessor, ProcessedImage

logger = logging.getLogger(__name__)


@dataclass
class PhotoMatch:
    """A photo that matches a person search."""
    
    media_id: str
    filename: str
    local_path: Optional[Path]
    match_confidence: float
    matched_person: str
    photo_date: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class PhotoSearchResult:
    """Results from a photo search operation."""
    
    query: str
    person_name: str
    total_searched: int
    matches: list[PhotoMatch] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    @property
    def match_count(self) -> int:
        return len(self.matches)


class PhotoService:
    """High-level service for photo search and facial recognition.
    
    Combines Google Photos access with local facial recognition to:
    - Find photos containing specific people
    - Search by date ranges
    - Add photo context to AI memory
    
    Example:
        >>> service = PhotoService()
        >>> results = service.find_photos_of("JRock", days_back=30)
        >>> print(f"Found {results.match_count} photos of JRock")
    """
    
    def __init__(
        self,
        photos_provider: Optional[GooglePhotosProvider] = None,
        vision_processor: Optional[VisionProcessor] = None,
        known_faces_dir: Optional[Path] = None
    ) -> None:
        """Initialize the photo service.
        
        Args:
            photos_provider: Google Photos provider instance.
            vision_processor: Vision processor for facial recognition.
            known_faces_dir: Directory with reference face images.
        """
        self.photos_provider = photos_provider or GooglePhotosProvider()
        
        # Use custom faces directory or default
        faces_dir = known_faces_dir or Path("data/faces")
        self.vision_processor = vision_processor or VisionProcessor(faces_dir)
        
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize providers and load known faces."""
        if self._initialized:
            return
        
        logger.info("Initializing PhotoService...")
        
        # Authenticate with Google Photos
        self.photos_provider.authenticate()
        
        # Load known face encodings
        self.vision_processor.load_known_faces()
        
        self._initialized = True
        logger.info(f"PhotoService ready. Known faces: {self.vision_processor._known_names}")
    
    def find_photos_of(
        self,
        person_name: str,
        days_back: int = 30,
        max_photos: int = 100,
        confidence_threshold: float = 0.6
    ) -> PhotoSearchResult:
        """Find photos containing a specific person.
        
        Args:
            person_name: Name to search for (must match a known face).
            days_back: How many days back to search.
            max_photos: Maximum photos to analyze.
            confidence_threshold: Minimum confidence for a match.
            
        Returns:
            PhotoSearchResult with matching photos.
        """
        self.initialize()
        
        result = PhotoSearchResult(
            query=f"photos of {person_name} from last {days_back} days",
            person_name=person_name,
            total_searched=0
        )
        
        # Check if person is known
        normalized_name = person_name.lower().replace(" ", "_")
        known_names_lower = [n.lower() for n in self.vision_processor._known_names]
        
        if normalized_name not in known_names_lower and person_name.lower() not in known_names_lower:
            result.errors.append(f"Unknown person: {person_name}. Known: {self.vision_processor._known_names}")
            return result
        
        try:
            # Get photos from date range
            photos = self.photos_provider.search_last_n_days(days_back, max_photos)
            result.total_searched = len(photos)
            
            logger.info(f"Analyzing {len(photos)} photos for {person_name}...")
            
            for photo in photos:
                try:
                    # Download photo
                    local_path = self.photos_provider.download_photo(photo)
                    if not local_path:
                        continue
                    
                    # Analyze for faces
                    processed = self.vision_processor.process_image(local_path)
                    
                    # Check for matches
                    for face in processed.faces:
                        face_name_lower = (face.name or "").lower()
                        if (face_name_lower == normalized_name or 
                            face_name_lower == person_name.lower() or
                            normalized_name in face_name_lower):
                            
                            if face.confidence >= confidence_threshold:
                                # Parse photo date
                                photo_date = None
                                if 'mediaMetadata' in photo:
                                    creation_time = photo['mediaMetadata'].get('creationTime')
                                    if creation_time:
                                        photo_date = datetime.fromisoformat(
                                            creation_time.replace('Z', '+00:00')
                                        )
                                
                                result.matches.append(PhotoMatch(
                                    media_id=photo['id'],
                                    filename=photo.get('filename', 'unknown'),
                                    local_path=local_path,
                                    match_confidence=face.confidence,
                                    matched_person=face.name or person_name,
                                    photo_date=photo_date,
                                    metadata={
                                        'base_url': photo.get('baseUrl'),
                                        'product_url': photo.get('productUrl'),
                                        'mime_type': photo.get('mimeType')
                                    }
                                ))
                                break  # Only count once per photo
                                
                except Exception as e:
                    logger.warning(f"Error processing photo {photo.get('id')}: {e}")
                    result.errors.append(str(e))
            
            logger.info(f"Found {result.match_count} photos of {person_name}")
            
        except Exception as e:
            logger.error(f"Photo search failed: {e}")
            result.errors.append(str(e))
        
        return result

    def find_photos_from_period(
        self,
        person_name: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        max_photos: int = 100,
        confidence_threshold: float = 0.6
    ) -> PhotoSearchResult:
        """Find photos of a person from a specific date range.
        
        Args:
            person_name: Name to search for.
            start_date: Start of search period.
            end_date: End of search period (defaults to now).
            max_photos: Maximum photos to analyze.
            confidence_threshold: Minimum confidence for match.
            
        Returns:
            PhotoSearchResult with matching photos.
        """
        self.initialize()
        
        end_date = end_date or datetime.now()
        days_back = (datetime.now() - start_date).days
        
        result = PhotoSearchResult(
            query=f"photos of {person_name} from {start_date.date()} to {end_date.date()}",
            person_name=person_name,
            total_searched=0
        )
        
        try:
            photos = self.photos_provider.search_by_date_range(
                start_date, end_date, max_photos
            )
            result.total_searched = len(photos)
            
            # Reuse the same analysis logic
            for photo in photos:
                try:
                    local_path = self.photos_provider.download_photo(photo)
                    if not local_path:
                        continue
                    
                    processed = self.vision_processor.process_image(local_path)
                    
                    for face in processed.faces:
                        if person_name.lower() in (face.name or "").lower():
                            if face.confidence >= confidence_threshold:
                                photo_date = None
                                if 'mediaMetadata' in photo:
                                    creation_time = photo['mediaMetadata'].get('creationTime')
                                    if creation_time:
                                        photo_date = datetime.fromisoformat(
                                            creation_time.replace('Z', '+00:00')
                                        )
                                
                                result.matches.append(PhotoMatch(
                                    media_id=photo['id'],
                                    filename=photo.get('filename', 'unknown'),
                                    local_path=local_path,
                                    match_confidence=face.confidence,
                                    matched_person=face.name or person_name,
                                    photo_date=photo_date
                                ))
                                break
                                
                except Exception as e:
                    result.errors.append(str(e))
                    
        except Exception as e:
            result.errors.append(str(e))
        
        return result

    def get_photo_context(self, result: PhotoSearchResult) -> str:
        """Generate natural language context from photo search results.
        
        Useful for adding to AI memory or conversation context.
        
        Args:
            result: A photo search result.
            
        Returns:
            Natural language description of the photos found.
        """
        if not result.matches:
            return f"No photos of {result.person_name} were found in the search."
        
        context_parts = [
            f"Found {result.match_count} photos of {result.person_name} "
            f"(searched {result.total_searched} total):"
        ]
        
        # Group by date
        dates = {}
        for match in result.matches:
            if match.photo_date:
                date_key = match.photo_date.strftime("%B %d, %Y")
                if date_key not in dates:
                    dates[date_key] = []
                dates[date_key].append(match)
        
        for date, matches in sorted(dates.items()):
            context_parts.append(f"- {date}: {len(matches)} photo(s)")
        
        # Add confidence info
        avg_confidence = sum(m.match_confidence for m in result.matches) / len(result.matches)
        context_parts.append(f"Average match confidence: {avg_confidence:.1%}")
        
        return "\n".join(context_parts)
