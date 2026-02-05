"""Task Planner - LLM-powered task decomposition.

Provides intelligent task planning and decomposition using LLMs
to break down complex requests into actionable sub-tasks.
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import re

from .base import AgentCapability


class TaskPriority(str, Enum):
    """Priority levels for tasks."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PlannedTask:
    """A task identified by the planner."""
    
    id: str
    description: str
    capability: Optional[AgentCapability] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[str] = field(default_factory=list)
    estimated_complexity: int = 1  # 1-5 scale
    metadata: dict = field(default_factory=dict)


@dataclass
class TaskPlan:
    """A complete plan with multiple tasks."""
    
    original_request: str
    tasks: list[PlannedTask]
    requires_synthesis: bool = False
    execution_order: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_parallel_groups(self) -> list[list[PlannedTask]]:
        """Get tasks grouped by parallelization opportunity.
        
        Returns:
            list[list[PlannedTask]]: Groups of tasks that can run in parallel.
        """
        if not self.tasks:
            return []
        
        groups = []
        remaining = {t.id: t for t in self.tasks}
        completed = set()
        
        while remaining:
            # Find tasks with satisfied dependencies
            ready = [
                t for t in remaining.values()
                if all(d in completed for d in t.dependencies)
            ]
            
            if not ready:
                # Break cycle by taking any remaining task
                ready = [list(remaining.values())[0]]
            
            groups.append(ready)
            for t in ready:
                completed.add(t.id)
                del remaining[t.id]
        
        return groups


