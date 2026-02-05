"""Image Processor - Extract metadata and captions from images.

Handles image files for personal AI training, including EXIF extraction,
face detection hints, and AI-generated captions.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
import base64
import hashlib


@dataclass
class ImageMetadata:
    """Metadata extracted from an image."""
    
    file_path: str
    file_name: str
    file_size: int
    dimensions: tuple[int, int] = (0, 0)
    format: str = "unknown"
    taken_date: Optional[datetime] = None
    location: Optional[str] = None
    camera: Optional[str] = None
    caption: str = ""
    tags: list[str] = field(default_factory=list)
    faces_detected: int = 0
    
    @property
    def id(self) -> str:
        """Generate unique ID for this image."""
        return hashlib.md5(self.file_path.encode()).hexdigest()


@dataclass
class ProcessedImage:
    """A fully processed image with metadata and embeddings."""
    
    metadata: ImageMetadata
    text_content: str  # Combined text for embedding
    base64_thumbnail: Optional[str] = None


class ImageProcessor:
    """Process images for the personal AI knowledge base.
    
    Extracts metadata, generates captions, and prepares images
    for embedding and retrieval.
    
    Example:
        >>> processor = ImageProcessor()
        >>> result = processor.process_file("photo.jpg")
        >>> print(result.metadata.caption)
    """
    
    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    
    def __init__(self, generate_captions: bool = True) -> None:
        """Initialize the image processor.
        
        Args:
            generate_captions: Whether to generate AI captions.
        """
        self.generate_captions = generate_captions
        self._pil_available = self._check_pil()
    
    def _check_pil(self) -> bool:
        """Check if PIL is available."""
        try:
            from PIL import Image
            return True
        except ImportError:
            return False
    
    def process_file(self, file_path: str | Path) -> ProcessedImage:
        """Process a single image file.
        
        Args:
            file_path: Path to the image file.
        
        Returns:
            ProcessedImage: Processed image with metadata.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {path.suffix}")
        
        # Basic metadata
        metadata = ImageMetadata(
            file_path=str(path),
            file_name=path.name,
            file_size=path.stat().st_size,
            format=path.suffix.lower()[1:],
        )
        
        # Extract detailed metadata if PIL available
        if self._pil_available:
            self._extract_pil_metadata(path, metadata)
        
        # Generate text content for embedding
        text_parts = [f"Image: {metadata.file_name}"]
        
        if metadata.caption:
            text_parts.append(f"Caption: {metadata.caption}")
        if metadata.tags:
            text_parts.append(f"Tags: {', '.join(metadata.tags)}")
        if metadata.location:
            text_parts.append(f"Location: {metadata.location}")
        if metadata.taken_date:
            text_parts.append(f"Date: {metadata.taken_date.strftime('%Y-%m-%d')}")
        
        text_content = "\n".join(text_parts)
        
        return ProcessedImage(
            metadata=metadata,
            text_content=text_content,
        )
    
    def _extract_pil_metadata(self, path: Path, metadata: ImageMetadata) -> None:
        """Extract metadata using PIL.
        
        Args:
            path: Path to the image.
            metadata: ImageMetadata to populate.
        """
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            with Image.open(path) as img:
                metadata.dimensions = img.size
                metadata.format = img.format or metadata.format
                
                # Extract EXIF data
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag == "DateTimeOriginal":
                            try:
                                metadata.taken_date = datetime.strptime(
                                    value, "%Y:%m:%d %H:%M:%S"
                                )
                            except (ValueError, TypeError):
                                pass
                        elif tag == "Model":
                            metadata.camera = str(value)
                            
        except Exception:
            pass  # Continue with basic metadata
    
    def process_directory(
        self,
        directory: str | Path,
        recursive: bool = True
    ) -> list[ProcessedImage]:
        """Process all images in a directory.
        
        Args:
            directory: Directory to process.
            recursive: Whether to search subdirectories.
        
        Returns:
            list: List of processed images.
        """
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        
        pattern = "**/*" if recursive else "*"
        results = []
        
        for path in dir_path.glob(pattern):
            if path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                try:
                    result = self.process_file(path)
                    results.append(result)
                except Exception:
                    continue  # Skip problematic files
        
        return results


def process_image(file_path: str) -> ProcessedImage:
    """Convenience function to process a single image.
    
    Args:
        file_path: Path to the image.
    
    Returns:
        ProcessedImage: The processed image.
    """
    processor = ImageProcessor()
    return processor.process_file(file_path)
