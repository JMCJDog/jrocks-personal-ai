import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.app.agents.cowork import CoworkAgent
from src.app.agents.agent_registry import get_registry, register_default_agents
from src.app.core.model_registry import ModelTier

async def main():
    print("Initializing agents...")
    registry = get_registry()
    register_default_agents(registry)
    
    agent = registry.get("Cowork Agent")
    if not agent:
        print("Failed to load Cowork Agent")
        return
        
    print("\nStarting test with Cowork Agent...")
    prompt = "Create a file called cowork_test.txt with the contents 'integration successful!'. Then use the list_directory tool to view the current directory to confirm it worked. What are the results?"
    print(f"Prompt: {prompt}\n")
    
    response = await agent.process(prompt)
    
    print("\n=== Agent Result ===")
    print(f"Success: {response.success}")
    print(f"Reasoning: {response.reasoning}")
    print(f"Content:\n{response.content}")
    print("====================\n")
    
    # Check history
    print("=== History ===")
    for msg in agent.get_history():
        role = msg.role
        tc = msg.metadata.get('tool_calls') if msg.metadata else None
        print(f"[{role}]: {msg.content[:100]}...")
        if tc:
            print(f"  Tool Calls: {tc}")

if __name__ == "__main__":
    asyncio.run(main())
