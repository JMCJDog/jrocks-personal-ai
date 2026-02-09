"""SLM Engine - Small Language Model integration for JRock's Personal AI.

Provides a unified interface for interacting with local language models
via Ollama, with support for persona injection and context management.
"""

from typing import Optional
from dataclasses import dataclass, field
import ollama


@dataclass
class ModelConfig:
    """Configuration for the SLM model."""
    
    model_name: str = "fast"  # Defaults to dynamic "fast" tier (e.g. Gemini Flash)
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = ""
    context_window: int = 4096


@dataclass
class Message:
    """A single message in a conversation."""
    
    role: str  # "user", "assistant", or "system"
    content: str
    images: Optional[list[bytes]] = None


@dataclass
class ConversationContext:
    """Maintains conversation history and context."""
    
    messages: list[Message] = field(default_factory=list)
    max_history: int = 20
    
    def add_message(self, role: str, content: str, images: Optional[list[bytes]] = None) -> None:
        """Add a message to the conversation history.
        
        Args:
            role: The role of the message sender.
            content: The message content.
            images: Optional list of image bytes.
        """
        self.messages.append(Message(role=role, content=content, images=images))
        
        # Trim history if too long (keep system messages)
        if len(self.messages) > self.max_history:
            system_msgs = [m for m in self.messages if m.role == "system"]
            other_msgs = [m for m in self.messages if m.role != "system"]
            self.messages = system_msgs + other_msgs[-(self.max_history - len(system_msgs)):]
    
    def get_messages_for_api(self) -> list[dict]:
        """Convert messages to the format expected by Ollama API.
        
        Returns:
            list: List of message dictionaries.
        """
        api_messages = []
        for m in self.messages:
            msg = {"role": m.role, "content": m.content}
            if m.images:
                msg["images"] = m.images
            api_messages.append(msg)
        return api_messages
    
    def clear(self) -> None:
        """Clear conversation history except system messages."""
        self.messages = [m for m in self.messages if m.role == "system"]


class SLMEngine:
    """Engine for interacting with Language Models via ModelRouter.
    
    Provides a high-level interface for generating responses with
    persona injection and conversation context management, supporting
    multiple providers (Ollama, Gemini, Anthropic, OpenAI).
    
    Example:
        >>> engine = SLMEngine()
        >>> response = engine.generate("Hello, who are you?")
        >>> print(response)
    """
    
    def __init__(self, config: Optional[ModelConfig] = None) -> None:
        """Initialize the SLM engine.
        
        Args:
            config: Optional model configuration. Uses defaults if not provided.
        """
        self.config = config or ModelConfig()
        self.context = ConversationContext()
        
        from .model_router import ModelRouter
        self.router = ModelRouter()
        
        # Initialize with system prompt if provided
        if self.config.system_prompt:
            self.context.add_message("system", self.config.system_prompt)
    
    def set_system_prompt(self, prompt: str) -> None:
        """Set or update the system prompt.
        
        Args:
            prompt: The system prompt to use for all conversations.
        """
        # Remove existing system messages
        self.context.messages = [m for m in self.context.messages if m.role != "system"]
        # Add new system prompt at the beginning
        self.context.messages.insert(0, Message(role="system", content=prompt))
    
    def generate(
        self,
        user_message: str,
        images: Optional[list[bytes]] = None,
        stream: bool = False,
        context: Optional[dict] = None
    ) -> str:
        """Generate a response to the user message.
        
        Args:
            user_message: The user's input message.
            images: Optional list of image bytes for multimodal models.
            stream: Whether to stream the response (not yet implemented).
            context: Optional context dictionary (e.g. for agent routing).
        
        Returns:
            str: The model's response.
        """
        # Add user message to context
        self.context.add_message("user", user_message, images=images)
        
        try:
            # Get the appropriate provider
            provider = self.router.get_provider(self.config.model_name)
            
            # Construct system prompt from context if needed
            system_prompt = next((m.content for m in self.context.messages if m.role == "system"), None)
            
            # Prepare structured messages for the provider
            # This allows providers (like Ollama) to see distinct turns instead of a flat string
            api_messages = []
            for msg in self.context.messages:
                # Skip system messages here as they are often handled separately by providers
                # (ModelRouter logic usually prepends system_prompt if passed)
                if msg.role != "system":
                    m_dict = {"role": msg.role, "content": msg.content}
                    if msg.images:
                        m_dict["images"] = msg.images
                    api_messages.append(m_dict)
            
            response_text = provider.generate(
                prompt=user_message,
                system_prompt=system_prompt,
                images=images,
                messages=api_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            # Add assistant response to context
            self.context.add_message("assistant", response_text)
            
            return response_text
            
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            return error_msg
    
    def reset_conversation(self) -> None:
        """Reset the conversation context."""
        self.context.clear()
    
    def is_model_available(self) -> bool:
        """Check if the configured model is available.
        
        Returns:
            bool: True if the model is available.
        """
        try:
            provider = self.router.get_provider(self.config.model_name)
            return provider.is_available()
        except Exception:
            return False


# Convenience function for quick generation
def quick_generate(
    message: str,
    model: str = "llama3.2",
    system_prompt: Optional[str] = None
) -> str:
    """Quick generation without maintaining conversation state.
    
    Args:
        message: The user message to respond to.
        model: The model name to use.
        system_prompt: Optional system prompt.
    
    Returns:
        str: The model's response.
    """
    config = ModelConfig(model_name=model, system_prompt=system_prompt or "")
    engine = SLMEngine(config)
    # For quick gen, we don't need history, so just pass message directly to avoid formatting
    # engine.generate adds to context, which is fine
    return engine.generate(message)
