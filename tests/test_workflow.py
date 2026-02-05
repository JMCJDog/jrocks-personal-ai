"""Tests for workflow patterns."""

import pytest
import asyncio
from app.agents import (
    Workflow,
    SequentialWorkflow,
    ParallelWorkflow,
    WorkflowStep,
    WorkflowResult,
    BaseAgent,
    AgentConfig,
    AgentResponse,
    AgentCapability,
    create_sequential,
    create_parallel,
)


class StepAgent(BaseAgent):
    """Simple agent for workflow testing."""
    
    def __init__(self, name: str, prefix: str = ""):
        self._name = name
        self._prefix = prefix
        super().__init__()
    
    def _default_config(self) -> AgentConfig:
        return AgentConfig(
            name=self._name,
            description=f"Step agent: {self._name}",
            capabilities=[AgentCapability.CONVERSATION],
        )
    
    def process(self, message: str, context: dict = None) -> AgentResponse:
        content = f"{self._prefix}[{self._name}]: {message}"
        return AgentResponse(
            agent_name=self.name,
            content=content,
            success=True,
        )


class TestSequentialWorkflow:
    """Tests for SequentialWorkflow."""
    
    @pytest.mark.asyncio
    async def test_single_step(self):
        """Test workflow with single step."""
        workflow = SequentialWorkflow("test")
        workflow.add_step(WorkflowStep(
            id="step_1",
            agent=StepAgent("Agent1"),
        ))
        
        result = await workflow.execute("Hello")
        
        assert result.success
        assert result.steps_completed == 1
        assert "[Agent1]" in result.output
    
    @pytest.mark.asyncio
    async def test_multiple_steps(self):
        """Test workflow with multiple steps."""
        workflow = SequentialWorkflow("test")
        workflow.add_step(WorkflowStep(id="s1", agent=StepAgent("First")))
        workflow.add_step(WorkflowStep(id="s2", agent=StepAgent("Second")))
        
        result = await workflow.execute("Test")
        
        assert result.success
        assert result.steps_completed == 2
        # Second step should receive output from first
        assert "[Second]" in result.output
    
    @pytest.mark.asyncio
    async def test_context_passing(self):
        """Test that context is passed between steps."""
        workflow = SequentialWorkflow("test")
        workflow.add_step(WorkflowStep(
            id="s1", 
            agent=StepAgent("A"),
            output_key="first_result",
        ))
        workflow.add_step(WorkflowStep(
            id="s2",
            agent=StepAgent("B"),
            output_key="second_result", 
        ))
        
        result = await workflow.execute("Input")
        
        assert "first_result" in result.context.variables
        assert "second_result" in result.context.variables
    
    @pytest.mark.asyncio
    async def test_conditional_step(self):
        """Test conditional step execution."""
        workflow = SequentialWorkflow("test")
        workflow.add_step(WorkflowStep(
            id="s1",
            agent=StepAgent("Always"),
        ))
        workflow.add_step(WorkflowStep(
            id="s2",
            agent=StepAgent("Never"),
            condition=lambda ctx: False,  # Never run this step
        ))
        
        result = await workflow.execute("Test")
        
        assert result.success
        assert result.steps_completed == 1


class TestParallelWorkflow:
    """Tests for ParallelWorkflow."""
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test that steps run in parallel."""
        workflow = ParallelWorkflow("test")
        workflow.add_step(WorkflowStep(id="s1", agent=StepAgent("A")))
        workflow.add_step(WorkflowStep(id="s2", agent=StepAgent("B")))
        workflow.add_step(WorkflowStep(id="s3", agent=StepAgent("C")))
        
        result = await workflow.execute("Hello")
        
        assert result.success
        assert result.steps_completed == 3
        # All agents should be in output
        assert "[A]" in result.output
        assert "[B]" in result.output
        assert "[C]" in result.output
    
    @pytest.mark.asyncio
    async def test_custom_aggregator(self):
        """Test custom result aggregation."""
        def custom_aggregator(responses):
            return " | ".join(r.content for r in responses)
        
        workflow = ParallelWorkflow("test", aggregator=custom_aggregator)
        workflow.add_step(WorkflowStep(id="s1", agent=StepAgent("X")))
        workflow.add_step(WorkflowStep(id="s2", agent=StepAgent("Y")))
        
        result = await workflow.execute("Test")
        
        assert " | " in result.output


class TestWorkflowHelpers:
    """Tests for workflow helper functions."""
    
    @pytest.mark.asyncio
    async def test_create_sequential(self):
        """Test create_sequential helper."""
        workflow = create_sequential(
            StepAgent("A"),
            StepAgent("B"),
            name="test_seq",
        )
        
        assert isinstance(workflow, SequentialWorkflow)
        assert len(workflow.steps) == 2
        
        result = await workflow.execute("Hello")
        assert result.success
    
    @pytest.mark.asyncio
    async def test_create_parallel(self):
        """Test create_parallel helper."""
        workflow = create_parallel(
            StepAgent("X"),
            StepAgent("Y"),
            name="test_par",
        )
        
        assert isinstance(workflow, ParallelWorkflow)
        assert len(workflow.steps) == 2
        
        result = await workflow.execute("Hello")
        assert result.success


class TestWorkflowHooks:
    """Tests for workflow hooks."""
    
    @pytest.mark.asyncio
    async def test_before_hook(self):
        """Test before-step hook."""
        hook_calls = []
        
        def before_hook(step, ctx):
            hook_calls.append(f"before:{step.id}")
        
        workflow = SequentialWorkflow("test")
        workflow.add_step(WorkflowStep(id="s1", agent=StepAgent("A")))
        workflow.before_step(before_hook)
        
        await workflow.execute("Test")
        
        assert len(hook_calls) == 1
        assert "before:s1" in hook_calls
    
    @pytest.mark.asyncio
    async def test_after_hook(self):
        """Test after-step hook."""
        hook_results = []
        
        def after_hook(step, ctx, response):
            hook_results.append(response.content)
        
        workflow = SequentialWorkflow("test")
        workflow.add_step(WorkflowStep(id="s1", agent=StepAgent("Agent")))
        workflow.after_step(after_hook)
        
        await workflow.execute("Hello")
        
        assert len(hook_results) == 1
        assert "[Agent]" in hook_results[0]
