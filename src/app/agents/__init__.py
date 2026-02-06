"""Agents module for JRock's Personal AI.

Multi-agent system with specialized agents orchestrated by a supervisor.
Uses LangGraph for state management and workflow coordination.
"""

from .base import BaseAgent, AgentConfig, AgentResponse, AgentMessage, InterAgentMessage
from .research import ResearchAgent
from .code import CodeAgent
from .content import ContentAgent
from .memory import MemoryAgent
from .supervisor import SupervisorAgent, AgentOrchestrator
from .agent_registry import AgentRegistry, get_registry, register_default_agents
from .coordinator import AgentCoordinator, Task, ExecutionPlan, CoordinatorResult, WorkflowMode
from .workflow import (
    Workflow, SequentialWorkflow, ParallelWorkflow, ConditionalWorkflow,
    WorkflowStep, WorkflowResult, create_sequential, create_parallel
)
from .task_planner import TaskPlanner, TaskPlan, PlannedTask
from .circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError,
    CircuitState, CircuitBreakerRegistry, get_circuit_breaker_registry,
    with_circuit_breaker,
)
from .distributed import (
    TaskQueue, InMemoryTaskQueue, QueuedTask, TaskPriority, TaskState,
    TaskWorker, WorkerPool, DistributedCoordinator,
)


__all__ = [
    # Base
    "BaseAgent",
    "AgentConfig",
    "AgentResponse",
    "AgentMessage",
    "InterAgentMessage",
    
    # Specialized Agents
    "ResearchAgent",
    "CodeAgent",
    "ContentAgent",
    "MemoryAgent",
    
    # Orchestration
    "SupervisorAgent",
    "AgentOrchestrator",
    "AgentCoordinator",
    "AgentRegistry",
    "get_registry",
    "register_default_agents",
    
    # Workflow
    "Workflow",
    "SequentialWorkflow",
    "ParallelWorkflow",
    "ConditionalWorkflow",
    "WorkflowStep",
    "WorkflowResult",
    "WorkflowMode",
    "create_sequential",
    "create_parallel",
    
    # Planning
    "TaskPlanner",
    "TaskPlan",
    "PlannedTask",
    "Task",
    "ExecutionPlan",
    "CoordinatorResult",
]
