"""Model Registry - Central definition of model capabilities and tiers.

Defines model tiers (FAST, SMART, etc.) and lists of candidate models
ordered by preference. Used by the ModelRouter to select the best
available model for a given task.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict
import os

class ModelTier(str, Enum):
    """Capability tiers for model selection."""
    FAST = "fast"              # Low latency, lower cost (e.g., Gemini Flash, Haiku)
    BALANCED = "balanced"      # Good mix of intelligence and speed (e.g., GPT-4o, Sonnet 3.5)
    SMART = "smart"            # Maximum reasoning capability (e.g., Opus, GPT-4 Turbo)
    CODING = "coding"          # Optimized for code generation (e.g., Sonnet 3.5, DeepSeek)
    VISION = "vision"          # Multimodal capabilities (e.g., GPT-4o, Gemini Pro Vision)
    LOCAL = "local"            # Local models only (Ollama)
    SMART_LOCAL = "smart_local"    # Best local model for complex reasoning (qwen2.5:14b)
    UNCENSORED = "uncensored"      # Unrestricted local model (dolphin3)

@dataclass
class ModelInfo:
    """Metadata about a specific model."""
    id: str
    provider: str
    context_window: int = 128000
    description: str = ""

class ModelRegistry:
    """
    Central registry for model capabilities and preferences.
    """
    
    # Define models in order of preference within each tier
    _TIERS: Dict[ModelTier, List[str]] = {
        ModelTier.SMART: [
            "claude-3-opus-20240229",
            "gpt-4-turbo",
            "gemini-3-pro-preview",
        ],
        ModelTier.BALANCED: [
            "claude-3-5-sonnet-20240620",
            "gpt-4o",
            "gemini-3-flash-preview",
        ],
        ModelTier.FAST: [
            "gemini-3-flash-preview",
            "claude-3-haiku-20240307",
            "gpt-3.5-turbo",
        ],
        ModelTier.CODING: [
            "claude-3-5-sonnet-20240620",
            "gpt-4o",
            "claude-3-opus-20240229",
        ],
        ModelTier.VISION: [
            "gpt-4o",
            "claude-3-5-sonnet-20240620",
            "gemini-3-pro-preview",
        ],
        ModelTier.LOCAL: [
            "qwen2.5:14b",
            "dolphin3",
            "llama3.2",
            "mistral",
        ],
        ModelTier.SMART_LOCAL: [
            "qwen2.5:14b",   # Best local reasoning model
            "llama3.1:8b",
            "llama3.2",
        ],
        ModelTier.UNCENSORED: [
            "dolphin3",       # Explicitly uncensored fine-tune
            "dolphin-mistral",
            "llama3.2",
        ],
    }

    # Map model IDs to providers (heuristic)
    @staticmethod
    def get_provider_for_model(model_id: str) -> str:
        """Determine the provider ID based on the model ID string."""
        model_id_lower = model_id.lower()
        if "claude" in model_id_lower: return "claude"
        if "gpt" in model_id_lower: return "openai"
        if "gemini" in model_id_lower: return "gemini"
        # All local / Ollama models
        if any(name in model_id_lower for name in [
            "llama", "mistral", "gemma", "dolphin", "qwen", "phi", "deepseek", "yi", "neural"
        ]):
            return "ollama"
        # Fallback default
        return "ollama"

    @classmethod
    def get_candidates(cls, tier: ModelTier) -> List[str]:
        """Get the list of candidate models for a specific tier."""
        return cls._TIERS.get(tier, [])

    @classmethod
    def get_best_model(cls, tier: ModelTier, api_keys: Dict[str, str]) -> Optional[str]:
        """
        Returns the best available model for the tier based on provided API keys.
        
        Args:
            tier: The desired capability tier.
            api_keys: Dictionary of available API keys (ANTHROPIC_API_KEY, etc.)
            
        Returns:
            The model ID of the best available model, or None if no match found.
        """
        candidates = cls.get_candidates(tier)
        for model in candidates:
            provider = cls.get_provider_for_model(model)
            
            # Check availability based on keys
            if provider == "claude" and api_keys.get("ANTHROPIC_API_KEY"):
                return model
            if provider == "openai" and api_keys.get("OPENAI_API_KEY"):
                return model
            if provider == "gemini" and api_keys.get("GOOGLE_API_KEY"):
                return model
            if provider == "ollama":
                # Local models are assumed "available" regarding keys,
                # though runtime might fail if not installed.
                # Use them as fallback.
                return model
                
        return None
