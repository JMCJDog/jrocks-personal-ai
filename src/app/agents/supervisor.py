"""Supervisor Agent - Orchestrates multiple specialized agents.

Implements the supervisor pattern for multi-agent coordination,
routing tasks to appropriate agents and synthesizing results.
"""

from typing import Optional, Type
from dataclasses import dataclass, field
from enum import Enum

from langgraph.graph import StateGraph, END

from .base import BaseAgent, AgentConfig, AgentResponse, AgentCapability, AgentMessage


class RoutingDecision(str, Enum):
    """Routing decisions for the supervisor."""
    
    RESEARCH = "research"
    CODE = "code"
    CONTENT = "content"
    MEMORY = "memory"
    MULTI = "multi"  # Multiple agents needed
    DIRECT = "direct"  # Handle directly


@dataclass
class OrchestratorState:
    """State for the agent orchestrator."""
    
    input: str = ""
    context: dict = field(default_factory=dict)
    routing: RoutingDecision = RoutingDecision.DIRECT
    agent_responses: list[AgentResponse] = field(default_factory=list)
    final_response: str = ""
    iteration: int = 0
    max_iterations: int = 3


class SupervisorAgent(BaseAgent):
    """Supervisor agent that routes and coordinates other agents.
    
    Uses a router to determine which agent(s) should handle a request,
    then synthesizes their responses into a final answer.
    
    Example:
        >>> supervisor = SupervisorAgent()
        >>> supervisor.register_agent("research", ResearchAgent())
        >>> response = supervisor.process("Find info and write a summary")
    """
    
    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the Supervisor Agent."""
        super().__init__(config)
        self._agents: dict[str, BaseAgent] = {}
    
    def _default_config(self) -> AgentConfig:
        """Return default configuration."""
        return AgentConfig(
            name="Supervisor",
            description="Coordinates multiple specialized agents to handle complex tasks "
                       "by routing requests and synthesizing responses.",
            model_name="llama3.2",
            temperature=0.5,
            capabilities=[AgentCapability.CONVERSATION],
            system_prompt="""You are a Supervisor Agent coordinating a team of specialists.

## Your Team
- Research Agent: Information retrieval and analysis
- Code Agent: Programming and technical tasks
- Content Agent: Writing and content creation
- Memory Agent: Knowledge management

## Your Role
1. Analyze incoming requests
2. Route to appropriate agent(s)
3. Synthesize responses when multiple agents contribute
4. Ensure quality and coherence of final output

