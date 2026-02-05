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
    
    model_name: str = "llama3.2"
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = ""
    context_window: int = 4096


@dataclass
class Message:
    """A single message in a conversation."""
    
    role: str  # "user", "assistant", or "system"
    content: str


@dataclass
class ConversationContext:
    """Maintains conversation history and context."""
    
    messages: list[Message] = field(default_factory=list)
    max_history: int = 20
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history.
        
        Args:
            role: The role of the message sender.
            content: The message content.
        """
        self.messages.append(Message(role=role, content=content))
        
        # Trim history if too long (keep system messages)
        if len(self.messages) > self.max_history:
            system_msgs = [m for m in self.messages if m.role == "system"]
            other_msgs = [m for m in self.messages if m.role != "system"]
            self.messages = system_msgs + other_msgs[-(self.max_history - len(system_msgs)):]
    
    def get_messages_for_api(self) -> list[dict[str, str]]:
        """Convert messages to the format expected by Ollama API.
        
        Returns:
            list: List of message dictionaries.
        """
        return [{"role": m.role, "content": m.content} for m in self.messages]
    
    def clear(self) -> None:
        """Clear conversation history except system messages."""
        self.messages = [m for m in self.messages if m.role == "system"]


class SLMEngine:
    """Engine for interacting with Small Language Models via Ollama.
    
    Provides a high-level interface for generating responses with
    persona injection and conversation context management.
    
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
        self._client = ollama.Client()
        
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
        stream: bool = False
    ) -> str:
        """Generate a response to the user message.
        
        Args:
            user_message: The user's input message.
            stream: Whether to stream the response (not yet implemented).
        
        Returns:
            str: The model's response.
        """
        # Add user message to context
        self.context.add_message("user", user_message)
        
        try:
            response = self._client.chat(
                model=self.config.model_name,
                messages=self.context.get_messages_for_api(),
                options={
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                }
            )
            
            assistant_message = response["message"]["content"]
            
            # Add assistant response to context
            self.context.add_message("assistant", assistant_message)
            
            return assistant_message
            
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
            models = self._client.list()
            model_names = [m["name"] for m in models.get("models", [])]
            return any(self.config.model_name in name for name in model_names)
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
    return engine.generate(message)
