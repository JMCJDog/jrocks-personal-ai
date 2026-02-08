"""Chatbot - Interactive conversation interface for JROCK's AI.

Provides a high-level interface for chat interactions that combines
the SLM engine with persona, RAG context, and conversation state.
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..core.slm_engine import SLMEngine, ModelConfig
from ..core.persona import JROCKPersona, default_persona
from ..rag.engine import RAGEngine
from ..memory.manager import MemoryManager


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

    ) -> None:
        """Initialize the chatbot.
        
        Args:
            persona: The persona to use. Defaults to JROCK persona.
            model_name: The Ollama model to use.
            use_rag: Whether to use RAG for context enhancement.
        """
        self.persona = persona or default_persona
        self.use_rag = use_rag
        self._embedding_pipeline = None
        
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
        
        # Persistent memory
        self.memory_manager = MemoryManager()
    
        self._rag_engine: Optional[RAGEngine] = None
        
    @property
    def rag_engine(self) -> RAGEngine:
        """Lazy-load RAG engine."""
        if self._rag_engine is None:
            self._rag_engine = RAGEngine(slm_engine=self.engine)
        return self._rag_engine
    
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
        
        # Persist session
        self.memory_manager.create_session(sid)
        
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
        if session_id in self._sessions:
            return self._sessions[session_id]
            
        # Try to load from memory
        history = self.memory_manager.get_session_history(session_id, limit=100)
        if history:
            # Reconstruct session
            session = ChatSession(session_id=session_id)
            for msg_data in history:
                session.add_message(msg_data['role'], msg_data['content'])
            
            self._sessions[session_id] = session
            return session
            
        return None
    
    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        include_context: bool = True,
        images: Optional[list[str]] = None,
        context: Optional[dict] = None,
    ) -> str:
        """Send a message and get a response.
        
        Args:
            message: The user's message.
            session_id: Optional session ID to continue a conversation.
            include_context: Whether to include RAG context.
            images: Optional list of base64 encoded images.
            context: Optional context dictionary (e.g. for agent routing).
        
        Returns:
            str: The assistant's response.
        """
        import base64
        import re
        from pathlib import Path
        from ..utils.video import VideoProcessor
        
        # Check for video summarization trigger: "summarize video: [path]"
        video_match = re.search(r"summarize video:?\s*(.*)", message, re.IGNORECASE)
        if video_match and not images:
            video_path = video_match.group(1).strip().strip('"').strip("'")
            if video_path and Path(video_path).exists():
                print(f"Detecting video summarization request for: {video_path}")
                frames = VideoProcessor.extract_keyframes(video_path, num_frames=6)
                if frames:
                    images = frames
                    message = f"I have extracted 6 keyframes from the video at {video_path}. Please summarize what happens in this video based on these visuals."
        
        # Get or create session
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
        elif self._current_session:
            session = self._current_session
        else:
            session = self.create_session()
        
        # Decode images if provided
        image_bytes_list = None
        if images:
            image_bytes_list = []
            for img_b64 in images:
                try:
                    if "," in img_b64:
                        img_b64 = img_b64.split(",")[1]
                    image_bytes_list.append(base64.b64decode(img_b64))
                except Exception as e:
                    print(f"Error decoding image: {e}")

        # Add user message to session
        # Note: ChatMessage currently doesn't store images in memory, 
        # but we could add it if needed for persistence.
        session.add_message("user", message)
        self.memory_manager.add_message(session.session_id, "user", message)
        
        # Check for agent routing
        if context and context.get("target_agent"):
            try:
                from ..agents.supervisor import AgentOrchestrator
                orchestrator = AgentOrchestrator()
                result = orchestrator.run(message, context)
                response = result.content
                
                # Add response to session
                session.add_message("assistant", response)
                self.memory_manager.add_message(session.session_id, "assistant", response)
                return response
            except Exception as e:
                print(f"Agent orchestration failed: {e}")
                # Fallback to normal generation
        
        # Generate response using RAG Engine if enabled, otherwise raw SLM
        if self.use_rag:
            # RAGEngine might need an update to handle images as well, 
            # but for now it passes extra kwargs to the engine
            try:
                # Assuming RAGEngine.generate_response can pass through images or we call engine directly
                # Let's check RAGEngine first if possible, or just call engine.generate
                # If images are present, we might want to skip RAG or combine them
                response = self.rag_engine.generate_response(
                    message, 
                    enhance_context=include_context,
                    images=image_bytes_list,
                    context=context
                )
            except TypeError:
                # Fallback if RAGEngine doesn't support images yet
                response = self.engine.generate(message, images=image_bytes_list, context=context)
        else:
            response = self.engine.generate(message, images=image_bytes_list, context=context)
        
        # Add response to session
        session.add_message("assistant", response)
        self.memory_manager.add_message(session.session_id, "assistant", response)
        
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
