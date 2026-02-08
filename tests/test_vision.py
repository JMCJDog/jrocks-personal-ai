"""Tests for vision module and facial recognition."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.app.ingest.vision import VisionProcessor, DetectedFace, ProcessedImage


class TestVisionProcessor:
    """Test suite for VisionProcessor."""
    
    def test_init_default_faces_dir(self):
        """Test default faces directory initialization."""
        processor = VisionProcessor()
        assert processor.known_faces_dir == Path("data/faces")
    
    def test_init_custom_faces_dir(self):
        """Test custom faces directory initialization."""
        custom_dir = Path("/custom/faces")
        processor = VisionProcessor(known_faces_dir=custom_dir)
        assert processor.known_faces_dir == custom_dir
    
    def test_load_known_faces_empty_dir(self, tmp_path):
        """Test loading faces from empty directory."""
        processor = VisionProcessor(known_faces_dir=tmp_path)
        processor.load_known_faces()
        assert len(processor._known_names) == 0
        assert len(processor._known_encodings) == 0
    
    def test_load_known_faces_nonexistent_dir(self, tmp_path):
        """Test loading faces from nonexistent directory."""
        processor = VisionProcessor(known_faces_dir=tmp_path / "nonexistent")
        processor.load_known_faces()  # Should not raise
        assert len(processor._known_names) == 0
    
    @patch('src.app.ingest.vision.face_recognition')
    def test_process_image_with_faces(self, mock_fr, tmp_path):
        """Test processing image with detected faces."""
        # Create a test image file
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"fake image data")
        
        # Mock face_recognition
        mock_fr.load_image_file.return_value = MagicMock()
        mock_fr.face_locations.return_value = [(100, 200, 300, 50)]
        mock_fr.face_encodings.return_value = [
            MagicMock(tolist=lambda: [0.1] * 128)
        ]
        
        processor = VisionProcessor(known_faces_dir=tmp_path)
        result = processor.process_image(test_image)
        
        assert isinstance(result, ProcessedImage)
        assert len(result.faces) == 1
        assert result.faces[0].name == "Unknown"
    
    @patch('src.app.ingest.vision.face_recognition')
    def test_process_image_matches_known_face(self, mock_fr, tmp_path):
        """Test that known faces are correctly identified."""
        import numpy as np
        
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b"fake image data")
        
        mock_encoding = MagicMock()
        mock_encoding.tolist.return_value = [0.1] * 128
        
        mock_fr.load_image_file.return_value = MagicMock()
        mock_fr.face_locations.return_value = [(100, 200, 300, 50)]
        mock_fr.face_encodings.return_value = [mock_encoding]
        mock_fr.compare_faces.return_value = [True]
        # Return numpy array with argmin method
        mock_fr.face_distance.return_value = np.array([0.3])
        
        processor = VisionProcessor(known_faces_dir=tmp_path)
        processor._known_encodings = [[0.1] * 128]
        processor._known_names = ["jrock_reference"]
        
        result = processor.process_image(test_image)
        
        assert len(result.faces) == 1
        assert result.faces[0].name == "jrock_reference"
        assert result.faces[0].confidence > 0


class TestProcessedImage:
    """Test suite for ProcessedImage dataclass."""
    
    def test_processed_image_creation(self):
        """Test ProcessedImage can be created with defaults."""
        image = ProcessedImage(file_path="/path/to/image.jpg")
        assert image.file_path == "/path/to/image.jpg"
        assert len(image.faces) == 0
        assert image.description == ""


class TestDetectedFace:
    """Test suite for DetectedFace dataclass."""
    
    def test_detected_face_creation(self):
        """Test DetectedFace can be created."""
        face = DetectedFace(
            bounding_box=(100, 200, 300, 50),
            name="jrock",
            confidence=0.85
        )
        assert face.name == "jrock"
        assert face.confidence == 0.85
        assert face.bounding_box == (100, 200, 300, 50)
