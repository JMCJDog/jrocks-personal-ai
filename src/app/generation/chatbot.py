"""Chatbot - Interactive conversation interface for JROCK's AI.

Provides a high-level interface for chat interactions that combines
the SLM engine with persona, RAG context, and conversation state.
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..core.slm_engine import SLMEngine, ModelConfig
from ..core.persona import JROCKPersona, default_persona
from ..ingest.embedding_pipeline import EmbeddingPipeline


@dataclass
class ChatMessage:
    """A single chat message."""
    
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatSession:
    """A chat session with history."""
    
    session_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def add_message(self, role: str, content: str) -> ChatMessage:
        """Add a message to the session.
        
        Args:
            role: The message role ("user" or "assistant").
            content: The message content.
        
        Returns:
            ChatMessage: The created message.
        """
        msg = ChatMessage(role=role, content=content)
        self.messages.append(msg)
        return msg
    
    def get_history(self, max_messages: int = 20) -> list[dict]:
        """Get conversation history in API format.
        
        Args:
            max_messages: Maximum messages to return.
        
        Returns:
            list: List of message dictionaries.
        """
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [{"role": m.role, "content": m.content} for m in recent]


class Chatbot:
    """JROCK's AI Chatbot with persona and RAG integration.
    
    Combines the SLM engine with persona definition and optional
    RAG context retrieval for informed, personalized responses.
    
    Example:
        >>> bot = Chatbot()
        >>> response = bot.chat("What are you working on?")
        >>> print(response)
    """
    
    def __init__(
        self,
        persona: Optional[JROCKPersona] = None,
        model_name: str = "llama3.2",
        use_rag: bool = True,
        embedding_pipeline: Optional[EmbeddingPipeline] = None,
    ) -> None:
        """Initialize the chatbot.
        
        Args:
            persona: The persona to use. Defaults to JROCK persona.
            model_name: The Ollama model to use.
            use_rag: Whether to use RAG for context enhancement.
            embedding_pipeline: Optional embedding pipeline for RAG.
        """
        self.persona = persona or default_persona
        self.use_rag = use_rag
        self._embedding_pipeline = embedding_pipeline
        
        # Initialize the SLM engine with persona
        config = ModelConfig(
            model_name=model_name,
            system_prompt=self.persona.generate_system_prompt(),
            temperature=0.7,
        )
        self.engine = SLMEngine(config)
        
        # Session management
        self._sessions: dict[str, ChatSession] = {}
        self._current_session: Optional[ChatSession] = None
    
    @property
    def embedding_pipeline(self) -> Optional[EmbeddingPipeline]:
        """Lazy-load embedding pipeline if RAG is enabled."""
        if self.use_rag and self._embedding_pipeline is None:
            try:
                self._embedding_pipeline = EmbeddingPipeline()
            except Exception:
                self.use_rag = False
        return self._embedding_pipeline
    
    def create_session(self, session_id: Optional[str] = None) -> ChatSession:
        """Create a new chat session.
        
        Args:
            session_id: Optional session ID. Generated if not provided.
        
        Returns:
            ChatSession: The new session.
        """
        import uuid
        sid = session_id or str(uuid.uuid4())
        session = ChatSession(session_id=sid)
        self._sessions[sid] = session
        self._current_session = session
        
        # Reset engine conversation
        self.engine.reset_conversation()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID.
        
        Args:
            session_id: The session ID.
        
        Returns:
            ChatSession or None: The session if found.
        """
        return self._sessions.get(session_id)
    
    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        include_context: bool = True,
    ) -> str:
        """Send a message and get a response.
        
        Args:
            message: The user's message.
            session_id: Optional session ID to continue a conversation.
            include_context: Whether to include RAG context.
        
        Returns:
            str: The assistant's response.
        """
        # Get or create session
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
        elif self._current_session:
            session = self._current_session
        else:
            session = self.create_session()
        
        # Retrieve context if RAG is enabled
        context_text = ""
        if include_context and self.use_rag and self.embedding_pipeline:
            try:
                results = self.embedding_pipeline.search(message, n_results=3)
                if results:
                    context_parts = [r["content"] for r in results]
                    context_text = "\n\n---\n\n".join(context_parts)
            except Exception:
                pass  # Continue without context if search fails
        
        # Enhance message with context if available
        enhanced_message = message
        if context_text:
            enhanced_message = (
                f"[Context from my knowledge base:\n{context_text}\n]\n\n"
                f"User: {message}"
            )
        
        # Add user message to session
        session.add_message("user", message)
        
        # Generate response
        response = self.engine.generate(enhanced_message)
        
        # Add response to session
        session.add_message("assistant", response)
        
        return response
    
    def get_intro(self) -> str:
        """Get an introduction message from the persona.
        
        Returns:
            str: An introduction message.
        """
        return self.persona.get_brief_intro()
    
    def reset(self) -> None:
        """Reset the current conversation."""
        self.engine.reset_conversation()
        if self._current_session:
            self._current_session.messages.clear()


# Convenience function for quick chat
def quick_chat(message: str, model: str = "llama3.2") -> str:
    """Quick one-off chat without session management.
    
    Args:
        message: The message to send.
        model: The model to use.
    
    Returns:
        str: The response.
    """
    bot = Chatbot(model_name=model, use_rag=False)
    return bot.chat(message)
