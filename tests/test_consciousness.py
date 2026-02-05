"""Tests for the Consciousness module."""

import pytest
from app.core.consciousness import (
    ConsciousnessState,
    EmotionalState,
    Memory,
    ConsciousnessSnapshot,
)


class TestEmotionalState:
    """Tests for EmotionalState enum."""
    
    def test_emotional_states_exist(self):
        """Test that all expected emotional states exist."""
        assert EmotionalState.NEUTRAL.value == "neutral"
        assert EmotionalState.CURIOUS.value == "curious"
        assert EmotionalState.ENTHUSIASTIC.value == "enthusiastic"


class TestMemory:
    """Tests for Memory dataclass."""
    
    def test_memory_creation(self):
        """Test creating a memory entry."""
        memory = Memory(
            content="User asked about Python",
            importance=0.8,
            category="conversation"
        )
        
        assert memory.content == "User asked about Python"
        assert memory.importance == 0.8
        assert memory.timestamp is not None


class TestConsciousnessState:
    """Tests for ConsciousnessState class."""
    
    def test_init(self):
        """Test consciousness initialization."""
        consciousness = ConsciousnessState()
        
        assert consciousness.emotional_state == EmotionalState.NEUTRAL
        assert consciousness.current_topic is None
        assert len(consciousness.short_term_memories) == 0
    
    def test_update_emotional_state_helpful(self):
        """Test updating emotional state to helpful."""
        consciousness = ConsciousnessState()
        
        state = consciousness.update_emotional_state("Can you help me?")
        
        assert state == EmotionalState.HELPFUL
    
    def test_update_emotional_state_curious(self):
        """Test updating emotional state to curious."""
        consciousness = ConsciousnessState()
        
        state = consciousness.update_emotional_state("I'm curious about AI")
        
        assert state == EmotionalState.CURIOUS
    
    def test_update_emotional_state_focused(self):
        """Test updating emotional state to focused."""
        consciousness = ConsciousnessState()
        
        state = consciousness.update_emotional_state("Let's build a project")
        
        assert state == EmotionalState.FOCUSED
    
    def test_add_memory(self):
        """Test adding a memory."""
        consciousness = ConsciousnessState()
        
        memory = consciousness.add_memory(
            content="Test memory",
            importance=0.5
        )
        
        assert len(consciousness.short_term_memories) == 1
        assert memory.content == "Test memory"
    
    def test_important_memory_promoted(self):
        """Test that important memories go to long-term."""
        consciousness = ConsciousnessState()
        
        consciousness.add_memory("Important!", importance=0.9)
        
        assert len(consciousness.long_term_memories) == 1
    
    def test_memory_trimming(self):
        """Test that short-term memories are trimmed."""
        consciousness = ConsciousnessState()
        
        # Add more than 20 memories
        for i in range(25):
            consciousness.add_memory(f"Memory {i}", importance=0.3)
        
        assert len(consciousness.short_term_memories) <= 20
    
    def test_get_relevant_memories(self):
        """Test retrieving relevant memories."""
        consciousness = ConsciousnessState()
        consciousness.add_memory("Python programming tips")
        consciousness.add_memory("JavaScript basics")
        
        relevant = consciousness.get_relevant_memories("Python")
        
        assert len(relevant) >= 1
        assert "Python" in relevant[0].content
    
    def test_update_context(self):
        """Test updating context."""
        consciousness = ConsciousnessState()
        
        consciousness.update_context("AI Development")
        
        assert consciousness.current_topic == "AI Development"
        assert consciousness.conversation_depth == 1
        assert "AI Development" in consciousness.topics_discussed
    
    def test_trigger_reflection(self):
        """Test triggering self-reflection."""
        consciousness = ConsciousnessState()
        
        consciousness.trigger_reflection("Deep conversation")
        
        assert len(consciousness.pending_reflections) == 1
    
    def test_get_snapshot(self):
        """Test getting state snapshot."""
        consciousness = ConsciousnessState()
        consciousness.update_emotional_state("exciting!")
        consciousness.update_context("Test topic")
        
        snapshot = consciousness.get_snapshot()
        
        assert isinstance(snapshot, ConsciousnessSnapshot)
        assert snapshot.current_topic == "Test topic"
    
    def test_reset_conversation(self):
        """Test resetting conversation state."""
        consciousness = ConsciousnessState()
        consciousness.add_memory("Test")
        consciousness.update_context("Topic")
        
        consciousness.reset_conversation()
        
        assert len(consciousness.short_term_memories) == 0
        assert consciousness.current_topic is None
        assert consciousness.emotional_state == EmotionalState.NEUTRAL
