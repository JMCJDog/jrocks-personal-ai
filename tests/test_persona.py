"""Tests for the Persona module."""

import pytest
from app.core.persona import (
    JROCKPersona,
    PersonaTrait,
    WritingStyle,
    KnowledgeDomain,
    default_persona,
    get_system_prompt,
)


class TestPersonaTrait:
    """Tests for PersonaTrait dataclass."""
    
    def test_trait_creation(self):
        """Test creating a personality trait."""
        trait = PersonaTrait(
            name="Creative",
            description="Thinks outside the box",
            examples=["What if we...", "Let's try..."],
            weight=1.5
        )
        
        assert trait.name == "Creative"
        assert trait.weight == 1.5
        assert len(trait.examples) == 2


class TestJROCKPersona:
    """Tests for JROCKPersona class."""
    
    def test_init(self):
        """Test persona initialization."""
        persona = JROCKPersona()
        
        assert persona.name == "JROCK"
        assert len(persona.traits) > 0
        assert len(persona.knowledge_domains) > 0
    
    def test_add_trait(self):
        """Test adding a new trait."""
        persona = JROCKPersona()
        initial_count = len(persona.traits)
        
        new_trait = PersonaTrait(
            name="Adventurous",
            description="Loves trying new things"
        )
        persona.add_trait(new_trait)
        
        assert len(persona.traits) == initial_count + 1
    
    def test_add_knowledge_domain(self):
        """Test adding a knowledge domain."""
        persona = JROCKPersona()
        initial_count = len(persona.knowledge_domains)
        
        domain = KnowledgeDomain(
            name="Music",
            expertise_level="intermediate",
            topics=["Guitar", "Production"]
        )
        persona.add_knowledge_domain(domain)
        
        assert len(persona.knowledge_domains) == initial_count + 1
    
    def test_generate_system_prompt(self):
        """Test system prompt generation."""
        persona = JROCKPersona()
        prompt = persona.generate_system_prompt()
        
        assert "JROCK" in prompt
        assert "personality" in prompt.lower() or "traits" in prompt.lower()
        assert len(prompt) > 100  # Should be substantial
    
    def test_generate_system_prompt_with_context(self):
        """Test system prompt with additional context."""
        persona = JROCKPersona()
        prompt = persona.generate_system_prompt(context="Focus on AI topics")
        
        assert "Focus on AI topics" in prompt
    
    def test_get_brief_intro(self):
        """Test getting brief introduction."""
        persona = JROCKPersona()
        intro = persona.get_brief_intro()
        
        assert "JROCK" in intro or persona.name in intro
        assert len(intro) < 500  # Should be brief


class TestDefaultPersona:
    """Tests for default persona instance."""
    
    def test_default_persona_exists(self):
        """Test that default persona is available."""
        assert default_persona is not None
        assert isinstance(default_persona, JROCKPersona)
    
    def test_get_system_prompt_function(self):
        """Test convenience function for system prompt."""
        prompt = get_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
