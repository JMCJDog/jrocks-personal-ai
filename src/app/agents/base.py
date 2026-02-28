"""Base Agent - Foundation for all specialized agents.

Defines the common interface, configuration, and response types
that all agents in the system inherit from.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentCapability(str, Enum):
    """Capabilities that agents can have."""
    
    WEB_SEARCH = "web_search"
    RAG_RETRIEVAL = "rag_retrieval"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    CONTENT_WRITING = "content_writing"
    MEMORY_MANAGEMENT = "memory_management"
    IMAGE_GENERATION = "image_generation"
    API_INTEGRATION = "api_integration"
    FILE_OPERATIONS = "file_operations"
    CONVERSATION = "conversation"
    FINANCIAL_ANALYSIS = "financial_analysis"
    VALUATION = "valuation"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    
    name: str
    description: str
    model_name: str = "llama3.2"
    temperature: float = 0.7
    max_tokens: int = 2048
    capabilities: list[AgentCapability] = field(default_factory=list)
    system_prompt: str = ""
    tools: list[Callable] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Response from an agent."""
    
    agent_name: str
    content: str
    success: bool = True
    confidence: float = 1.0
    reasoning: Optional[str] = None
    tool_calls: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "agent": self.agent_name,
            "content": self.content,
            "success": self.success,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class InterAgentMessage:
    """A message between agents for coordination."""
    
    sender: str
    recipient: str
    content: str
    message_type: str = "request"  # request, response, notification
    context: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None


@dataclass
class AgentMessage:
    """A message in the agent conversation."""
    
    role: str  # "user", "assistant", "system", "tool"
    content: str
    agent_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    sender: Optional[str] = None  # For inter-agent messages
    recipient: Optional[str] = None  # For inter-agent messages
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all agents.
    
    Provides common functionality for agent initialization,
    message handling, and response generation.
    
    Example:
        >>> class MyAgent(BaseAgent):
        ...     def process(self, message, context):
        ...         return AgentResponse(...)
    """
    
    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the agent.
        
        Args:
            config: Agent configuration. Uses defaults if not provided.
        """
        self.config = config or self._default_config()
        self._history: list[AgentMessage] = []
        self._llm = None
    
    @abstractmethod
    def _default_config(self) -> AgentConfig:
        """Return the default configuration for this agent.
        
        Returns:
            AgentConfig: Default configuration.
        """
        pass
    
    @abstractmethod
    def process(
        self,
        message: str,
        context: Optional[dict] = None
    ) -> AgentResponse:
        """Process a message and generate a response.
        
        Args:
            message: The input message to process.
            context: Optional context from other agents or system.
        
        Returns:
            AgentResponse: The agent's response.
        """
        pass
    
    @property
    def name(self) -> str:
        """Get the agent's name."""
        return self.config.name
    
    @property
    def capabilities(self) -> list[AgentCapability]:
        """Get the agent's capabilities."""
        return self.config.capabilities
    
    def can_handle(self, capability: AgentCapability) -> bool:
        """Check if the agent has a specific capability.
        
        Args:
            capability: The capability to check.
        
        Returns:
            bool: True if the agent has this capability.
        """
        return capability in self.capabilities
    
    def add_to_history(self, message: AgentMessage) -> None:
        """Add a message to the agent's history.
        
        Args:
            message: The message to add.
        """
        self._history.append(message)
    
    def get_history(self, max_messages: int = 20) -> list[AgentMessage]:
        """Get recent message history.
        
        Args:
            max_messages: Maximum messages to return.
        
        Returns:
            list: Recent messages.
        """
        return self._history[-max_messages:]
    
    def clear_history(self) -> None:
        """Clear the agent's message history."""
        self._history.clear()
    
    def get_system_prompt(self) -> str:
        """Get the agent's system prompt.
        
        Returns:
            str: The system prompt.
        """
        return self.config.system_prompt or self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build a default system prompt.
        
        Returns:
            str: Generated system prompt.
        """
        caps = ", ".join(c.value for c in self.capabilities)
        return f"""You are {self.config.name}, a specialized AI agent.

## Description
{self.config.description}

## Capabilities
{caps}

## Guidelines
- Focus on your specialized domain
- Be concise and accurate
- Indicate when a task is outside your expertise
- Collaborate with other agents when needed
"""
    
    def _call_llm(self, messages: list[dict]) -> str:
        """Call the LLM and get a response.
        
        Args:
            messages: List of message dicts for the LLM.
        
        Returns:
            str: The LLM response.
        """
        try:
            import ollama
            
            if self._llm is None:
                self._llm = ollama.Client()
            
            response = self._llm.chat(
                model=self.config.model_name,
                messages=messages,
                options={
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                }
            )
            return response["message"]["content"]
            
        except Exception as e:
            return f"Error calling LLM: {str(e)}"
    
    def get_capabilities_schema(self) -> dict:
        """Get a JSON schema describing the agent's capabilities.
        
        Returns:
            dict: Schema with name, description, and capabilities.
        """
        return {
            "name": self.name,
            "description": self.config.description,
            "capabilities": [c.value for c in self.capabilities],
            "model": self.config.model_name,
        }
    
    async def receive_message(self, message: InterAgentMessage) -> AgentResponse:
        """Receive a message from another agent.
        
        Args:
            message: The inter-agent message.
        
        Returns:
            AgentResponse: Response to the sender.
        """
        # Process the message content
        context = message.context.copy()
        context["from_agent"] = message.sender
        context["message_type"] = message.message_type
        
        return self.process(message.content, context)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"

