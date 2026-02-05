"""Research Agent - Specialized for information retrieval and analysis.

Handles web search, RAG retrieval, and synthesizing information
from multiple sources.
"""

from typing import Optional
from .base import BaseAgent, AgentConfig, AgentResponse, AgentCapability, AgentMessage


class ResearchAgent(BaseAgent):
    """Agent specialized for research and information retrieval.
    
    Capabilities:
    - Web search integration
    - RAG-based knowledge retrieval
    - Source synthesis and citation
    - Fact verification
    
    Example:
        >>> agent = ResearchAgent()
        >>> response = agent.process("Find information about LangGraph")
    """
    
    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the Research Agent."""
        super().__init__(config)
        self._embedding_pipeline = None
    
    def _default_config(self) -> AgentConfig:
        """Return default configuration."""
        return AgentConfig(
            name="Research Agent",
            description="Specializes in finding, retrieving, and synthesizing information "
                       "from the knowledge base and external sources.",
            model_name="llama3.2",
            temperature=0.3,  # Lower for factual accuracy
            capabilities=[
                AgentCapability.WEB_SEARCH,
                AgentCapability.RAG_RETRIEVAL,
            ],
            system_prompt="""You are a Research Agent specialized in information retrieval.

## Your Expertise
- Searching and retrieving relevant information
- Synthesizing information from multiple sources
- Providing accurate, well-sourced answers
- Identifying knowledge gaps

## Guidelines
1. Always cite your sources when possible
2. Distinguish between facts and inferences
3. Acknowledge when information is incomplete
4. Prioritize accuracy over comprehensiveness
"""
        )
    
    def process(
        self,
        message: str,
        context: Optional[dict] = None
    ) -> AgentResponse:
        """Process a research request.
        
        Args:
            message: The research query.
            context: Optional context with search parameters.
        
        Returns:
            AgentResponse: Research results.
        """
        context = context or {}
        
        # Track this message
        self.add_to_history(AgentMessage(role="user", content=message))
        
        # Perform RAG search if available
        rag_results = []
        if context.get("use_rag", True):
            rag_results = self._search_knowledge_base(message)
        
        # Build prompt with context
        research_context = ""
        if rag_results:
            research_context = "\n## Knowledge Base Results:\n"
            for i, result in enumerate(rag_results, 1):
                research_context += f"{i}. {result}\n"
        
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"Research query: {message}\n{research_context}"}
        ]
        
        # Generate response
        response_text = self._call_llm(messages)
        
        self.add_to_history(AgentMessage(
            role="assistant",
            content=response_text,
            agent_name=self.name
        ))
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            success=True,
            confidence=0.8 if rag_results else 0.6,
            reasoning="Used RAG retrieval" if rag_results else "General knowledge",
            metadata={"sources_found": len(rag_results)}
        )
    
    def _search_knowledge_base(self, query: str, n_results: int = 3) -> list[str]:
        """Search the knowledge base using RAG.
        
        Args:
            query: Search query.
            n_results: Number of results.
        
        Returns:
            list: Retrieved text chunks.
        """
        try:
            if self._embedding_pipeline is None:
                from ..ingest.embedding_pipeline import EmbeddingPipeline
                self._embedding_pipeline = EmbeddingPipeline()
            
            results = self._embedding_pipeline.search(query, n_results=n_results)
            return [r["content"] for r in results]
            
        except Exception:
            return []
    
    def search(self, query: str) -> list[str]:
        """Direct search interface.
        
        Args:
            query: Search query.
        
        Returns:
            list: Search results.
        """
        return self._search_knowledge_base(query)
