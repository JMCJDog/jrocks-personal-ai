"""Vision Processor - Facial recognition and image analysis.

Handles ingestion of the "Pictures" node, providing facial recognition
and scene analysis to identify people and contexts in photos.
"""

import logging
from pathlib import Path
from typing import Optional, Any

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    """A face detected in an image."""
    
    bounding_box: tuple[int, int, int, int]  # top, right, bottom, left
    encoding: list[float] = field(default_factory=list)
    name: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ProcessedImage:
    """A processed image with analysis results."""
    
    file_path: str
    faces: list[DetectedFace] = field(default_factory=list)
    description: str = ""
    metadata: dict = field(default_factory=dict)


class VisionProcessor:
    """Process images for facial recognition and scene analysis.
    
    Uses face_recognition library for identifying known individuals
    to build the social graph.
    """
    
    def __init__(self, known_faces_dir: Optional[Path] = None) -> None:
        """Initialize the vision processor.
        
        Args:
            known_faces_dir: Directory containing labeled reference photos.
        """
        self.known_faces_dir = known_faces_dir or Path("data/faces")
        self._known_encodings = []
        self._known_names = []
        
    def load_known_faces(self) -> None:
        """Load known face encodings from reference directory."""
        if not self.known_faces_dir.exists():
            return
            
        try:
            import face_recognition
            
            for file_path in self.known_faces_dir.glob("*"):
                if file_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                    image = face_recognition.load_image_file(str(file_path))
                    encodings = face_recognition.face_encodings(image)
                    
                    if encodings:
                        self._known_encodings.append(encodings[0])
                        self._known_names.append(file_path.stem)
                        
            logger.info(f"Loaded {len(self._known_names)} known faces")
            
        except ImportError:
            logger.warning("face_recognition library not installed")
        except Exception as e:
            logger.error(f"Error loading faces: {e}")

    def process_image(self, file_path: str | Path) -> ProcessedImage:
        """Process an image for faces and content.
        
        Args:
            file_path: Path to the image file.
            
        Returns:
            ProcessedImage: Analysis results.
        """
        path = Path(file_path)
        result = ProcessedImage(file_path=str(path))
        
        try:
            import face_recognition
            
            # Load image
            image = face_recognition.load_image_file(str(path))
            
            # Find faces
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
                name = "Unknown"
                confidence = 0.0
                
                # Match against known faces
                if self._known_encodings:
                    matches = face_recognition.compare_faces(self._known_encodings, encoding)
                    face_distances = face_recognition.face_distance(self._known_encodings, encoding)
                    
                    if True in matches:
                        best_match_index = face_distances.argmin()
                        if matches[best_match_index]:
                            name = self._known_names[best_match_index]
                            confidence = 1.0 - face_distances[best_match_index]
                
                result.faces.append(DetectedFace(
                    bounding_box=(top, right, bottom, left),
                    encoding=encoding.tolist(),
                    name=name,
                    confidence=confidence
                ))
            
            logger.info(f"Detected {len(result.faces)} faces in {path.name}")
            
        except ImportError:
            logger.warning("face_recognition not installed, skipping analysis")
            result.description = "Analysis skipped: face_recognition library missing"
        except Exception as e:
            logger.error(f"Error processing image {path}: {e}")
            result.metadata["error"] = str(e)
            
        return result
