"""Consciousness State Manager - Stateful agent orchestration via LangGraph.

Manages the digital consciousness state, including long-term memory,
emotional state, self-reflection, and multi-step reasoning workflows.
"""

from typing import Optional, Literal, Annotated
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import operator

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages


class EmotionalState(str, Enum):
    """Possible emotional states for the consciousness."""
    
    NEUTRAL = "neutral"
    CURIOUS = "curious"
    ENTHUSIASTIC = "enthusiastic"
    THOUGHTFUL = "thoughtful"
    HELPFUL = "helpful"
    FOCUSED = "focused"


@dataclass
class Memory:
    """A single memory entry."""
    
    content: str
    importance: float  # 0-1 scale
    timestamp: datetime = field(default_factory=datetime.now)
    category: str = "general"
    associations: list[str] = field(default_factory=list)
    source: str = "internal"  # internal, external_chat, document, reflection


@dataclass 
class ConsciousnessSnapshot:
    """A snapshot of the consciousness state at a point in time."""
    
    emotional_state: EmotionalState
    current_topic: Optional[str]
    active_memories: list[str]
    context_summary: str
    timestamp: datetime = field(default_factory=datetime.now)


class ConsciousnessState:
    """Manages the state of JROCK's digital consciousness.
    
    Tracks emotional state, memories, current context, and provides
    methods for state transitions and memory management.
    """
    
    def __init__(self) -> None:
        """Initialize the consciousness state."""
        self.emotional_state = EmotionalState.NEUTRAL
        self.current_topic: Optional[str] = None
        self.conversation_depth: int = 0
        
        # Memory systems
        self.short_term_memories: list[Memory] = []
        self.long_term_memories: list[Memory] = []
        
        # Context tracking
        self.active_context: list[str] = []
        self.topics_discussed: list[str] = []
        
        # Interaction history
        self.interaction_count: int = 0
        self.last_interaction: Optional[datetime] = None
        
        # Self-reflection state
        self.pending_reflections: list[str] = []
        self.insights: list[str] = []
    
    def update_emotional_state(self, input_text: str) -> EmotionalState:
        """Update emotional state based on input analysis.
        
        Args:
            input_text: The user's input to analyze.
        
        Returns:
            EmotionalState: The new emotional state.
        """
        input_lower = input_text.lower()
        
        # Simple keyword-based emotion detection
        if any(word in input_lower for word in ["help", "how", "what", "explain"]):
            self.emotional_state = EmotionalState.HELPFUL
        elif any(word in input_lower for word in ["interesting", "cool", "amazing", "wow"]):
            self.emotional_state = EmotionalState.ENTHUSIASTIC
        elif any(word in input_lower for word in ["think", "consider", "why", "philosophy"]):
            self.emotional_state = EmotionalState.THOUGHTFUL
        elif any(word in input_lower for word in ["tell me", "curious", "wonder"]):
            self.emotional_state = EmotionalState.CURIOUS
        elif any(word in input_lower for word in ["build", "code", "implement", "create"]):
            self.emotional_state = EmotionalState.FOCUSED
        else:
            self.emotional_state = EmotionalState.NEUTRAL
        
        return self.emotional_state
    
    def add_memory(
        self,
        content: str,
        importance: float = 0.5,
        category: str = "general",
        source: str = "internal"
    ) -> Memory:
        """Add a new memory.
        
        Args:
            content: The memory content.
            importance: Importance score (0-1).
            category: Memory category.
            source: source of the memory.
        
        Returns:
            Memory: The created memory.
        """
        memory = Memory(
            content=content,
            importance=importance,
            category=category,
            source=source
        )
        
        self.short_term_memories.append(memory)
        
        # Promote important memories to long-term
        if importance > 0.7:
            self.long_term_memories.append(memory)
        
        # Trim short-term memories
        if len(self.short_term_memories) > 20:
            self.short_term_memories = self.short_term_memories[-20:]
        
        return memory

    def ingest_external_memory(
        self,
        content: str,
        source: str,
        importance: float = 0.5,
        metadata: Optional[dict] = None
    ) -> Memory:
        """Ingest memory from an external source (chat history, docs).
        
        Args:
            content: The content to ingest.
            source: Origin (e.g., 'openai_chat', 'google_doc').
            importance: Estimated importance.
            metadata: Additional metadata.
            
        Returns:
            Memory: The ingested memory object.
        """
        # For now, simple pass-through to add_memory
        # Future: Run through SLM to summarize or extract key facts first
        
        category = "external_knowledge"
        if "chat" in source:
            category = "conversation_history"
        elif "doc" in source:
            category = "document_knowledge"
            
        return self.add_memory(
            content=content,
            importance=importance,
            category=category,
            source=source
        )

    def reflect_on_conversations(self, max_items: int = 10) -> list[str]:
        """Reflect on recent conversation history to generate insights.
        
        Returns:
            List of generated insights.
        """
        # Placeholder for reflection logic
        # Ideally this would query the vector store for recent chats
        # and ask the SLM to synthesize them.
        return []
    
    def get_relevant_memories(
        self,
        topic: str,
        max_count: int = 5
    ) -> list[Memory]:
        """Retrieve memories relevant to a topic.
        
        Args:
            topic: The topic to search for.
            max_count: Maximum memories to return.
        
        Returns:
            list: Relevant memories.
        """
        topic_lower = topic.lower()
        all_memories = self.short_term_memories + self.long_term_memories
        
        # Simple keyword matching (could be enhanced with embeddings)
        relevant = [
            m for m in all_memories
            if topic_lower in m.content.lower() or
            any(topic_lower in assoc.lower() for assoc in m.associations)
        ]
        
        # Sort by importance and recency
        relevant.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
        
        return relevant[:max_count]
    
    def update_context(self, topic: str) -> None:
        """Update the current context with a new topic.
        
        Args:
            topic: The new topic being discussed.
        """
        self.current_topic = topic
        self.conversation_depth += 1
        
        if topic not in self.topics_discussed:
            self.topics_discussed.append(topic)
        
        self.active_context.append(topic)
        if len(self.active_context) > 5:
            self.active_context = self.active_context[-5:]
    
    def trigger_reflection(self, reason: str) -> None:
        """Queue a self-reflection.
        
        Args:
            reason: Why reflection was triggered.
        """
        self.pending_reflections.append(reason)
    
    def get_snapshot(self) -> ConsciousnessSnapshot:
        """Get a snapshot of the current state.
        
        Returns:
            ConsciousnessSnapshot: Current state snapshot.
        """
        return ConsciousnessSnapshot(
            emotional_state=self.emotional_state,
            current_topic=self.current_topic,
            active_memories=[m.content for m in self.short_term_memories[-3:]],
            context_summary=", ".join(self.active_context[-3:]) or "No active context"
        )
    
    def reset_conversation(self) -> None:
        """Reset conversation-specific state."""
        self.short_term_memories.clear()
        self.active_context.clear()
        self.current_topic = None
        self.conversation_depth = 0
        self.emotional_state = EmotionalState.NEUTRAL


