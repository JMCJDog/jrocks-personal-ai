"""Tests for the AgentCoordinator and AgentRegistry."""

import pytest
import asyncio
from app.agents import (
    AgentCoordinator,
    AgentRegistry,
    BaseAgent,
    AgentConfig,
    AgentResponse,
    AgentCapability,
    WorkflowMode,
)


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    def __init__(self, name: str = "MockAgent", caps: list = None):
        self._name = name
        self._caps = caps or [AgentCapability.CONVERSATION]
        super().__init__()
    
    def _default_config(self) -> AgentConfig:
        return AgentConfig(
            name=self._name,
            description="A mock agent for testing",
            capabilities=self._caps,
        )
    
    def process(self, message: str, context: dict = None) -> AgentResponse:
        return AgentResponse(
            agent_name=self.name,
            content=f"Processed: {message}",
            success=True,
            confidence=0.9,
        )


class TestAgentRegistry:
    """Tests for AgentRegistry."""
    
    def test_register_agent(self):
        """Test registering an agent."""
        registry = AgentRegistry()
        agent = MockAgent("TestAgent")
        
        entry = registry.register(agent)
        
        assert entry.name == "TestAgent"
        assert "TestAgent" in registry
    
    def test_duplicate_registration_raises(self):
        """Test that duplicate registration raises error."""
        registry = AgentRegistry()
        agent = MockAgent("TestAgent")
        
        registry.register(agent)
        
        with pytest.raises(ValueError):
            registry.register(agent)
    
    def test_duplicate_with_replace(self):
        """Test replacing an existing registration."""
        registry = AgentRegistry()
        agent1 = MockAgent("TestAgent")
        agent2 = MockAgent("TestAgent")
        
        registry.register(agent1)
        registry.register(agent2, replace=True)
        
        assert registry.count() == 1
    
    def test_get_by_capability(self):
        """Test retrieving agents by capability."""
        registry = AgentRegistry()
        search_agent = MockAgent("SearchAgent", [AgentCapability.WEB_SEARCH])
        code_agent = MockAgent("CodeAgent", [AgentCapability.CODE_GENERATION])
        
        registry.register(search_agent)
        registry.register(code_agent)
        
        result = registry.get_by_capability(AgentCapability.WEB_SEARCH)
        
        assert len(result) == 1
        assert result[0].name == "SearchAgent"
    
    def test_get_best_for_capability(self):
        """Test getting highest priority agent for capability."""
        registry = AgentRegistry()
        agent1 = MockAgent("LowPriority", [AgentCapability.CODE_GENERATION])
        agent2 = MockAgent("HighPriority", [AgentCapability.CODE_GENERATION])
        
        registry.register(agent1, priority=1)
        registry.register(agent2, priority=10)
        
        result = registry.get_best_for_capability(AgentCapability.CODE_GENERATION)
        
        assert result.name == "HighPriority"
    
    def test_list_capabilities(self):
        """Test listing all capabilities."""
        registry = AgentRegistry()
        registry.register(MockAgent("A", [AgentCapability.WEB_SEARCH]))
        registry.register(MockAgent("B", [AgentCapability.CODE_GENERATION]))
        
        caps = registry.list_capabilities()
        
        assert AgentCapability.WEB_SEARCH in caps
        assert AgentCapability.CODE_GENERATION in caps
    
    def test_enable_disable(self):
        """Test enabling and disabling agents."""
        registry = AgentRegistry()
        registry.register(MockAgent("TestAgent"))
        
        assert registry.count() == 1
        
        registry.disable("TestAgent")
        assert registry.count(only_enabled=True) == 0
        assert registry.count(only_enabled=False) == 1
        
        registry.enable("TestAgent")
        assert registry.count() == 1


class TestAgentCoordinator:
    """Tests for AgentCoordinator."""
    
    @pytest.fixture
    def coordinator(self):
        """Create a coordinator with mock agents."""
        registry = AgentRegistry()
        registry.register(MockAgent("Research", [AgentCapability.WEB_SEARCH]))
        registry.register(MockAgent("Code", [AgentCapability.CODE_GENERATION]))
        registry.register(MockAgent("Content", [AgentCapability.CONTENT_WRITING]))
        
        return AgentCoordinator(registry=registry)
    
    @pytest.mark.asyncio
    async def test_execute_simple_request(self, coordinator):
        """Test executing a simple request."""
        result = await coordinator.execute("Test message")
        
        assert result.success
        assert len(result.content) > 0
    
    @pytest.mark.asyncio
    async def test_execute_with_research_capability(self, coordinator):
        """Test that research requests route correctly."""
        result = await coordinator.execute("Search for AI information")
        
        assert result.success
        assert "Research" in result.agents_used
    
    @pytest.mark.asyncio
    async def test_execute_with_code_capability(self, coordinator):
        """Test that code requests route correctly."""
        result = await coordinator.execute("Write a Python function")
        
        assert result.success
        assert "Code" in result.agents_used
    
    @pytest.mark.asyncio
    async def test_execute_multi_agent(self, coordinator):
        """Test multi-agent execution."""
        result = await coordinator.execute(
            "Research AI then write a blog post about it"
        )
        
        assert result.success
        assert result.tasks_completed > 0
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, coordinator):
        """Test parallel execution mode."""
        result = await coordinator.execute(
            "Compare Python and JavaScript",
            mode=WorkflowMode.PARALLEL,
        )
        
        assert result.success
    
    def test_chat_sync(self, coordinator):
        """Test synchronous chat interface."""
        response = coordinator.chat_sync("Hello")
        
        assert len(response) > 0


class TestExecutionPlan:
    """Tests for execution planning."""
    
    def test_plan_creation(self):
        """Test that plans are created correctly."""
        registry = AgentRegistry()
        registry.register(MockAgent("Test", [AgentCapability.WEB_SEARCH]))
        
        coordinator = AgentCoordinator(registry=registry)
        plan = coordinator._create_plan("Search for something", WorkflowMode.SEQUENTIAL, {})
        
        assert len(plan.tasks) > 0
        assert plan.workflow_mode == WorkflowMode.SEQUENTIAL
    
    def test_adaptive_mode_detection(self):
        """Test that adaptive mode correctly detects workflow type."""
        registry = AgentRegistry()
        registry.register(MockAgent("R", [AgentCapability.WEB_SEARCH]))
        registry.register(MockAgent("W", [AgentCapability.CONTENT_WRITING]))
        
        coordinator = AgentCoordinator(registry=registry)
        
        # Sequential indicator
        plan = coordinator._create_plan(
            "First search, then write",
            WorkflowMode.ADAPTIVE, {}
        )
        assert plan.workflow_mode == WorkflowMode.SEQUENTIAL
