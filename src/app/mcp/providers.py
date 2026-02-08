"""LLM Providers - Unified interface for best-in-class LLMs.

Provides a provider-agnostic layer for Claude, GPT-4, Gemini,
and local models (Ollama) with MCP tool integration.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import os
from ..core.model_registry import ModelRegistry, ModelTier


class ProviderType(str, Enum):
    """Supported LLM providers."""
    
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    
    provider_type: ProviderType
    api_key: Optional[str] = None
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    base_url: Optional[str] = None
    timeout: int = 60
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        # Set default models per provider
        if not self.model:
            defaults = {
                ProviderType.CLAUDE: "claude-sonnet-4-20250514",
                ProviderType.OPENAI: "gpt-4o",
                ProviderType.GEMINI: "gemini-2.0-flash",
                ProviderType.OLLAMA: "llama3.2",
            }
            self.model = defaults.get(self.provider_type, "")


@dataclass
class ProviderMessage:
    """A message for the LLM."""
    
    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ProviderResponse:
    """Response from an LLM provider."""
    
    content: str
    model: str
    provider: ProviderType
    tool_calls: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    finish_reason: str = "stop"
    raw_response: Optional[Any] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers.
    
    Provides a unified interface for all LLM integrations
    with support for MCP tools and streaming.
    
    Example:
        >>> provider = ClaudeProvider(config)
        >>> response = await provider.complete(messages, tools)
    """
    
    def __init__(self, config: ProviderConfig) -> None:
        """Initialize the provider.
        
        Args:
            config: Provider configuration.
        """
        self.config = config
        self._client = None
    
    @property
    def provider_type(self) -> ProviderType:
        """Get the provider type."""
        return self.config.provider_type
    
    @abstractmethod
    async def complete(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> ProviderResponse:
        """Generate a completion.
        
        Args:
            messages: Conversation messages.
            tools: Optional MCP tools in provider format.
            **kwargs: Additional provider-specific options.
        
        Returns:
            ProviderResponse: The completion response.
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a completion.
        
        Args:
            messages: Conversation messages.
            tools: Optional MCP tools.
            **kwargs: Additional options.
        
        Yields:
            str: Completion chunks.
        """
        pass
    
    def _prepare_messages(self, messages: list[ProviderMessage]) -> list[dict]:
        """Convert messages to provider format."""
        return [
            {"role": m.role, "content": m.content}
            for m in messages
        ]


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider.
    
    Supports Claude 3.5 Sonnet, Opus, and other Claude models
    with native tool use capabilities.
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        if config is None:
            config = ProviderConfig(
                provider_type=ProviderType.CLAUDE,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        super().__init__(config)
    
    def _get_client(self):
        """Get or create the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                )
            except ImportError:
                raise ImportError("anthropic package required: pip install anthropic")
        return self._client
    
    async def complete(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> ProviderResponse:
        """Generate completion with Claude."""
        client = self._get_client()
        
        # Separate system message
        system = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})
        
        # Build request
        request = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": chat_messages,
        }
        if system:
            request["system"] = system
        if tools:
            request["tools"] = tools
        
        response = await client.messages.create(**request, **kwargs)
        
        # Extract tool calls if present
        tool_calls = []
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })
        
        return ProviderResponse(
            content=content,
            model=response.model,
            provider=ProviderType.CLAUDE,
            tool_calls=tool_calls,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
            raw_response=response,
        )
    
    async def stream(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream completion with Claude."""
        client = self._get_client()
        
        system = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})
        
        request = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": chat_messages,
        }
        if system:
            request["system"] = system
        
        async with client.messages.stream(**request, **kwargs) as stream:
            async for text in stream.text_stream:
                yield text


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider.
    
    Supports GPT-4, GPT-4 Turbo, and other OpenAI models
    with function calling capabilities.
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        if config is None:
            config = ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key=os.getenv("OPENAI_API_KEY"),
            )
        super().__init__(config)
    
    def _get_client(self):
        """Get or create the OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                )
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        return self._client
    
    async def complete(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> ProviderResponse:
        """Generate completion with GPT."""
        client = self._get_client()
        
        chat_messages = self._prepare_messages(messages)
        
        request = {
            "model": self.config.model,
            "messages": chat_messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        if tools:
            request["tools"] = tools
        
        response = await client.chat.completions.create(**request, **kwargs)
        
        choice = response.choices[0]
        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })
        
        return ProviderResponse(
            content=choice.message.content or "",
            model=response.model,
            provider=ProviderType.OPENAI,
            tool_calls=tool_calls,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
            finish_reason=choice.finish_reason,
            raw_response=response,
        )
    
    async def stream(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream completion with GPT."""
        client = self._get_client()
        
        chat_messages = self._prepare_messages(messages)
        
        stream = await client.chat.completions.create(
            model=self.config.model,
            messages=chat_messages,
            max_tokens=self.config.max_tokens,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class GeminiProvider(LLMProvider):
    """Google Gemini provider.
    
    Supports Gemini Pro, Ultra, and other Google models.
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        if config is None:
            config = ProviderConfig(
                provider_type=ProviderType.GEMINI,
                api_key=os.getenv("GOOGLE_API_KEY"),
            )
        super().__init__(config)
    
    def _get_client(self):
        """Get or create the Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.config.api_key)
                self._client = genai.GenerativeModel(self.config.model)
            except ImportError:
                raise ImportError("google-generativeai required: pip install google-generativeai")
        return self._client
    
    async def complete(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> ProviderResponse:
        """Generate completion with Gemini."""
        client = self._get_client()
        
        # Convert messages to Gemini format
        contents = []
        for m in messages:
            if m.role == "system":
                continue  # Gemini handles system differently
            role = "user" if m.role == "user" else "model"
            contents.append({"role": role, "parts": [m.content]})
        
        response = await client.generate_content_async(
            contents,
            generation_config={
                "max_output_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            },
        )
        
        return ProviderResponse(
            content=response.text,
            model=self.config.model,
            provider=ProviderType.GEMINI,
            raw_response=response,
        )
    
    async def stream(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream completion with Gemini."""
        client = self._get_client()
        
        contents = []
        for m in messages:
            if m.role != "system":
                role = "user" if m.role == "user" else "model"
                contents.append({"role": role, "parts": [m.content]})
        
        response = await client.generate_content_async(
            contents,
            stream=True,
        )
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text


class OllamaProvider(LLMProvider):
    """Ollama local model provider.
    
    Supports all Ollama models including Llama, Mistral, etc.
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        if config is None:
            config = ProviderConfig(
                provider_type=ProviderType.OLLAMA,
                base_url="http://localhost:11434",
            )
        super().__init__(config)
    
    def _get_client(self):
        """Get or create the Ollama client."""
        if self._client is None:
            try:
                import ollama
                self._client = ollama.AsyncClient(
                    host=self.config.base_url
                )
            except ImportError:
                raise ImportError("ollama package required: pip install ollama")
        return self._client
    
    async def complete(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> ProviderResponse:
        """Generate completion with Ollama."""
        client = self._get_client()
        
        chat_messages = self._prepare_messages(messages)
        
        response = await client.chat(
            model=self.config.model,
            messages=chat_messages,
            options={
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        )
        
        return ProviderResponse(
            content=response["message"]["content"],
            model=self.config.model,
            provider=ProviderType.OLLAMA,
            raw_response=response,
        )
    
    async def stream(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream completion with Ollama."""
        client = self._get_client()
        
        chat_messages = self._prepare_messages(messages)
        
        async for chunk in await client.chat(
            model=self.config.model,
            messages=chat_messages,
            stream=True,
        ):
            if "message" in chunk and "content" in chunk["message"]:
                yield chunk["message"]["content"]


def get_provider(
    provider_type: str | ProviderType | ModelTier,
    **kwargs
) -> LLMProvider:
    """Factory function to get an LLM provider.
    
    Args:
        provider_type: Provider type string, enum, or ModelTier.
        **kwargs: Provider configuration options.
    
    Returns:
        LLMProvider: Configured provider instance.
    
    Example:
        >>> provider = get_provider("claude", api_key="...")
        >>> provider = get_provider(ModelTier.SMART)
    """
    # Handle ModelTier or string that matches a tier
    tier_input = None
    if isinstance(provider_type, ModelTier):
        tier_input = provider_type
    elif isinstance(provider_type, str):
        try:
            tier_input = ModelTier(provider_type.lower())
        except ValueError:
            pass
            
    if tier_input:
        # Resolve the best model for this tier
        best_model = ModelRegistry.get_best_model(tier_input, os.environ)
        if not best_model:
            # Fallback to local if no API keys found but tier requested
            if tier_input == ModelTier.LOCAL:
                 best_model = "llama3.2"
            else:
                 # Default fallback to ollama/llama3.2 if nothing else matches
                 best_model = "llama3.2"
        
        # Now determine provider for this model
        provider_str = ModelRegistry.get_provider_for_model(best_model)
        provider_type = ProviderType(provider_str)
        
        # Ensure model is passed in config if not explicitly provided
        if "model" not in kwargs:
            kwargs["model"] = best_model

    if isinstance(provider_type, str):
        provider_type = ProviderType(provider_type.lower())
    
    config = ProviderConfig(provider_type=provider_type, **kwargs)
    
    providers = {
        ProviderType.CLAUDE: ClaudeProvider,
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.GEMINI: GeminiProvider,
        ProviderType.OLLAMA: OllamaProvider,
    }
    
    provider_class = providers.get(provider_type)
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_type}")
    
    return provider_class(config)
