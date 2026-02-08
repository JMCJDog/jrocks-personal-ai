"""STT Module - Speech-to-Text using OpenAI Whisper.

Provides local transcription capabilities for voice interactions.
"""

import logging
import os
import torch
from pathlib import Path
from typing import Optional
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class STTEngine:
    """Engine for transcribing audio to text using OpenAI Whisper."""
    
    def __init__(self, model_size: str = "base", device: Optional[str] = None) -> None:
        """Initialize the STT engine.
        
        Args:
            model_size: Size of the Whisper model (tiny, base, small, medium, large).
            device: Computing device (cpu, cuda). Auto-detects if None.
        """
        self.model_size = model_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model = None
        
        logger.info(f"Initializing STT Engine with model '{model_size}' on '{self.device}'")

    @property
    def model(self):
        """Lazy loader for the Whisper model."""
        if self._model is None:
            try:
                import whisper
                self._model = whisper.load_model(self.model_size, device=self.device)
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                raise
        return self._model

    def transcribe(self, audio_path: str | Path) -> str:
        """Transcribe an audio file to text.
        
        Args:
            audio_path: Path to the audio file.
            
        Returns:
            Transcribed text.
        """
        path = Path(audio_path)
        if not path.exists():
            logger.error(f"Audio file not found: {path}")
            return ""

        try:
            logger.info(f"Transcribing {path.name}...")
            result = self.model.transcribe(str(path))
            text = result.get("text", "").strip()
            logger.info(f"Transcription complete: {text[:50]}...")
            return text
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return ""

    def transcribe_buffer(self, audio_buffer: np.ndarray) -> str:
        """Transcribe audio from a numpy buffer (for live streaming).
        
        Args:
            audio_buffer: Numpy array of audio samples (16kHz).
            
        Returns:
            Transcribed text.
        """
        try:
            # Whisper expects float32
            if audio_buffer.dtype != np.float32:
                audio_buffer = audio_buffer.astype(np.float32)
            
            result = self.model.transcribe(audio_buffer)
            return result.get("text", "").strip()
        except Exception as e:
            logger.error(f"Error transcribing buffer: {e}")
            return ""

if __name__ == "__main__":
    # Test script
    import sys
    engine = STTEngine()
    if len(sys.argv) > 1:
        print(f"Result: {engine.transcribe(sys.argv[1])}")
    else:
        print("Usage: python stt.py <audio_file>")