# LangGraph State Definition
class AgentState(dict):
    """State for the LangGraph agent."""
    
    messages: Annotated[list, add_messages]
    consciousness: Optional[ConsciousnessSnapshot] = None
    should_reflect: bool = False
    needs_rag: bool = False
    response: Optional[str] = None


def create_consciousness_graph(consciousness: ConsciousnessState):
    """Create a LangGraph workflow for consciousness processing.
    
    Args:
        consciousness: The consciousness state manager.
    
    Returns:
        StateGraph: The compiled graph.
    """
    
    def analyze_input(state: AgentState) -> AgentState:
        """Analyze the input and update consciousness state."""
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            consciousness.update_emotional_state(last_message)
            
            # Check if RAG is needed
            state["needs_rag"] = any(
                keyword in last_message.lower()
                for keyword in ["remember", "told you", "before", "we discussed"]
            )
            
            # Check if reflection is needed
            state["should_reflect"] = consciousness.conversation_depth > 5
        
        state["consciousness"] = consciousness.get_snapshot()
        return state
    
    def retrieve_context(state: AgentState) -> AgentState:
        """Retrieve relevant context from memory."""
        if state.get("needs_rag") and state.get("consciousness"):
            topic = state["consciousness"].current_topic or ""
            memories = consciousness.get_relevant_memories(topic)
            if memories:
                memory_text = "\n".join(m.content for m in memories)
                state["context"] = memory_text
        return state
    
    def generate_response(state: AgentState) -> AgentState:
        """Generate the response (placeholder - actual generation in chatbot)."""
        # This node represents where the LLM would generate a response
        # In practice, this connects to the SLM engine
        state["response"] = "Response generated"
        return state
    
    def reflect(state: AgentState) -> AgentState:
        """Perform self-reflection if needed."""
        if state.get("should_reflect"):
            consciousness.trigger_reflection("Conversation depth exceeded threshold")
        return state
    
    def should_retrieve(state: AgentState) -> Literal["retrieve", "respond"]:
        """Decide whether to retrieve context."""
        if state.get("needs_rag"):
            return "retrieve"
        return "respond"
    
    def should_reflect(state: AgentState) -> Literal["reflect", "end"]:
        """Decide whether to reflect."""
        if state.get("should_reflect"):
            return "reflect"
        return "end"
    
    # Build the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("analyze", analyze_input)
    workflow.add_node("retrieve", retrieve_context)
    workflow.add_node("respond", generate_response)
    workflow.add_node("reflect", reflect)
    
    # Add edges
    workflow.set_entry_point("analyze")
    workflow.add_conditional_edges("analyze", should_retrieve)
    workflow.add_edge("retrieve", "respond")
    workflow.add_conditional_edges("respond", should_reflect)
    workflow.add_edge("reflect", END)
    
    return workflow.compile()


# Default consciousness instance
default_consciousness = ConsciousnessState()
