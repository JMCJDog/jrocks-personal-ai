"""Audio/Video Processor - Transcribe and analyze media content.

Handles audio and video files for personal AI training, including
transcription via Whisper and video frame analysis.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import timedelta
import hashlib


@dataclass
class MediaSegment:
    """A segment of transcribed content."""
    
    text: str
    start_time: float  # seconds
    end_time: float
    confidence: float = 1.0
    speaker: Optional[str] = None
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    def format_timestamp(self) -> str:
        """Format timestamp as HH:MM:SS."""
        start = str(timedelta(seconds=int(self.start_time)))
        return f"[{start}]"


@dataclass
class ProcessedMedia:
    """A fully processed audio/video file."""
    
    file_path: str
    file_name: str
    media_type: str  # "audio" or "video"
    duration: float  # seconds
    transcript: str = ""
    segments: list[MediaSegment] = field(default_factory=list)
    language: str = "en"
    metadata: dict = field(default_factory=dict)
    
    @property
    def id(self) -> str:
        """Generate unique ID for this media."""
        return hashlib.md5(self.file_path.encode()).hexdigest()
    
    def to_text(self) -> str:
        """Convert to text for embedding."""
        parts = [f"Media: {self.file_name} ({self.media_type})"]
        
        if self.transcript:
            parts.append(f"Transcript:\n{self.transcript[:2000]}")
        
        return "\n".join(parts)


class AudioVideoProcessor:
    """Process audio and video files for personal AI training.
    
    Uses OpenAI Whisper for transcription when available,
    with fallback to basic metadata extraction.
    
    Example:
        >>> processor = AudioVideoProcessor()
        >>> result = processor.process_file("interview.mp3")
        >>> print(result.transcript)
    """
    
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma", ".aac"}
    VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv"}
    
    def __init__(
        self,
        whisper_model: str = "base",
        use_gpu: bool = False,
    ) -> None:
        """Initialize the media processor.
        
        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large).
            use_gpu: Whether to use GPU for transcription.
        """
        self.whisper_model = whisper_model
        self.use_gpu = use_gpu
        self._whisper = None
    
    @property
    def whisper(self):
        """Lazy-load Whisper model."""
        if self._whisper is None:
            try:
                import whisper
                device = "cuda" if self.use_gpu else "cpu"
                self._whisper = whisper.load_model(self.whisper_model, device=device)
            except ImportError:
                pass  # Whisper not available
        return self._whisper
    
    def process_file(self, file_path: str | Path) -> ProcessedMedia:
        """Process an audio or video file.
        
        Args:
            file_path: Path to the media file.
        
        Returns:
            ProcessedMedia: Processed media with transcript.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {path}")
        
        ext = path.suffix.lower()
        
        if ext in self.AUDIO_EXTENSIONS:
            media_type = "audio"
        elif ext in self.VIDEO_EXTENSIONS:
            media_type = "video"
        else:
            raise ValueError(f"Unsupported media format: {ext}")
        
        # Get basic info
        duration = self._get_duration(path)
        
        result = ProcessedMedia(
            file_path=str(path),
            file_name=path.name,
            media_type=media_type,
            duration=duration,
        )
        
        # Transcribe if Whisper is available
        if self.whisper:
            self._transcribe(path, result)
        
        return result
    
    def _get_duration(self, path: Path) -> float:
        """Get media duration using ffprobe or mutagen.
        
        Args:
            path: Path to media file.
        
        Returns:
            float: Duration in seconds.
        """
        # Try mutagen for audio
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(str(path))
            if audio and audio.info:
                return audio.info.length
        except ImportError:
            pass
        except Exception:
            pass
        
        # Try ffprobe
        try:
            import subprocess
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(path)
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except (subprocess.SubprocessError, ValueError, OSError):
            pass
        
        return 0.0
    
    def _transcribe(self, path: Path, result: ProcessedMedia) -> None:
        """Transcribe media using Whisper.
        
        Args:
            path: Path to media file.
            result: ProcessedMedia to populate.
        """
        try:
            transcription = self.whisper.transcribe(str(path))
            
            result.transcript = transcription.get("text", "")
            result.language = transcription.get("language", "en")
            
            # Extract segments
            for seg in transcription.get("segments", []):
                result.segments.append(MediaSegment(
                    text=seg.get("text", ""),
                    start_time=seg.get("start", 0),
                    end_time=seg.get("end", 0),
                ))
                
        except Exception:
            pass  # Continue without transcript
    
    def process_directory(
        self,
        directory: str | Path,
        recursive: bool = True
    ) -> list[ProcessedMedia]:
        """Process all media files in a directory.
        
        Args:
            directory: Directory to process.
            recursive: Whether to search subdirectories.
        
        Returns:
            list: List of processed media files.
        """
        dir_path = Path(directory)
        all_extensions = self.AUDIO_EXTENSIONS | self.VIDEO_EXTENSIONS
        
        pattern = "**/*" if recursive else "*"
        results = []
        
        for path in dir_path.glob(pattern):
            if path.suffix.lower() in all_extensions:
                try:
                    result = self.process_file(path)
                    results.append(result)
                except Exception:
                    continue
        
        return results


def transcribe_media(file_path: str) -> ProcessedMedia:
    """Transcribe an audio or video file.
    
    Args:
        file_path: Path to the media file.
    
    Returns:
        ProcessedMedia: Processed media with transcript.
    """
    processor = AudioVideoProcessor()
    return processor.process_file(file_path)
