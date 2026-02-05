"""Tests for the SLM Engine module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.core.slm_engine import (
    SLMEngine,
    ModelConfig,
    Message,
    ConversationContext,
    quick_generate,
)


class TestModelConfig:
    """Tests for ModelConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ModelConfig()
        
        assert config.model_name == "llama3.2"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.system_prompt == ""
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ModelConfig(
            model_name="mistral",
            temperature=0.5,
            max_tokens=1024,
            system_prompt="You are helpful."
        )
        
        assert config.model_name == "mistral"
        assert config.temperature == 0.5
        assert config.system_prompt == "You are helpful."


class TestConversationContext:
    """Tests for ConversationContext class."""
    
    def test_add_message(self):
        """Test adding messages to context."""
        context = ConversationContext()
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi there!")
        
        assert len(context.messages) == 2
        assert context.messages[0].role == "user"
        assert context.messages[1].content == "Hi there!"
    
    def test_get_messages_for_api(self):
        """Test converting messages to API format."""
        context = ConversationContext()
        context.add_message("user", "Test message")
        
        api_messages = context.get_messages_for_api()
        
        assert len(api_messages) == 1
        assert api_messages[0] == {"role": "user", "content": "Test message"}
    
    def test_history_trimming(self):
        """Test that history is trimmed when exceeding max_history."""
        context = ConversationContext(max_history=5)
        
        # Add system message
        context.add_message("system", "System prompt")
        
        # Add more messages than max
        for i in range(10):
            context.add_message("user", f"Message {i}")
        
        # Should keep system message + recent messages
        assert len(context.messages) <= 5
        assert context.messages[0].role == "system"
    
    def test_clear(self):
        """Test clearing conversation except system messages."""
        context = ConversationContext()
        context.add_message("system", "System prompt")
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi")
        
        context.clear()
        
        assert len(context.messages) == 1
        assert context.messages[0].role == "system"


class TestSLMEngine:
    """Tests for SLMEngine class."""
    
    @patch('app.core.slm_engine.ollama')
    def test_init_with_system_prompt(self, mock_ollama):
        """Test initialization with system prompt."""
        config = ModelConfig(system_prompt="You are JROCK")
        engine = SLMEngine(config)
        
        assert len(engine.context.messages) == 1
        assert engine.context.messages[0].role == "system"
        assert "JROCK" in engine.context.messages[0].content
    
    @patch('app.core.slm_engine.ollama')
    def test_set_system_prompt(self, mock_ollama):
        """Test setting system prompt after init."""
        engine = SLMEngine()
        engine.set_system_prompt("New system prompt")
        
        assert len(engine.context.messages) == 1
        assert engine.context.messages[0].content == "New system prompt"
    
    @patch('app.core.slm_engine.ollama')
    def test_generate(self, mock_ollama):
        """Test generating a response."""
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {"content": "Hello! I'm JROCK's AI."}
        }
        mock_ollama.Client.return_value = mock_client
        
        engine = SLMEngine()
        response = engine.generate("Hello")
        
        assert "JROCK" in response or "Hello" in response
        mock_client.chat.assert_called_once()
    
    @patch('app.core.slm_engine.ollama')
    def test_reset_conversation(self, mock_ollama):
        """Test resetting conversation."""
        config = ModelConfig(system_prompt="System")
        engine = SLMEngine(config)
        engine.context.add_message("user", "Hello")
        
        engine.reset_conversation()
        
        # Should only have system message
        assert len(engine.context.messages) == 1
        assert engine.context.messages[0].role == "system"
