import asyncio
from src.app.agents.fintech import FintechAgent
from src.app.agents.base import AgentMessage

async def verify_fintech_agent():
    agent = FintechAgent()
    
    test_queries = [
        "Explain SEC Rule 144 for tokenized private equity.",
        "Calculate the IRR for a $1M investment with $200k annual returns for 5 years and a $2M exit.",
        "What is the difference between an accredited investor and a qualified purchaser for a real estate token fund?",
        "Valuation check: A startup has $5M ARR, 80% margins, growing 100% YoY. What is a reasonable revenue multiple for a secondary sale?"
    ]
    
    print("\n--- Fintech Agent Verification ---\n")
    
    for query in test_queries:
        print(f"Query: {query}")
        result = agent.process(query)
        print(f"Response (Success: {result.success}):\n{result.content}\n")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(verify_fintech_agent())
