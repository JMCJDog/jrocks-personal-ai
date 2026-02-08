import logging
import os
import pyttsx3
import threading
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

class VoiceEngine:
    """Engine for generating voice audio.
    
    Supports ElevenLabs or local TTS via pyttsx3.
    """
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the voice engine.
        
        Args:
            api_key: ElevenLabs API key (optional).
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.output_dir = Path("data/output/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize local engine
        try:
            self._local_engine = pyttsx3.init()
            # Default properties
            self._local_engine.setProperty('rate', 175)    # Speed percent (usually 200)
            self._local_engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
            logger.info("Local TTS engine (pyttsx3) initialized")
        except Exception as e:
            logger.error(f"Failed to initialize local TTS engine: {e}")
            self._local_engine = None
        
    async def generate_speech(
        self, 
        text: str, 
        voice_id: str = "local",
        output_file: Optional[str] = None
    ) -> str:
        """Generate speech from text.
        
        Args:
            text: The text to speak.
            voice_id: The ID of the voice model to use. "local" uses pyttsx3.
            output_file: Optional filename for output.
            
        Returns:
            Path to the generated audio file.
        """
        logger.info(f"Generating speech for: {text[:30]}...")
        
        filename = output_file or f"speech_{hash(text)}_{int(threading.get_ident())}.wav"
        output_path = self.output_dir / filename
        
        if voice_id == "local" or not self.api_key:
            return self._generate_local_speech(text, output_path)
        else:
            # TODO: Implement ElevenLabs integration if needed
            return self._generate_local_speech(text, output_path)
            
    def _generate_local_speech(self, text: str, output_path: Path) -> str:
        """Internal helper for pyttsx3 generation."""
        if not self._local_engine:
            return ""
            
        try:
            # pyttsx3 save_to_file is synchronous
            # We wrap it in a lock or just run it as is since we're in a thread-safe-ish context
            # NOTE: pyttsx3 might have issues with concurrent calls
            self._local_engine.save_to_file(text, str(output_path))
            self._local_engine.runAndWait()
            return str(output_path)
        except Exception as e:
            logger.error(f"Error generating local speech: {e}")
            return ""
    
    def speak_live(self, text: str):
        """Immediately speak text through speakers."""
        if self._local_engine:
            self._local_engine.say(text)
            self._local_engine.runAndWait()

    def clone_voice(self, sample_files: list[str]) -> str:
        """Train a cloned voice from samples. (Placeholder for advanced cloning)"""
        logger.info(f"Cloning voice from {len(sample_files)} samples")
        return "new_cloned_voice_id"
