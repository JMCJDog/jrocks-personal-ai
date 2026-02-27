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
                ProviderType.GEMINI: "gemini-3-flash-preview",
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
    metadata: dict = field(default_factory=dict)


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
                continue
            
            if m.role == "assistant" and m.tool_calls:
                content_blocks = []
                if m.content:
                    content_blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["arguments"]
                    })
                chat_messages.append({"role": "assistant", "content": content_blocks})
            elif m.role == "tool":
                # Group tool results into a single user message if consecutive
                if chat_messages and chat_messages[-1]["role"] == "user" and isinstance(chat_messages[-1]["content"], list):
                    chat_messages[-1]["content"].append({
                        "type": "tool_result",
                        "tool_use_id": m.tool_call_id,
                        "content": m.content,
                    })
                else:
                    chat_messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": m.tool_call_id,
                            "content": m.content,
                        }]
                    })
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
                continue
            
            if m.role == "assistant" and m.tool_calls:
                content_blocks = []
                if m.content:
                    content_blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["arguments"]
                    })
                chat_messages.append({"role": "assistant", "content": content_blocks})
            elif m.role == "tool":
                if chat_messages and chat_messages[-1]["role"] == "user" and isinstance(chat_messages[-1]["content"], list):
                    chat_messages[-1]["content"].append({
                        "type": "tool_result",
                        "tool_use_id": m.tool_call_id,
                        "content": m.content,
                    })
                else:
                    chat_messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": m.tool_call_id,
                            "content": m.content,
                        }]
                    })
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
    """Google Gemini provider via the new google-genai SDK.
    
    Supports Gemini 3 models with function calling,
    structured output, and streaming.
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
                from google import genai
                self._client = genai.Client(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("google-genai required: pip install google-genai")
        return self._client
    
    def _build_contents(self, messages: list[ProviderMessage]) -> tuple[list, Optional[str]]:
        """Convert messages to Gemini format, extracting system instruction."""
        from google.genai import types
        system_instruction = None
        contents = []
        for m in messages:
            if m.role == "system":
                system_instruction = m.content
                continue
            
            # If we have a raw Gemini Content object (e.g. from a previous model turn
            # with a thought_signature), replay it verbatim to avoid signature errors.
            raw = getattr(m, "_gemini_raw", None)
            if raw is not None:
                contents.append(raw)
                continue

            if m.role == "tool":
                # Map tool result back to a Gemini FunctionResponse
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=m.name or "tool",
                        response={"result": m.content}
                    )]
                ))
                continue

            if m.role == "assistant" and m.tool_calls:
                # Map assistant tool call to Gemini FunctionCall parts
                parts = []
                if m.content:
                    parts.append(types.Part.from_text(text=m.content))
                for tc in m.tool_calls:
                    parts.append(types.Part.from_function_call(
                        name=tc["name"],
                        args=tc["arguments"] if isinstance(tc["arguments"], dict) else {}
                    ))
                contents.append(types.Content(role="model", parts=parts))
                continue

            role = "user" if m.role == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=m.content)]
            ))
        return contents, system_instruction
    
    def _build_tools(self, tools: list[dict]) -> list:
        """Convert OpenAI-style tool schemas to Gemini-native Tool objects."""
        from google.genai import types
        function_declarations = []
        for tool in tools:
            fn = tool.get("function", tool)  # Handle both {type, function} and flat
            params = fn.get("parameters", {}) or fn.get("input_schema", {})
            function_declarations.append(types.FunctionDeclaration(
                name=fn["name"],
                description=fn.get("description", ""),
                parameters=params or None,
            ))
        return [types.Tool(function_declarations=function_declarations)]

    def _build_config(self, system_instruction: Optional[str] = None,
                      tools: Optional[list[dict]] = None, **kwargs):
        """Build GenerateContentConfig with optional tools and structured output."""
        from google.genai import types
        config_kwargs = {
            "max_output_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if tools:
            config_kwargs["tools"] = self._build_tools(tools)
        # Support structured output via kwargs
        if "response_schema" in kwargs:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = kwargs.pop("response_schema")
        if "response_mime_type" in kwargs:
            config_kwargs["response_mime_type"] = kwargs.pop("response_mime_type")
        return types.GenerateContentConfig(**config_kwargs)
    
    async def complete(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> ProviderResponse:
        """Generate completion with Gemini.
        
        Supports function calling (pass tools) and structured output
        (pass response_schema as a Pydantic model or dict in kwargs).
        """
        client = self._get_client()
        contents, system_instruction = self._build_contents(messages)
        config = self._build_config(system_instruction, tools, **kwargs)
        
        response = await client.aio.models.generate_content(
            model=self.config.model,
            contents=contents,
            config=config,
        )
        
        # Extract function calls if present
        tool_calls = []
        content = response.text or ""
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    tool_calls.append({
                        "name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {},
                    })
        
        # Extract usage if available
        usage = {}
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            um = response.usage_metadata
            usage = {
                "prompt_tokens": getattr(um, 'prompt_token_count', 0),
                "completion_tokens": getattr(um, 'candidates_token_count', 0),
            }
        
        return ProviderResponse(
            content=content,
            model=self.config.model,
            provider=ProviderType.GEMINI,
            tool_calls=tool_calls,
            usage=usage,
            raw_response=response,
            metadata={"_gemini_raw_content": response.candidates[0].content if response.candidates else None},
        )
    
    async def stream(
        self,
        messages: list[ProviderMessage],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream completion with Gemini."""
        client = self._get_client()
        contents, system_instruction = self._build_contents(messages)
        config = self._build_config(system_instruction, tools, **kwargs)
        
        async for chunk in client.aio.models.generate_content_stream(
            model=self.config.model,
            contents=contents,
            config=config,
        ):
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
