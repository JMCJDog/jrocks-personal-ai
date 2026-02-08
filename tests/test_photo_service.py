"""Tests for photo service integration."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.app.ingest.photo_service import (
    PhotoService, 
    PhotoMatch, 
    PhotoSearchResult
)


class TestPhotoSearchResult:
    """Test suite for PhotoSearchResult dataclass."""
    
    def test_empty_result(self):
        """Test empty search result."""
        result = PhotoSearchResult(
            query="test query",
            person_name="jrock",
            total_searched=0
        )
        assert result.match_count == 0
        assert len(result.errors) == 0
    
    def test_result_with_matches(self):
        """Test result with matches."""
        result = PhotoSearchResult(
            query="find photos of jrock",
            person_name="jrock",
            total_searched=50,
            matches=[
                PhotoMatch(
                    media_id="123",
                    filename="photo1.jpg",
                    local_path=Path("/cache/photo1.jpg"),
                    match_confidence=0.85,
                    matched_person="jrock_reference"
                )
            ]
        )
        assert result.match_count == 1
        assert result.matches[0].match_confidence == 0.85


class TestPhotoService:
    """Test suite for PhotoService."""
    
    def test_init_default(self):
        """Test service initialization with defaults."""
        with patch('src.app.ingest.photo_service.GooglePhotosProvider'):
            with patch('src.app.ingest.photo_service.VisionProcessor'):
                service = PhotoService()
                assert service._initialized is False
    
    def test_get_photo_context_empty(self):
        """Test context generation with no matches."""
        service = PhotoService.__new__(PhotoService)
        result = PhotoSearchResult(
            query="test",
            person_name="jrock",
            total_searched=10,
            matches=[]
        )
        context = service.get_photo_context(result)
        assert "No photos of jrock were found" in context
    
    def test_get_photo_context_with_matches(self):
        """Test context generation with matches."""
        service = PhotoService.__new__(PhotoService)
        result = PhotoSearchResult(
            query="test",
            person_name="jrock",
            total_searched=50,
            matches=[
                PhotoMatch(
                    media_id="1",
                    filename="photo1.jpg",
                    local_path=None,
                    match_confidence=0.9,
                    matched_person="jrock",
                    photo_date=datetime(2026, 2, 7)
                ),
                PhotoMatch(
                    media_id="2",
                    filename="photo2.jpg",
                    local_path=None,
                    match_confidence=0.85,
                    matched_person="jrock",
                    photo_date=datetime(2026, 2, 7)
                )
            ]
        )
        context = service.get_photo_context(result)
        assert "Found 2 photos" in context
        assert "February 07, 2026" in context
        assert "87.5%" in context or "88%" in context  # Average confidence


class TestPhotoMatch:
    """Test suite for PhotoMatch dataclass."""
    
    def test_photo_match_creation(self):
        """Test PhotoMatch can be created."""
        match = PhotoMatch(
            media_id="abc123",
            filename="vacation.jpg",
            local_path=Path("/cache/vacation.jpg"),
            match_confidence=0.92,
            matched_person="jrock_reference",
            photo_date=datetime.now()
        )
        assert match.media_id == "abc123"
        assert match.match_confidence == 0.92