class TaskPlanner:
    """LLM-powered task decomposition and planning.
    
    Analyzes complex requests and breaks them into sub-tasks
    with dependencies and capability requirements.
    
    Example:
        >>> planner = TaskPlanner()
        >>> plan = planner.plan("Research AI trends and write a blog post about them")
        >>> for task in plan.tasks:
        ...     print(task.description)
    """
    
    # Mapping from keywords to capabilities
    CAPABILITY_PATTERNS = {
        AgentCapability.WEB_SEARCH: [
            "search", "find", "look up", "research", "discover", "investigate"
        ],
        AgentCapability.RAG_RETRIEVAL: [
            "remember", "recall", "what did", "previously", "we discussed",
            "knowledge base", "from memory"
        ],
        AgentCapability.CODE_GENERATION: [
            "write code", "create function", "implement", "program",
            "script", "build a", "develop"
        ],
        AgentCapability.CODE_ANALYSIS: [
            "debug", "fix code", "analyze code", "review", "refactor",
            "find bugs", "optimize"
        ],
        AgentCapability.CONTENT_WRITING: [
            "write", "blog", "article", "tweet", "post", "summary",
            "draft", "compose", "create content"
        ],
        AgentCapability.MEMORY_MANAGEMENT: [
            "remember this", "store", "save for later", "keep track",
            "note that"
        ],
    }
    
    # Patterns indicating task boundaries
    TASK_SEPARATORS = [
        "then", "after that", "next", "finally", "also",
        "and then", "once done", "following that"
    ]
    
    def __init__(
        self,
        model_name: str = "llama3.2",
        use_llm: bool = True,
    ) -> None:
        """Initialize the task planner.
        
        Args:
            model_name: LLM model for planning.
            use_llm: Whether to use LLM for planning (vs rule-based).
        """
        self.model_name = model_name
        self.use_llm = use_llm
        self._llm = None
    
    def plan(self, request: str) -> TaskPlan:
        """Create a task plan from a request.
        
        Args:
            request: The user request.
        
        Returns:
            TaskPlan: The task plan.
        """
        if self.use_llm:
            return self._plan_with_llm(request)
        return self._plan_rule_based(request)
    
    def _plan_rule_based(self, request: str) -> TaskPlan:
        """Create plan using rule-based analysis.
        
        Args:
            request: User request.
        
        Returns:
            TaskPlan: Generated plan.
        """
        tasks = []
        request_lower = request.lower()
        
        # Split request by task separators
        segments = [request]
        for sep in self.TASK_SEPARATORS:
            new_segments = []
            for seg in segments:
                parts = seg.lower().split(sep)
                if len(parts) > 1:
                    new_segments.extend([
                        seg[seg.lower().find(p):seg.lower().find(p)+len(p)]
                        for p in parts if p.strip()
                    ])
                else:
                    new_segments.append(seg)
            segments = new_segments if new_segments else segments
        
        # Deduplicate while preserving order
        seen = set()
        unique_segments = []
        for seg in segments:
            seg_clean = seg.strip()
            if seg_clean.lower() not in seen and len(seg_clean) > 3:
                seen.add(seg_clean.lower())
                unique_segments.append(request)  # Use full request for each
        
        # If no clear segments, analyze as single task
        if len(unique_segments) <= 1:
            unique_segments = [request]
        
        # Detect capabilities and create tasks
        detected_caps = self._detect_capabilities(request_lower)
        
        if detected_caps:
            for i, cap in enumerate(detected_caps):
                tasks.append(PlannedTask(
                    id=f"task_{i}",
                    description=request,
                    capability=cap,
                    priority=TaskPriority.HIGH if i == 0 else TaskPriority.MEDIUM,
                    dependencies=[f"task_{i-1}"] if i > 0 else [],
                    estimated_complexity=self._estimate_complexity(request),
                ))
        else:
            # Default single task
            tasks.append(PlannedTask(
                id="task_0",
                description=request,
                capability=None,
                priority=TaskPriority.MEDIUM,
                estimated_complexity=self._estimate_complexity(request),
            ))
        
        return TaskPlan(
            original_request=request,
            tasks=tasks,
            requires_synthesis=len(tasks) > 1,
            execution_order=[t.id for t in tasks],
        )
    
    def _plan_with_llm(self, request: str) -> TaskPlan:
        """Create plan using LLM analysis.
        
        Args:
            request: User request.
        
        Returns:
            TaskPlan: Generated plan.
        """
        try:
            import ollama
            
            if self._llm is None:
                self._llm = ollama.Client()
            
            prompt = f"""Analyze this request and break it into discrete sub-tasks.

Request: {request}

For each task, identify:
1. A clear description
2. The type (research, code, writing, memory)
3. Dependencies on other tasks (by number)
4. Complexity (1-5)

Return as a JSON array with format:
[{{"id": "task_0", "description": "...", "type": "research|code|writing|memory", "depends_on": [], "complexity": 1}}]

Only return the JSON array, nothing else."""

            response = self._llm.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1},
            )
            
            content = response["message"]["content"]
            tasks = self._parse_llm_response(content, request)
            
            return TaskPlan(
                original_request=request,
                tasks=tasks,
                requires_synthesis=len(tasks) > 1,
                execution_order=[t.id for t in tasks],
            )
            
        except Exception:
            # Fallback to rule-based
            return self._plan_rule_based(request)
    
    def _parse_llm_response(
        self,
        content: str,
        original_request: str,
    ) -> list[PlannedTask]:
        """Parse LLM response into tasks.
        
        Args:
            content: LLM response.
            original_request: Original request.
        
        Returns:
            list[PlannedTask]: Parsed tasks.
        """
        tasks = []
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                type_to_cap = {
                    "research": AgentCapability.WEB_SEARCH,
                    "code": AgentCapability.CODE_GENERATION,
                    "writing": AgentCapability.CONTENT_WRITING,
                    "memory": AgentCapability.MEMORY_MANAGEMENT,
                }
                
                for item in data:
                    tasks.append(PlannedTask(
                        id=item.get("id", f"task_{len(tasks)}"),
                        description=item.get("description", original_request),
                        capability=type_to_cap.get(item.get("type")),
                        dependencies=item.get("depends_on", []),
                        estimated_complexity=item.get("complexity", 2),
                    ))
        except (json.JSONDecodeError, KeyError):
            pass
        
        if not tasks:
            # Fallback single task
            tasks.append(PlannedTask(
                id="task_0",
                description=original_request,
            ))
        
        return tasks
    
    def _detect_capabilities(self, text: str) -> list[AgentCapability]:
        """Detect required capabilities from text.
        
        Args:
            text: Text to analyze.
        
        Returns:
            list[AgentCapability]: Detected capabilities.
        """
        detected = []
        
        for cap, patterns in self.CAPABILITY_PATTERNS.items():
            if any(p in text for p in patterns):
                detected.append(cap)
        
        return detected
    
    def _estimate_complexity(self, text: str) -> int:
        """Estimate task complexity.
        
        Args:
            text: Task description.
        
        Returns:
            int: Complexity score 1-5.
        """
        # Simple heuristics
        complexity = 2
        
        if len(text) > 200:
            complexity += 1
        if any(word in text.lower() for word in ["complex", "detailed", "comprehensive"]):
            complexity += 1
        if any(word in text.lower() for word in ["simple", "quick", "brief"]):
            complexity -= 1
        
        return max(1, min(5, complexity))
    
    def identify_capability(self, description: str) -> Optional[AgentCapability]:
        """Identify the primary capability needed for a task.
        
        Args:
            description: Task description.
        
        Returns:
            AgentCapability or None.
        """
        caps = self._detect_capabilities(description.lower())
        return caps[0] if caps else None
