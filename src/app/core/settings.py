"""Settings Management Module.

Handles loading, saving, and accessing application definitions.
Persists configuration to data/settings.json.
"""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Constants
SETTINGS_FILE = Path("data/settings.json")

class PersonaTrait(BaseModel):
    """A single personality trait."""
    name: str
    description: str
    weight: float = 1.0

class WritingStyle(BaseModel):
    """Writing style configuration."""
    tone: str = "conversational"
    formality: str = "casual"
    humor_level: float = 0.6
    verbosity: str = "moderate"
    emoji_usage: bool = True

class ModelConfig(BaseModel):
    """LLM Configuration."""
    provider: str = "ollama"  # ollama, gemini, claude, openai
    model_name: str = "llama3.2"
    temperature: float = 0.7
    max_tokens: int = 2048

class AppSettings(BaseModel):
    """Global Application Settings."""
    # Persona
    persona_name: str = "Jared 'JRock' Cohen"
    persona_traits: List[PersonaTrait] = Field(default_factory=list)
    writing_style: WritingStyle = Field(default_factory=WritingStyle)
    
    # Models
    default_model: ModelConfig = Field(default_factory=ModelConfig)
    
    # API Keys (Optional - usually env vars are better, but UI might want to override)
    # We will only store these if explicitly set via UI to override env vars
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    class Config:
        validate_assignment = True

class SettingsManager:
    """Manages loading and saving of settings."""
    
    def __init__(self):
        self._settings: Optional[AppSettings] = None
        self._load()

    def _load(self):
        """Load settings from JSON or create default."""
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                self._settings = AppSettings(**data)
            except Exception as e:
                print(f"Error loading settings: {e}. Using defaults.")
                self._settings = self._create_defaults()
        else:
            self._settings = self._create_defaults()
            self.save()

    def _create_defaults(self) -> AppSettings:
        """Create default settings matching legacy persona.py."""
        return AppSettings(
            persona_name="Jared 'JRock' Cohen",
            persona_traits=[
                PersonaTrait(name="Sarcastic & Witty", description="Uses dry humor, sarcasm, and wit.", weight=1.6),
                PersonaTrait(name="Technical", description="Deep understanding, simple explanations.", weight=1.0),
                PersonaTrait(name="Direct & Concise", description="Minimal fluff. Point blank.", weight=2.0),
                PersonaTrait(name="Innovative", description="Creative solutions.", weight=1.1),
            ],
            writing_style=WritingStyle(
                tone="sarcastic",
                formality="informal",
                humor_level=0.9,
                verbosity="concise",
                emoji_usage=True
            ),
            default_model=ModelConfig(
                provider="ollama",
                model_name="qwen2.5:14b",
                temperature=0.7,
                max_tokens=4096
            )
        )

    def get(self) -> AppSettings:
        """Get current settings."""
        if not self._settings:
            self._load()
        return self._settings

    def save(self, new_settings: AppSettings = None):
        """Save settings to file."""
        if new_settings:
            self._settings = new_settings
        
        # Ensure directory exists
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        SETTINGS_FILE.write_text(
            self._settings.model_dump_json(indent=4), 
            encoding="utf-8"
        )

# Global Instance
settings_manager = SettingsManager()
