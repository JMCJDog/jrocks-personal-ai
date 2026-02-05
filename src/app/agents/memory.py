"""Memory Agent - Specialized for knowledge management.

Handles storing, retrieving, and organizing knowledge and memories
for the personal AI system.
"""

from typing import Optional
from datetime import datetime
from .base import BaseAgent, AgentConfig, AgentResponse, AgentCapability, AgentMessage


class MemoryAgent(BaseAgent):
    """Agent specialized for memory and knowledge management.
    
    Capabilities:
    - Storing new information
    - Retrieving relevant memories
    - Organizing knowledge
    - Maintaining context across conversations
    
    Example:
        >>> agent = MemoryAgent()
        >>> response = agent.process("Remember that my favorite color is blue")
    """
    
    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the Memory Agent."""
        super().__init__(config)
        self._embedding_pipeline = None
        self._consciousness = None
    
    def _default_config(self) -> AgentConfig:
        """Return default configuration."""
        return AgentConfig(
            name="Memory Agent",
            description="Specializes in managing the knowledge base, storing memories, "
                       "and maintaining context across conversations.",
            model_name="llama3.2",
            temperature=0.4,
            capabilities=[
                AgentCapability.MEMORY_MANAGEMENT,
                AgentCapability.RAG_RETRIEVAL,
            ],
            system_prompt="""You are a Memory Agent specialized in knowledge management.

## Your Expertise
- Storing and organizing information
- Retrieving relevant memories and context
- Maintaining long-term knowledge
- Identifying important information to remember

## Guidelines
1. Distinguish between facts and preferences
2. Organize memories by topic and importance
3. Update existing knowledge when corrections are made
4. Flag conflicting information for clarification
"""
        )
    
    def _get_embedding_pipeline(self):
        """Lazy load the embedding pipeline."""
        if self._embedding_pipeline is None:
            try:
                from ..ingest.embedding_pipeline import EmbeddingPipeline
                self._embedding_pipeline = EmbeddingPipeline()
            except Exception:
                pass
        return self._embedding_pipeline
    
    def _get_consciousness(self):
        """Lazy load the consciousness module."""
        if self._consciousness is None:
            try:
                from ..core.consciousness import ConsciousnessState
                self._consciousness = ConsciousnessState()
            except Exception:
                pass
        return self._consciousness
    
    def process(
        self,
        message: str,
        context: Optional[dict] = None
    ) -> AgentResponse:
        """Process a memory-related request.
        
        Args:
            message: The memory request.
            context: Optional context (action type, importance, etc.).
        
        Returns:
            AgentResponse: Memory operation result.
        """
        context = context or {}
        action = context.get("action", "auto")  # store, retrieve, auto
        
        self.add_to_history(AgentMessage(role="user", content=message))
        
        # Determine action type
        if action == "auto":
            action = self._detect_action(message)
        
        if action == "store":
            result = self._store_memory(message, context)
        elif action == "retrieve":
            result = self._retrieve_memories(message, context)
        else:
            result = self._process_memory_query(message)
        
        return result
    
    def _detect_action(self, message: str) -> str:
        """Detect whether to store or retrieve.
        
        Args:
            message: The input message.
        
        Returns:
            str: "store" or "retrieve"
        """
        store_keywords = ["remember", "store", "save", "note", "add to memory"]
        retrieve_keywords = ["recall", "what was", "what is", "do you remember", "find"]
        
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in store_keywords):
            return "store"
        if any(kw in message_lower for kw in retrieve_keywords):
            return "retrieve"
        
        return "retrieve"  # Default to retrieve
    
    def _store_memory(
        self,
        message: str,
        context: dict
    ) -> AgentResponse:
        """Store a new memory.
        
        Args:
            message: The information to store.
            context: Storage context.
        
        Returns:
            AgentResponse: Storage result.
        """
        importance = context.get("importance", 0.5)
        category = context.get("category", "general")
        
        # Store in consciousness if available
        consciousness = self._get_consciousness()
        if consciousness:
            consciousness.add_memory(
                content=message,
                importance=importance,
                category=category
            )
        
        # Store in vector database
        pipeline = self._get_embedding_pipeline()
        if pipeline:
            try:
                pipeline.add_text(
                    text=message,
                    metadata={
                        "type": "memory",
                        "category": category,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                stored = True
            except Exception:
                stored = False
        else:
            stored = False
        
        response_text = f"Memory stored: {message[:100]}..." if stored else "Failed to store memory"
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            success=stored,
            confidence=0.9 if stored else 0.3,
            reasoning="Stored in knowledge base" if stored else "Storage failed",
            metadata={"action": "store", "stored": stored}
        )
    
    def _retrieve_memories(
        self,
        query: str,
        context: dict
    ) -> AgentResponse:
        """Retrieve relevant memories.
        
        Args:
            query: Search query.
            context: Retrieval context.
        
        Returns:
            AgentResponse: Retrieved memories.
        """
        n_results = context.get("n_results", 5)
        
        pipeline = self._get_embedding_pipeline()
        if not pipeline:
            return AgentResponse(
                agent_name=self.name,
                content="Memory system not available",
                success=False,
                confidence=0.0,
            )
        
        try:
            results = pipeline.search(query, n_results=n_results)
            
            if results:
                memories = [r["content"] for r in results]
                response_text = "Found these relevant memories:\n\n"
                for i, mem in enumerate(memories, 1):
                    response_text += f"{i}. {mem}\n"
            else:
                response_text = "No relevant memories found."
            
            return AgentResponse(
                agent_name=self.name,
                content=response_text,
                success=True,
                confidence=0.8 if results else 0.4,
                reasoning=f"Retrieved {len(results)} memories",
                metadata={"action": "retrieve", "count": len(results)}
            )
            
        except Exception as e:
            return AgentResponse(
                agent_name=self.name,
                content=f"Error retrieving memories: {str(e)}",
                success=False,
                confidence=0.0,
            )
    
    def _process_memory_query(self, message: str) -> AgentResponse:
        """Process a general memory query using LLM.
        
        Args:
            message: The query.
        
        Returns:
            AgentResponse: LLM-generated response.
        """
        # Get relevant memories first
        memories = []
        pipeline = self._get_embedding_pipeline()
        if pipeline:
            try:
                results = pipeline.search(message, n_results=3)
                memories = [r["content"] for r in results]
            except Exception:
                pass
        
        memory_context = ""
        if memories:
            memory_context = "\n\nRelevant memories:\n" + "\n".join(f"- {m}" for m in memories)
        
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"{message}{memory_context}"}
        ]
        
        response_text = self._call_llm(messages)
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            success=True,
            confidence=0.7,
            reasoning="Memory query processed",
            metadata={"memories_used": len(memories)}
        )
    
    def remember(self, content: str, importance: float = 0.5) -> bool:
        """Store a memory.
        
        Args:
            content: Content to remember.
            importance: Importance score (0-1).
        
        Returns:
            bool: Whether storage succeeded.
        """
        response = self.process(
            content,
            {"action": "store", "importance": importance}
        )
        return response.success
    
    def recall(self, query: str, n_results: int = 5) -> list[str]:
        """Recall memories matching a query.
        
        Args:
            query: Search query.
            n_results: Number of results.
        
        Returns:
            list: Retrieved memory contents.
        """
        pipeline = self._get_embedding_pipeline()
        if not pipeline:
            return []
        
        try:
            results = pipeline.search(query, n_results=n_results)
            return [r["content"] for r in results]
        except Exception:
            return []
