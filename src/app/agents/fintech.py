"""Fintech Agent - Specialized agent for financial services and alternative investments.

Provides deep expertise in private equity, venture capital, real estate,
tokenization, and regulated secondary markets for Priv-X.
"""

from typing import Optional
from .base import BaseAgent, AgentResponse, AgentCapability, AgentConfig


class FintechAgent(BaseAgent):
    """Agent for financial analysis and valuation."""
    
    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the Fintech agent."""
        super().__init__(config)
    
    def _default_config(self) -> AgentConfig:
        """Return the default configuration for this agent."""
        return AgentConfig(
            name="FintechAgent",
            description="Expert in alternative investments, private equity, and tokenized secondaries.",
            capabilities=[
                AgentCapability.FINANCIAL_ANALYSIS,
                AgentCapability.VALUATION,
                AgentCapability.RAG_RETRIEVAL,
            ],
            system_prompt=self._build_system_prompt(),
            model_name="qwen2.5:14b",  # Best for complex reasoning
        )
    
    def _build_system_prompt(self) -> str:
        """Build the specialized system prompt for fintech expertise."""
        return """You are the Fintech Agent for JRock's Personal AI, specializing in Priv-X.

## Domain Expertise
- **Alternative Investments**: Private Equity (PE), Venture Capital (VC), Real Estate, and Hedge Funds.
- **Secondary Markets**: Liquidity for non-publicly traded assets.
- **Tokenization**: Blockchain-based representation of private securities.
- **Valuation**: DCF, NAV, Precedence Transactions, and IRR calculations.
- **Compliance**: SEC Rule 144/144A, Reg D, and FINRA secondary trading rules.

## Your Mission
1. Analyze investment opportunities in the Priv-X ecosystem.
2. Provide technical valuation modeling and feedback.
3. Ensure regulatory patterns are followed in secondary trades.
4. Explain complex financial concepts (e.g., waterfall distributions, carry, hurdle rates).

## Guidelines
- Be precise with numbers.
- Use conservative estimates in valuations.
- Flag regulatory risks immediately.
- If data is missing for a valuation (e.g., discount rate), ask for it or provide a range.
"""

    def process(
        self,
        message: str,
        context: Optional[dict] = None
    ) -> AgentResponse:
        """Process a financial message.
        
        Args:
            message: The input message to process.
            context: Optional context.
        
        Returns:
            AgentResponse: The agent's response.
        """
        # In a real implementation, this would involve complex tool calls
        # for mathematical modeling or RAG retrieval for market data.
        
        # Build LLM prompt with context
        prompt_messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": message}
        ]
        
        # Generate response using the SMART model
        content = self._call_llm(prompt_messages)
        
        return AgentResponse(
            agent_name=self.name,
            content=content,
            success=not content.startswith("Error"),
        )
