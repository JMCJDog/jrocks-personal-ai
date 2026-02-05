"""Workflow Patterns - Execution patterns for multi-agent workflows.

Provides configurable workflow patterns for coordinating agent execution
including sequential, parallel, hierarchical, and adaptive flows.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

from .base import BaseAgent, AgentResponse


class ExecutionStatus(str, Enum):
    """Status of workflow execution."""
    
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    
    id: str
    agent: BaseAgent
    input_transform: Optional[Callable[[dict], str]] = None
    output_key: str = "result"
    condition: Optional[Callable[[dict], bool]] = None
    timeout_seconds: int = 60
    retry_count: int = 0
    max_retries: int = 2


@dataclass
class WorkflowContext:
    """Shared context across workflow steps."""
    
    original_input: str
    variables: dict = field(default_factory=dict)
    responses: list[AgentResponse] = field(default_factory=list)
    current_step: int = 0
    status: ExecutionStatus = ExecutionStatus.NOT_STARTED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    
    success: bool
    output: str
    context: WorkflowContext
    execution_time_ms: float
    steps_completed: int
    
    @property
    def all_responses(self) -> list[AgentResponse]:
        return self.context.responses


class Workflow(ABC):
    """Abstract base class for workflows."""
    
    def __init__(self, name: str = "Workflow") -> None:
        self.name = name
        self.steps: list[WorkflowStep] = []
        self._before_hooks: list[Callable] = []
        self._after_hooks: list[Callable] = []
    
    def add_step(self, step: WorkflowStep) -> "Workflow":
        """Add a step to the workflow."""
        self.steps.append(step)
        return self
    
    def before_step(self, hook: Callable) -> None:
        """Add a before-step hook."""
        self._before_hooks.append(hook)
    
    def after_step(self, hook: Callable) -> None:
        """Add an after-step hook."""
        self._after_hooks.append(hook)
    
    @abstractmethod
    async def execute(
        self,
        input_text: str,
        initial_context: Optional[dict] = None,
    ) -> WorkflowResult:
        """Execute the workflow."""
        pass
    
    def _create_context(
        self,
        input_text: str,
        initial_context: Optional[dict] = None,
    ) -> WorkflowContext:
        """Create a new workflow context."""
        return WorkflowContext(
            original_input=input_text,
            variables=initial_context or {},
            status=ExecutionStatus.NOT_STARTED,
        )


class SequentialWorkflow(Workflow):
    """Execute steps one after another, passing context.
    
    Each step receives the accumulated context from previous steps.
    
    Example:
        >>> workflow = SequentialWorkflow("research_and_write")
        >>> workflow.add_step(WorkflowStep("research", research_agent))
        >>> workflow.add_step(WorkflowStep("write", content_agent))
    """
    
    def __init__(self, name: str = "SequentialWorkflow") -> None:
        super().__init__(name)
    
    async def execute(
        self,
        input_text: str,
        initial_context: Optional[dict] = None,
    ) -> WorkflowResult:
        """Execute steps sequentially."""
        ctx = self._create_context(input_text, initial_context)
        ctx.status = ExecutionStatus.RUNNING
        ctx.started_at = datetime.now()
        
        try:
            for i, step in enumerate(self.steps):
                ctx.current_step = i
                
                # Check condition
                if step.condition and not step.condition(ctx.variables):
                    continue
                
                # Run before hooks
                for hook in self._before_hooks:
                    hook(step, ctx)
                
                # Transform input
                if step.input_transform:
                    step_input = step.input_transform(ctx.variables)
                else:
                    # Use previous response or original input
                    if ctx.responses:
                        step_input = ctx.responses[-1].content
                    else:
                        step_input = input_text
                
                # Execute with retry
                response = await self._execute_with_retry(step, step_input, ctx)
                
                if response:
                    ctx.responses.append(response)
                    ctx.variables[step.output_key] = response.content
                
                # Run after hooks
                for hook in self._after_hooks:
                    hook(step, ctx, response)
            
            ctx.status = ExecutionStatus.COMPLETED
            ctx.completed_at = datetime.now()
            
            final_output = ctx.responses[-1].content if ctx.responses else ""
            
            return WorkflowResult(
                success=True,
                output=final_output,
                context=ctx,
                execution_time_ms=self._calc_duration(ctx),
                steps_completed=len(ctx.responses),
            )
            
        except Exception as e:
            ctx.status = ExecutionStatus.FAILED
            ctx.error = str(e)
            ctx.completed_at = datetime.now()
            
            return WorkflowResult(
                success=False,
                output=f"Workflow failed: {str(e)}",
                context=ctx,
                execution_time_ms=self._calc_duration(ctx),
                steps_completed=len(ctx.responses),
            )
    
    async def _execute_with_retry(
        self,
        step: WorkflowStep,
        input_text: str,
        ctx: WorkflowContext,
    ) -> Optional[AgentResponse]:
        """Execute a step with retry logic."""
        attempts = 0
        last_error = None
        
        while attempts <= step.max_retries:
            try:
                response = step.agent.process(input_text, ctx.variables)
                return response
            except Exception as e:
                last_error = e
                attempts += 1
                if attempts <= step.max_retries:
                    await asyncio.sleep(0.5 * attempts)
        
        if last_error:
            raise last_error
        return None
    
    def _calc_duration(self, ctx: WorkflowContext) -> float:
        """Calculate execution duration in ms."""
        if ctx.started_at and ctx.completed_at:
            return (ctx.completed_at - ctx.started_at).total_seconds() * 1000
        return 0


class ParallelWorkflow(Workflow):
    """Execute steps concurrently and aggregate results.
    
    All steps run in parallel, then results are combined.
    
    Example:
        >>> workflow = ParallelWorkflow("compare_sources")
        >>> workflow.add_step(WorkflowStep("source_a", agent_a))
        >>> workflow.add_step(WorkflowStep("source_b", agent_b))
    """
    
    def __init__(
        self,
        name: str = "ParallelWorkflow",
        aggregator: Optional[Callable[[list[AgentResponse]], str]] = None,
    ) -> None:
        super().__init__(name)
        self.aggregator = aggregator or self._default_aggregator
    
    async def execute(
        self,
        input_text: str,
        initial_context: Optional[dict] = None,
    ) -> WorkflowResult:
        """Execute all steps in parallel."""
        ctx = self._create_context(input_text, initial_context)
        ctx.status = ExecutionStatus.RUNNING
        ctx.started_at = datetime.now()
        
        try:
            # Create tasks for all steps
            tasks = []
            for step in self.steps:
                if step.condition and not step.condition(ctx.variables):
                    continue
                
                step_input = step.input_transform(ctx.variables) if step.input_transform else input_text
                tasks.append(self._run_step(step, step_input, ctx.variables.copy()))
            
            # Execute all in parallel
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            valid_responses = []
            for resp in responses:
                if isinstance(resp, AgentResponse):
                    valid_responses.append(resp)
                    ctx.responses.append(resp)
            
            ctx.status = ExecutionStatus.COMPLETED
            ctx.completed_at = datetime.now()
            
            # Aggregate results
            final_output = self.aggregator(valid_responses)
            
            return WorkflowResult(
                success=len(valid_responses) > 0,
                output=final_output,
                context=ctx,
                execution_time_ms=self._calc_duration(ctx),
                steps_completed=len(valid_responses),
            )
            
        except Exception as e:
            ctx.status = ExecutionStatus.FAILED
            ctx.error = str(e)
            ctx.completed_at = datetime.now()
            
            return WorkflowResult(
                success=False,
                output=f"Workflow failed: {str(e)}",
                context=ctx,
                execution_time_ms=self._calc_duration(ctx),
                steps_completed=len(ctx.responses),
            )
    
    async def _run_step(
        self,
        step: WorkflowStep,
        input_text: str,
        context: dict,
    ) -> AgentResponse:
        """Run a single step."""
        return step.agent.process(input_text, context)
    
    def _default_aggregator(self, responses: list[AgentResponse]) -> str:
        """Default aggregation - concatenate responses."""
        if not responses:
            return ""
        if len(responses) == 1:
            return responses[0].content
        
        parts = []
        for r in responses:
            parts.append(f"## {r.agent_name}\n{r.content}")
        return "\n\n".join(parts)
    
    def _calc_duration(self, ctx: WorkflowContext) -> float:
        if ctx.started_at and ctx.completed_at:
            return (ctx.completed_at - ctx.started_at).total_seconds() * 1000
        return 0


class ConditionalWorkflow(Workflow):
    """Execute steps based on conditions and branching.
    
    Routes to different paths based on conditional logic.
    
    Example:
        >>> workflow = ConditionalWorkflow("adaptive")
        >>> workflow.add_branch("code", lambda ctx: "code" in ctx["input"], code_steps)
        >>> workflow.add_branch("content", lambda ctx: True, content_steps)
    """
    
    def __init__(self, name: str = "ConditionalWorkflow") -> None:
        super().__init__(name)
        self.branches: list[tuple[str, Callable, list[WorkflowStep]]] = []
        self._fallback_steps: list[WorkflowStep] = []
    
    def add_branch(
        self,
        name: str,
        condition: Callable[[dict], bool],
        steps: list[WorkflowStep],
    ) -> "ConditionalWorkflow":
        """Add a conditional branch."""
        self.branches.append((name, condition, steps))
        return self
    
    def set_fallback(self, steps: list[WorkflowStep]) -> "ConditionalWorkflow":
        """Set fallback steps if no branch matches."""
        self._fallback_steps = steps
        return self
    
    async def execute(
        self,
        input_text: str,
        initial_context: Optional[dict] = None,
    ) -> WorkflowResult:
        """Execute the matching branch."""
        ctx = self._create_context(input_text, initial_context)
        ctx.variables["input"] = input_text
        ctx.status = ExecutionStatus.RUNNING
        ctx.started_at = datetime.now()
        
        # Find matching branch
        steps_to_run = self._fallback_steps
        branch_name = "fallback"
        
        for name, condition, steps in self.branches:
            try:
                if condition(ctx.variables):
                    steps_to_run = steps
                    branch_name = name
                    break
            except Exception:
                continue
        
        ctx.variables["branch"] = branch_name
        
        # Execute selected branch as sequential
        try:
            for step in steps_to_run:
                if ctx.responses:
                    step_input = ctx.responses[-1].content
                else:
                    step_input = input_text
                
                response = step.agent.process(step_input, ctx.variables)
                ctx.responses.append(response)
                ctx.variables[step.output_key] = response.content
            
            ctx.status = ExecutionStatus.COMPLETED
            ctx.completed_at = datetime.now()
            
            final_output = ctx.responses[-1].content if ctx.responses else ""
            
            return WorkflowResult(
                success=True,
                output=final_output,
                context=ctx,
                execution_time_ms=self._calc_duration(ctx),
                steps_completed=len(ctx.responses),
            )
            
        except Exception as e:
            ctx.status = ExecutionStatus.FAILED
            ctx.error = str(e)
            ctx.completed_at = datetime.now()
            
            return WorkflowResult(
                success=False,
                output=f"Workflow failed: {str(e)}",
                context=ctx,
                execution_time_ms=self._calc_duration(ctx),
                steps_completed=len(ctx.responses),
            )
    
    def _calc_duration(self, ctx: WorkflowContext) -> float:
        if ctx.started_at and ctx.completed_at:
            return (ctx.completed_at - ctx.started_at).total_seconds() * 1000
        return 0


def create_sequential(*agents: BaseAgent, name: str = "Sequential") -> SequentialWorkflow:
    """Helper to create a sequential workflow from agents.
    
    Args:
        *agents: Agents to chain.
        name: Workflow name.
    
    Returns:
        SequentialWorkflow: Configured workflow.
    """
    workflow = SequentialWorkflow(name)
    for i, agent in enumerate(agents):
        workflow.add_step(WorkflowStep(
            id=f"step_{i}",
            agent=agent,
            output_key=f"step_{i}_result",
        ))
    return workflow


def create_parallel(*agents: BaseAgent, name: str = "Parallel") -> ParallelWorkflow:
    """Helper to create a parallel workflow from agents.
    
    Args:
        *agents: Agents to run in parallel.
        name: Workflow name.
    
    Returns:
        ParallelWorkflow: Configured workflow.
    """
    workflow = ParallelWorkflow(name)
    for i, agent in enumerate(agents):
        workflow.add_step(WorkflowStep(
            id=f"step_{i}",
            agent=agent,
            output_key=f"step_{i}_result",
        ))
    return workflow
