"""Agent Coordinator - Advanced multi-agent orchestration.

Provides sophisticated coordination between agents with task planning,
capability-based routing, workflow execution, and result synthesis.
"""

from typing import Optional, Any, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

from langgraph.graph import StateGraph, END

from .base import BaseAgent, AgentResponse, AgentCapability, AgentMessage
from .agent_registry import AgentRegistry, get_registry


class TaskStatus(str, Enum):
    """Status of a task."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowMode(str, Enum):
    """Execution mode for multi-agent workflows."""
    
    SEQUENTIAL = "sequential"  # Execute tasks one by one
    PARALLEL = "parallel"      # Execute tasks concurrently
    ADAPTIVE = "adaptive"      # Route based on intermediate results


@dataclass
class Task:
    """A discrete unit of work for an agent."""
    
    id: str
    description: str
    capability: Optional[AgentCapability] = None
    agent_name: Optional[str] = None
    dependencies: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[AgentResponse] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class ExecutionPlan:
    """A plan for executing multiple tasks."""
    
    tasks: list[Task]
    workflow_mode: WorkflowMode = WorkflowMode.SEQUENTIAL
    original_request: str = ""
    context: dict = field(default_factory=dict)


@dataclass
class CoordinatorResult:
    """Result from the coordinator."""
    
    content: str
    tasks_completed: int
    tasks_failed: int
    agents_used: list[str]
    execution_time_ms: float
    metadata: dict = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        return self.tasks_failed == 0


class AgentCoordinator:
    """Coordinates multiple agents for complex task execution.
    
    Provides advanced orchestration features:
    - Task decomposition and planning
    - Capability-based agent selection
    - Multiple workflow execution modes
    - Result synthesis from multiple agents
    
    Example:
        >>> coordinator = AgentCoordinator()
        >>> result = await coordinator.execute("Research AI and write a summary")
    """
    
    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        synthesizer_model: str = "llama3.2",
    ) -> None:
        """Initialize the coordinator.
        
        Args:
            registry: Agent registry to use.
            synthesizer_model: Model for synthesis tasks.
        """
        self.registry = registry or get_registry()
        self._synthesizer_model = synthesizer_model
        self._graph = None
        self._llm = None
    
    async def execute(
        self,
        request: str,
        context: Optional[dict] = None,
        mode: WorkflowMode = WorkflowMode.ADAPTIVE,
    ) -> CoordinatorResult:
        """Execute a request using coordinated agents.
        
        Args:
            request: The user request.
            context: Optional additional context.
            mode: Workflow execution mode.
        
        Returns:
            CoordinatorResult: The execution result.
        """
        start_time = datetime.now()
        context = context or {}
        
        # Create execution plan
        plan = self._create_plan(request, mode, context)
        
        # Execute the plan
        if plan.workflow_mode == WorkflowMode.PARALLEL:
            responses = await self._execute_parallel(plan)
        else:
            responses = await self._execute_sequential(plan)
        
        # Synthesize results
        content = self._synthesize_results(request, responses)
        
        # Calculate metrics
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        completed = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in plan.tasks if t.status == TaskStatus.FAILED)
        agents = list(set(r.agent_name for r in responses if r))
        
        return CoordinatorResult(
            content=content,
            tasks_completed=completed,
            tasks_failed=failed,
            agents_used=agents,
            execution_time_ms=elapsed_ms,
            metadata={"plan_tasks": len(plan.tasks)},
        )
    
    def _create_plan(
        self,
        request: str,
        mode: WorkflowMode,
        context: dict,
    ) -> ExecutionPlan:
        """Create an execution plan for the request.
        
        Args:
            request: User request.
            mode: Workflow mode.
            context: Context.
        
        Returns:
            ExecutionPlan: The execution plan.
        """
        tasks = []
        request_lower = request.lower()
        
        # Analyze request for required capabilities
        capability_keywords = {
            AgentCapability.WEB_SEARCH: ["search", "find", "look up", "research"],
            AgentCapability.RAG_RETRIEVAL: ["remember", "recall", "knowledge", "what did"],
            AgentCapability.CODE_GENERATION: ["code", "program", "function", "script", "implement"],
            AgentCapability.CODE_ANALYSIS: ["debug", "analyze", "review code"],
            AgentCapability.CONTENT_WRITING: ["write", "blog", "tweet", "article", "summary", "draft"],
            AgentCapability.MEMORY_MANAGEMENT: ["store", "save", "remember this"],
        }
        
        detected_capabilities = []
        for cap, keywords in capability_keywords.items():
            if any(kw in request_lower for kw in keywords):
                detected_capabilities.append(cap)
        
        # Create tasks for each capability
        for i, cap in enumerate(detected_capabilities):
            agent = self.registry.get_best_for_capability(cap)
            if agent:
                tasks.append(Task(
                    id=f"task_{i}",
                    description=request,
                    capability=cap,
                    agent_name=agent.name,
                    context=context.copy(),
                ))
        
        # If no specific capabilities detected, use a general approach
        if not tasks:
            # Try to route to the most appropriate agent
            agents = self.registry.list_all()
            if agents:
                tasks.append(Task(
                    id="task_0",
                    description=request,
                    agent_name=agents[0].name,
                    context=context.copy(),
                ))
        
        # Determine workflow mode
        effective_mode = mode
        if mode == WorkflowMode.ADAPTIVE:
            # Use sequential for multi-step, parallel for independent
            if len(tasks) > 1 and self._has_dependencies(request):
                effective_mode = WorkflowMode.SEQUENTIAL
            elif len(tasks) > 1:
                effective_mode = WorkflowMode.PARALLEL
            else:
                effective_mode = WorkflowMode.SEQUENTIAL
        
        return ExecutionPlan(
            tasks=tasks,
            workflow_mode=effective_mode,
            original_request=request,
            context=context,
        )
    
    def _has_dependencies(self, request: str) -> bool:
        """Check if request implies task dependencies.
        
        Args:
            request: The request text.
        
        Returns:
            bool: True if dependencies detected.
        """
        dependency_indicators = [
            "then", "after", "first", "finally", "next",
            "and then", "once you", "based on"
        ]
        request_lower = request.lower()
        return any(ind in request_lower for ind in dependency_indicators)
    
    async def _execute_sequential(self, plan: ExecutionPlan) -> list[AgentResponse]:
        """Execute tasks sequentially.
        
        Args:
            plan: The execution plan.
        
        Returns:
            list[AgentResponse]: Agent responses.
        """
        responses = []
        accumulated_context = plan.context.copy()
        
        for task in plan.tasks:
            task.status = TaskStatus.RUNNING
            
            try:
                agent = self.registry.get(task.agent_name)
                if not agent:
                    task.status = TaskStatus.SKIPPED
                    continue
                
                # Add previous responses to context
                task.context.update(accumulated_context)
                if responses:
                    task.context["previous_response"] = responses[-1].content
                
                response = agent.process(task.description, task.context)
                
                task.result = response
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                responses.append(response)
                
                # Accumulate context
                accumulated_context[f"response_{task.id}"] = response.content
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                responses.append(AgentResponse(
                    agent_name=task.agent_name or "unknown",
                    content=f"Error: {str(e)}",
                    success=False,
                ))
        
        return responses
    
    async def _execute_parallel(self, plan: ExecutionPlan) -> list[AgentResponse]:
        """Execute tasks in parallel.
        
        Args:
            plan: The execution plan.
        
        Returns:
            list[AgentResponse]: Agent responses.
        """
        async def run_task(task: Task) -> AgentResponse:
            task.status = TaskStatus.RUNNING
            try:
                agent = self.registry.get(task.agent_name)
                if not agent:
                    task.status = TaskStatus.SKIPPED
                    return AgentResponse(
                        agent_name=task.agent_name or "unknown",
                        content="Agent not found",
                        success=False,
                    )
                
                response = agent.process(task.description, task.context)
                task.result = response
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                return response
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                return AgentResponse(
                    agent_name=task.agent_name or "unknown",
                    content=f"Error: {str(e)}",
                    success=False,
                )
        
        # Execute all tasks concurrently
        tasks_coroutines = [run_task(task) for task in plan.tasks]
        responses = await asyncio.gather(*tasks_coroutines)
        
        return list(responses)
    
    def _synthesize_results(
        self,
        request: str,
        responses: list[AgentResponse],
    ) -> str:
        """Synthesize multiple agent responses into one.
        
        Args:
            request: Original request.
            responses: Agent responses.
        
        Returns:
            str: Synthesized response.
        """
        # Filter successful responses
        successful = [r for r in responses if r.success]
        
        if not successful:
            return "I couldn't complete the request. Please try again."
        
        if len(successful) == 1:
            return successful[0].content
        
        # Multiple responses - synthesize
        synthesis_prompt = f"Original request: {request}\n\nCombine these responses coherently:\n\n"
        for r in successful:
            synthesis_prompt += f"--- {r.agent_name} ---\n{r.content}\n\n"
        synthesis_prompt += "Synthesized response:"
        
        return self._call_synthesizer(synthesis_prompt)
    
    def _call_synthesizer(self, prompt: str) -> str:
        """Call the LLM to synthesize responses.
        
        Args:
            prompt: Synthesis prompt.
        
        Returns:
            str: Synthesized text.
        """
        try:
            import ollama
            
            if self._llm is None:
                self._llm = ollama.Client()
            
            response = self._llm.chat(
                model=self._synthesizer_model,
                messages=[
                    {"role": "system", "content": "You synthesize multiple AI responses into one coherent answer."},
                    {"role": "user", "content": prompt}
                ],
            )
            return response["message"]["content"]
            
        except Exception as e:
            # Fallback: concatenate responses
            return prompt.split("Synthesized response:")[0].strip()
    
    def build_langgraph_workflow(self) -> StateGraph:
        """Build a LangGraph workflow for orchestration.
        
        Returns:
            StateGraph: Compiled LangGraph workflow.
        """
        def analyze_request(state: dict) -> dict:
            """Analyze the request and create plan."""
            request = state.get("request", "")
            plan = self._create_plan(request, WorkflowMode.ADAPTIVE, {})
            return {
                "plan": plan,
                "current_task_index": 0,
                "responses": [],
            }
        
        def execute_task(state: dict) -> dict:
            """Execute the current task."""
            plan = state.get("plan")
            idx = state.get("current_task_index", 0)
            responses = state.get("responses", [])
            
            if idx >= len(plan.tasks):
                return state
            
            task = plan.tasks[idx]
            agent = self.registry.get(task.agent_name)
            
            if agent:
                response = agent.process(task.description, task.context)
                responses.append(response)
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.SKIPPED
            
            return {
                "current_task_index": idx + 1,
                "responses": responses,
            }
        
        def should_continue(state: dict) -> Literal["execute", "synthesize"]:
            """Decide whether to continue executing tasks."""
            plan = state.get("plan")
            idx = state.get("current_task_index", 0)
            
            if idx < len(plan.tasks):
                return "execute"
            return "synthesize"
        
        def synthesize(state: dict) -> dict:
            """Synthesize all responses."""
            request = state.get("request", "")
            responses = state.get("responses", [])
            
            content = self._synthesize_results(request, responses)
            return {"final_response": content}
        
        # Build graph
        workflow = StateGraph(dict)
        
        workflow.add_node("analyze", analyze_request)
        workflow.add_node("execute", execute_task)
        workflow.add_node("synthesize", synthesize)
        
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "execute")
        workflow.add_conditional_edges("execute", should_continue)
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    async def chat(self, message: str) -> str:
        """Simple chat interface.
        
        Args:
            message: User message.
        
        Returns:
            str: Response content.
        """
        result = await self.execute(message)
        return result.content
    
    def chat_sync(self, message: str) -> str:
        """Synchronous chat interface.
        
        Args:
            message: User message.
        
        Returns:
            str: Response content.
        """
        import asyncio
        return asyncio.run(self.execute(message)).content
