"""Agents API Router - Endpoints for multi-agent orchestration.

Provides REST API access to the agent system, allowing
direct agent access or supervisor-coordinated requests.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


# Request/Response models
class AgentRequest(BaseModel):
    """Request to an agent."""
    
    message: str = Field(..., description="The message to process")
    context: Optional[dict] = Field(default=None, description="Optional context")


class AgentResponse(BaseModel):
    """Response from an agent."""
    
    agent: str = Field(..., description="Agent that handled the request")
    content: str = Field(..., description="Response content")
    success: bool = Field(default=True)
    confidence: float = Field(default=1.0)
    reasoning: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class CodeRequest(BaseModel):
    """Request for code generation/analysis."""
    
    task: str = Field(..., description="The coding task")
    language: str = Field(default="python")
    code: Optional[str] = Field(default=None, description="Existing code for context")


class ContentRequest(BaseModel):
    """Request for content creation."""
    
    topic: str = Field(..., description="Content topic")
    content_type: str = Field(default="blog", description="Type: blog, tweet, linkedin, email")
    tone: str = Field(default="conversational")


class MemoryRequest(BaseModel):
    """Request for memory operations."""
    
    content: str = Field(..., description="Memory content or query")
    action: str = Field(default="auto", description="Action: store, retrieve, auto")
    importance: float = Field(default=0.5, ge=0, le=1)


class AgentListResponse(BaseModel):
    """List of available agents."""
    
    agents: list[dict]


# Create router
router = APIRouter(prefix="/api/agents", tags=["agents"])


# Lazy-loaded orchestrator
_orchestrator = None


def get_orchestrator():
    """Get or create the orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        from ..agents.supervisor import AgentOrchestrator
        _orchestrator = AgentOrchestrator()
    return _orchestrator


@router.get("/", response_model=AgentListResponse)
async def list_agents():
    """List all available agents."""
    orchestrator = get_orchestrator()
    
    agents = []
    for name, agent in orchestrator.supervisor._agents.items():
        agents.append({
            "name": name,
            "display_name": agent.config.name,
            "description": agent.config.description,
            "capabilities": [c.value for c in agent.config.capabilities]
        })
    
    # Add supervisor
    agents.append({
        "name": "supervisor",
        "display_name": "Supervisor",
        "description": "Routes requests to appropriate agents",
        "capabilities": ["routing", "synthesis"]
    })
    
    return AgentListResponse(agents=agents)


@router.post("/chat", response_model=AgentResponse)
async def chat_with_agents(request: AgentRequest):
    """Send a message to the agent orchestrator.
    
    The supervisor will route the request to the most appropriate
    agent(s) and return a synthesized response.
    """
    orchestrator = get_orchestrator()
    
    try:
        result = orchestrator.run(request.message, request.context)
        
        return AgentResponse(
            agent=result.agent_name,
            content=result.content,
            success=result.success,
            confidence=result.confidence,
            reasoning=result.reasoning,
            metadata=result.metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research", response_model=AgentResponse)
async def research(request: AgentRequest):
    """Send a request directly to the Research Agent."""
    orchestrator = get_orchestrator()
    agent = orchestrator.supervisor.get_agent("research")
    
    if not agent:
        raise HTTPException(status_code=404, detail="Research agent not found")
    
    result = agent.process(request.message, request.context)
    
    return AgentResponse(
        agent=result.agent_name,
        content=result.content,
        success=result.success,
        confidence=result.confidence,
        reasoning=result.reasoning,
        metadata=result.metadata
    )


@router.post("/code", response_model=AgentResponse)
async def code(request: CodeRequest):
    """Send a request directly to the Code Agent."""
    orchestrator = get_orchestrator()
    agent = orchestrator.supervisor.get_agent("code")
    
    if not agent:
        raise HTTPException(status_code=404, detail="Code agent not found")
    
    context = {"language": request.language}
    if request.code:
        context["code"] = request.code
    
    result = agent.process(request.task, context)
    
    return AgentResponse(
        agent=result.agent_name,
        content=result.content,
        success=result.success,
        confidence=result.confidence,
        reasoning=result.reasoning,
        metadata=result.metadata
    )


@router.post("/content", response_model=AgentResponse)
async def content(request: ContentRequest):
    """Send a request directly to the Content Agent."""
    orchestrator = get_orchestrator()
    agent = orchestrator.supervisor.get_agent("content")
    
    if not agent:
        raise HTTPException(status_code=404, detail="Content agent not found")
    
    result = agent.process(
        request.topic,
        {"content_type": request.content_type, "tone": request.tone}
    )
    
    return AgentResponse(
        agent=result.agent_name,
        content=result.content,
        success=result.success,
        confidence=result.confidence,
        reasoning=result.reasoning,
        metadata=result.metadata
    )


@router.post("/memory", response_model=AgentResponse)
async def memory(request: MemoryRequest):
    """Send a request directly to the Memory Agent."""
    orchestrator = get_orchestrator()
    agent = orchestrator.supervisor.get_agent("memory")
    
    if not agent:
        raise HTTPException(status_code=404, detail="Memory agent not found")
    
    result = agent.process(
        request.content,
        {"action": request.action, "importance": request.importance}
    )
    
    return AgentResponse(
        agent=result.agent_name,
        content=result.content,
        success=result.success,
        confidence=result.confidence,
        reasoning=result.reasoning,
        metadata=result.metadata
    )