## Routing Keywords
- Research: search, find, retrieve, what is, explain
- Code: write code, debug, program, function, implement
- Content: write, create, blog, tweet, article
- Memory: remember, recall, store, what did I say
"""
        )
    
    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register a specialized agent.
        
        Args:
            name: Agent identifier.
            agent: The agent instance.
        """
        self._agents[name] = agent
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get a registered agent.
        
        Args:
            name: Agent identifier.
        
        Returns:
            BaseAgent or None.
        """
        return self._agents.get(name)
    
    def process(
        self,
        message: str,
        context: Optional[dict] = None
    ) -> AgentResponse:
        """Process a request by routing to appropriate agents.
        
        Args:
            message: The input message.
            context: Optional context.
        
        Returns:
            AgentResponse: Synthesized response.
        """
        context = context or {}
        
        # Check for forced routing via context
        target_agent = context.get("target_agent")
        if target_agent:
            # Handle supervisor specifically
            if target_agent == "supervisor":
                return self._handle_direct(message, context)
                
            # Handle specific agents
            if target_agent in self._agents:
                response = self._agents[target_agent].process(message, context)
                return self._wrap_response(response)
        
        # Route the request
        routing = self._route_request(message)
        
        # Handle based on routing
        if routing == RoutingDecision.DIRECT:
            return self._handle_direct(message, context)
        
        if routing == RoutingDecision.MULTI:
            return self._handle_multi(message, context)
        
        # Route to specific agent
        agent_name = routing.value
        if agent_name in self._agents:
            response = self._agents[agent_name].process(message, context)
            return self._wrap_response(response)
        
        # Fallback to direct
        return self._handle_direct(message, context)
    
    def _route_request(self, message: str) -> RoutingDecision:
        """Determine which agent(s) should handle the request.
        
        Args:
            message: The input message.
        
        Returns:
            RoutingDecision: The routing decision.
        """
        message_lower = message.lower()
        
        # Check for multi-agent indicators
        multi_keywords = ["and also", "then write", "find and create", "research and code"]
        if any(kw in message_lower for kw in multi_keywords):
            return RoutingDecision.MULTI
        
        # Route to specific agents
        research_keywords = ["search", "find", "retrieve", "what is", "explain", "look up"]
        code_keywords = ["code", "program", "function", "debug", "implement", "write a script"]
        content_keywords = ["write", "blog", "tweet", "article", "create content", "draft"]
        memory_keywords = ["remember", "recall", "store", "memory", "what did i"]
        
        if any(kw in message_lower for kw in code_keywords):
            return RoutingDecision.CODE
        if any(kw in message_lower for kw in content_keywords):
            return RoutingDecision.CONTENT
        if any(kw in message_lower for kw in memory_keywords):
            return RoutingDecision.MEMORY
        if any(kw in message_lower for kw in research_keywords):
            return RoutingDecision.RESEARCH
        
        return RoutingDecision.DIRECT
    
    def _handle_direct(
        self,
        message: str,
        context: dict
    ) -> AgentResponse:
        """Handle a request directly without delegation.
        
        Args:
            message: The input message.
            context: Context.
        
        Returns:
            AgentResponse: Direct response.
        """
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": message}
        ]
        
        response_text = self._call_llm(messages)
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            success=True,
            confidence=0.7,
            reasoning="Handled directly by supervisor"
        )
    
    def _handle_multi(
        self,
        message: str,
        context: dict
    ) -> AgentResponse:
        """Handle a multi-agent request.
        
        Args:
            message: The input message.
            context: Context.
        
        Returns:
            AgentResponse: Synthesized response.
        """
        responses = []
        
        # Call relevant agents in sequence
        for name, agent in self._agents.items():
            try:
                response = agent.process(message, context)
                responses.append(response)
            except Exception:
                continue
        
        if not responses:
            return self._handle_direct(message, context)
        
        # Synthesize responses
        synthesis_prompt = f"Original request: {message}\n\nAgent responses:\n"
        for resp in responses:
            synthesis_prompt += f"\n--- {resp.agent_name} ---\n{resp.content}\n"
        synthesis_prompt += "\nPlease synthesize these into a coherent, unified response."
        
        messages = [
            {"role": "system", "content": "You synthesize multiple agent responses into one coherent answer."},
            {"role": "user", "content": synthesis_prompt}
        ]
        
        final_text = self._call_llm(messages)
        
        return AgentResponse(
            agent_name=self.name,
            content=final_text,
            success=True,
            confidence=0.85,
            reasoning=f"Synthesized from {len(responses)} agents",
            metadata={"agents_used": [r.agent_name for r in responses]}
        )
    
    def _wrap_response(self, response: AgentResponse) -> AgentResponse:
        """Wrap an agent response for consistency.
        
        Args:
            response: The agent response.
        
        Returns:
            AgentResponse: Wrapped response.
        """
        response.metadata["routed_by"] = self.name
        return response


class AgentOrchestrator:
    """LangGraph-based orchestrator for multi-agent workflows.
    
    Provides a more sophisticated orchestration layer using
    LangGraph state machines for complex agent interactions.
    
    Example:
        >>> orchestrator = AgentOrchestrator()
        >>> result = orchestrator.run("Research AI and write a blog post")
    """
    
    def __init__(self) -> None:
        """Initialize the orchestrator."""
        self.supervisor = SupervisorAgent()
        self._graph = None
        self._setup_default_agents()
    
    def _setup_default_agents(self) -> None:
        """Set up default specialized agents."""
        from .research import ResearchAgent
        from .code import CodeAgent
        from .content import ContentAgent
        from .memory import MemoryAgent
        
        self.supervisor.register_agent("research", ResearchAgent())
        self.supervisor.register_agent("code", CodeAgent())
        self.supervisor.register_agent("content", ContentAgent())
        self.supervisor.register_agent("memory", MemoryAgent())
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.
        
        Returns:
            StateGraph: The compiled workflow.
        """
        # Define state schema
        def analyze_input(state: dict) -> dict:
            """Analyze input and determine routing."""
            message = state.get("input", "")
            routing = self.supervisor._route_request(message)
            return {"routing": routing.value}
        
        def route_to_agent(state: dict) -> dict:
            """Route to the appropriate agent."""
            routing = state.get("routing", "direct")
            message = state.get("input", "")
            context = state.get("context", {})
            
            if routing == "direct":
                response = self.supervisor._handle_direct(message, context)
            elif routing == "multi":
                response = self.supervisor._handle_multi(message, context)
            else:
                agent = self.supervisor.get_agent(routing)
                if agent:
                    response = agent.process(message, context)
                else:
                    response = self.supervisor._handle_direct(message, context)
            
            return {"agent_response": response, "final_response": response.content}
        
        # Build graph
        workflow = StateGraph(dict)
        
        workflow.add_node("analyze", analyze_input)
        workflow.add_node("route", route_to_agent)
        
        workflow.add_edge("analyze", "route")
        workflow.add_edge("route", END)
        
        workflow.set_entry_point("analyze")
        
        return workflow.compile()
    
    @property
    def graph(self) -> StateGraph:
        """Get or build the workflow graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph
    
    def run(self, message: str, context: Optional[dict] = None) -> AgentResponse:
        """Run the orchestrator on a message.
        
        Args:
            message: The input message.
            context: Optional context.
        
        Returns:
            AgentResponse: The final response.
        """
        initial_state = {
            "input": message,
            "context": context or {},
            "routing": "direct",
            "agent_responses": [],
            "final_response": "",
        }
        
        result = self.graph.invoke(initial_state)
        
        if "agent_response" in result:
            return result["agent_response"]
        
        return AgentResponse(
            agent_name="Orchestrator",
            content=result.get("final_response", ""),
            success=True,
        )
    
    def add_agent(self, name: str, agent: BaseAgent) -> None:
        """Add a custom agent to the orchestrator.
        
        Args:
            name: Agent identifier.
            agent: The agent instance.
        """
        self.supervisor.register_agent(name, agent)
    
    def chat(self, message: str) -> str:
        """Simple chat interface.
        
        Args:
            message: User message.
        
        Returns:
            str: Response content.
        """
        response = self.run(message)
        return response.content
