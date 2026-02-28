import asyncio
from src.app.agents.coordinator import AgentCoordinator, WorkflowMode
from src.app.agents.agent_registry import register_default_agents

async def verify_coordinator_routing():
    # Setup coordinator with default agents
    register_default_agents()
    coordinator = AgentCoordinator()
    
    test_queries = [
        "I need help with portfolio management for my private equity holdings.",
        "Analyze the deal flow for these alternative investments.",
        "What's the due diligence process for a real estate fund?",
        "Calculate the moic for this venture capital exit."
    ]
    
    print("\n--- Coordinator Routing Verification ---\n")
    
    for query in test_queries:
        print(f"Query: {query}")
        plan = coordinator._create_plan(query, WorkflowMode.ADAPTIVE, {})
        agent_names = [t.agent_name for t in plan.tasks]
        capabilities = [t.capability for t in plan.tasks]
        print(f"Selected Agents: {agent_names}")
        print(f"Detected Capabilities: {capabilities}")
        
        # Check if FintechAgent is selected
        if "FintechAgent" in agent_names:
            print("✅ FintechAgent correctly identified.")
        else:
            print("❌ FintechAgent NOT identified.")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(verify_coordinator_routing())
