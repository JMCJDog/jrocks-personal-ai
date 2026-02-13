
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from .model_registry import ModelRegistry, ModelTier

# Configure logging
logger = logging.getLogger(__name__)

class ModelProvider(ABC):
    """Abstract base class for model providers."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, images: Optional[List[bytes]] = None, messages: Optional[List[Dict[str, Any]]] = None, **kwargs) -> str:
        """Generate a response from the model.
        
        Args:
             prompt: The latest user prompt (or full prompt if messages not used).
             system_prompt: Optional system instructions.
             images: Optional images associated with the prompt.
             messages: Optional full conversation history [{'role': 'user', 'content': '...'}, ...].
             **kwargs: Additional model parameters.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (e.g., API key present)."""
        pass


class OllamaProvider(ModelProvider):
    """Provider for local Ollama models."""
    
    def __init__(self, model_name: str = "llama3.2"):
        self.model_name = model_name
        import ollama
        self.client = ollama.Client()

    def generate(self, prompt: str, system_prompt: Optional[str] = None, images: Optional[List[bytes]] = None, messages: Optional[List[Dict[str, Any]]] = None, **kwargs) -> str:
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        
        # Use full history if provided, otherwise construct from prompt
        if messages:
            # Append history (excluding system if we just added it)
            for m in messages:
                if m.get("role") != "system":
                    api_messages.append(m)
        else:
            # Legacy/Fallback behavior
            user_msg = {"role": "user", "content": prompt}
            if images:
                 user_msg["images"] = images
            api_messages.append(user_msg)
        
        # Ensure the *latest* prompt is in there if it wasn't in messages
        # (SLMEngine typically adds it to context first, so it would be in messages)

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=api_messages,
                options={
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 2048),
                }
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    def is_available(self) -> bool:
        try:
            self.client.list()
            return True
        except:
            return False


class GeminiProvider(ModelProvider):
    """Provider for Google Gemini models via the new google-genai SDK."""
    
    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        self.model_name = model_name
        from google import genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    def generate(self, prompt: str, system_prompt: Optional[str] = None, images: Optional[List[bytes]] = None, messages: Optional[List[Dict[str, Any]]] = None, **kwargs) -> str:
        if not self.client:
            raise ValueError("Google API Key not configured.")
        
        from google.genai import types
        
        # Build contents list
        contents = []
        if messages:
            for m in messages:
                if m.get("role") == "system":
                    continue  # Handled via system_instruction in config
                role = "user" if m.get("role") == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=m.get("content", ""))]
                ))
        else:
            # Build from prompt
            parts = [types.Part.from_text(text=prompt)]
            if images:
                import PIL.Image
                import io
                for img_bytes in images:
                    parts.append(types.Part.from_image(image=PIL.Image.open(io.BytesIO(img_bytes))))
            contents.append(types.Content(role="user", parts=parts))

        # Build config
        config = types.GenerateContentConfig(
            temperature=kwargs.get("temperature", 0.7),
            max_output_tokens=kwargs.get("max_tokens", 2048),
        )
        if system_prompt:
            config.system_instruction = system_prompt

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    def is_available(self) -> bool:
        return bool(os.getenv("GOOGLE_API_KEY"))


class AnthropicProvider(ModelProvider):
    """Provider for Anthropic Claude models."""
    
    def __init__(self, model_name: str = "claude-3-5-sonnet-20240620"):
        self.model_name = model_name
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = None

    def generate(self, prompt: str, system_prompt: Optional[str] = None, images: Optional[List[bytes]] = None, messages: Optional[List[Dict[str, Any]]] = None, **kwargs) -> str:
        if not self.client:
            raise ValueError("Anthropic API Key not configured.")
        
        messages = [{"role": "user", "content": prompt}]
        # Handle images if needed (requires base64 encoding for Anthropic)
        if images:
            import base64
            content_list = []
            for img_bytes in images:
                b64_data = base64.b64encode(img_bytes).decode('utf-8')
                content_list.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg", # Assuming JPEG for now, ideally detect
                        "data": b64_data,
                    }
                })
            content_list.append({"type": "text", "text": prompt})
            messages = [{"role": "user", "content": content_list}]

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=kwargs.get("max_tokens", 1024),
                temperature=kwargs.get("temperature", 0.7),
                system=system_prompt if system_prompt else "",
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise

    def is_available(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))


class OpenAIProvider(ModelProvider):
    """Provider for OpenAI GPT models."""
    
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            self.client = None

    def generate(self, prompt: str, system_prompt: Optional[str] = None, images: Optional[List[bytes]] = None, messages: Optional[List[Dict[str, Any]]] = None, **kwargs) -> str:
        if not self.client:
            raise ValueError("OpenAI API Key not configured.")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        # Image handling for OpenAI is similar to others, omitted for brevity but can be added if needed

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2048),
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    def is_available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))


class ModelRouter:
    """Routes requests to the appropriate model provider based on configuration."""
    
    def __init__(self):
        self._providers: Dict[str, ModelProvider] = {}
        # Pre-load settings
        from .settings import settings_manager
        self.settings = settings_manager.get()

    def get_provider(self, model_name: str = None) -> ModelProvider:
        """Get or create a provider for the specific model.
        
        If model_name is None, use the default from settings.
        """
        # Refresh settings in case they changed
        from .settings import settings_manager
        self.settings = settings_manager.get()
        
        if not model_name:
            model_name = self.settings.default_model.model_name
            
        # Check if model_name is a Tier
        try:
            tier = ModelTier(model_name.lower())
            resolved_model = ModelRegistry.get_best_model(tier, os.environ)
            if resolved_model:
                model_name = resolved_model
            else:
                # Fallback if no API keys found for tier
                logger.warning(f"No API keys found for tier {tier}, falling back to local llama3.2")
                model_name = "llama3.2"
        except ValueError:
            pass # Not a tier, assume it's a specific model name

        if model_name in self._providers:
            return self._providers[model_name]
        
        provider = self._create_provider(model_name)
        self._providers[model_name] = provider
        return provider

    def _create_provider(self, model_name: str) -> ModelProvider:
        """Factory method to create the correct provider."""
        # Check provider type based on model name via Registry (robust) or fallback to simple string check
        provider_type = ModelRegistry.get_provider_for_model(model_name)
        
        # Override provider type based on settings if matching default model
        if model_name == self.settings.default_model.model_name:
             provider_type = self.settings.default_model.provider

        if provider_type == "gemini":
            return GeminiProvider(model_name)
        elif provider_type == "claude":
            return AnthropicProvider(model_name)
        elif provider_type == "openai":
            return OpenAIProvider(model_name)
        else:
            # Default to Ollama for everything else (llama, mistral, etc.)
            return OllamaProvider(model_name)
