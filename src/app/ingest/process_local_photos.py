import argparse
import sys
import logging
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- Inlined VisionProcessor Core ---

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
    """Process images for facial recognition (Standalone Version)."""
    
    def __init__(self, known_faces_dir: Optional[Path] = None) -> None:
        self.known_faces_dir = known_faces_dir or Path("data/faces")
        self._known_encodings = []
        self._known_names = []
        
    def load_known_faces(self) -> None:
        """Load known face encodings from reference directory."""
        if not self.known_faces_dir.exists():
            print(f"Warning: Reference directory {self.known_faces_dir} does not exist.")
            return
            
        try:
            import face_recognition
            # Suppress intermediate warnings if needed
            
            count = 0
            for file_path in self.known_faces_dir.glob("*"):
                if file_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                    try:
                        image = face_recognition.load_image_file(str(file_path))
                        encodings = face_recognition.face_encodings(image)
                        
                        if encodings:
                            self._known_encodings.append(encodings[0])
                            self._known_names.append(file_path.stem)
                            count += 1
                    except Exception as e:
                        print(f"Skipping {file_path.name}: {e}")
                        
            print(f"Loaded {count} known faces from {self.known_faces_dir}")
            
        except ImportError:
            print("Error: face_recognition library not installed.")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading faces: {e}")

    def process_image(self, file_path: str | Path) -> ProcessedImage:
        """Process an image for faces."""
        path = Path(file_path)
        result = ProcessedImage(file_path=str(path))
        
        try:
            import face_recognition
            import numpy as np # Implicit dependency of face_recognition output
            
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
            
        except Exception as e:
            # print(f"Error processing {path.name}: {e}")
            pass
            
        return result

# --- Main Script Logic ---

def process_local_photos(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    target_person: str = "jrock",
    copy_matches: bool = False
):
    """Scan local photos for matches."""
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist.")
        return

    print(f"\n--- Starting Local Photo Processing ---")
    print(f"Scanning: {input_path}")
    print(f"Target: {target_person}")
    
    processor = VisionProcessor()
    processor.load_known_faces()
    
    if not processor._known_names:
        print("Warning: No known faces found. Please add reference photos to data/faces/")
        # Continue anyway to show scanning works

    # Recursively find images
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.heic'}
    # Use rglob for recursive, but maybe limit distinct files if massive? 
    # glob is generator, good.
    
    print(f"\nScanning for images...")
    
    image_files = []
    try:
        for p in input_path.rglob('*'):
            if p.suffix.lower() in image_extensions:
                image_files.append(p)
    except Exception as e:
        print(f"Error scanning directory: {e}")
        return
        
    print(f"Found {len(image_files)} images to process.\n")
    
    matches_found = []
    
    for i, photo_path in enumerate(image_files, 1):
        try:
            print(f"[{i}/{len(image_files)}] Processing {photo_path.name}...", end='', flush=True)
            
            result = processor.process_image(photo_path)
            
            found_match = False
            for face in result.faces:
                if face.name and target_person.lower() in face.name.lower():
                    found_match = True
                    matches_found.append(photo_path)
                    print(f" MATCH! ({face.confidence:.1%})")
                    
                    # Copy if requested
                    if copy_matches:
                        # Default output if not specified
                        dest_base = output_dir or Path("data/found_photos") 
                        dest_dir = Path(dest_base)
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        try:
                            shutil.copy2(photo_path, dest_dir / photo_path.name)
                        except Exception as copy_err:
                            print(f" (Copy failed: {copy_err})", end='')
                        
            if not found_match:
                if result.faces:
                    print(f" detected {len(result.faces)} faces, no match.")
                else:
                    print(" no faces.")
                
        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f" Error: {e}")

    print(f"\n--- Processing Complete ---")
    print(f"Total Matches Found: {len(matches_found)}")
    for match in matches_found:
        print(f"- {match}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan local photos for specific people.")
    parser.add_argument("input_dir", help="Directory containing photos to scan")
    parser.add_argument("--target", default="jrock", help="Person to search for")
    parser.add_argument("--output", help="Directory to copy matches to")
    parser.add_argument("--copy", action="store_true", help="Copy matching photos to output directory")
    
    args = parser.parse_args()
    
    process_local_photos(
        args.input_dir,
        args.output,
        args.target,
        args.copy
    )
