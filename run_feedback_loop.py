"""Run and Feedback Loop Watcher.

Entry point to start the Vibe Coding feedback loop.
"""

import logging
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from app.ingest.providers.feedback_watcher import FeedbackWatcher
from app.agents.agent_registry import get_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("FeedbackLoop")

def execute_command(command: str) -> str:
    """Execute a command found in the doc."""
    logger.info(f"Received command: {command}")
    
    try:
        # Get the code agent or orchestrator
        registry = get_registry()
        
        # We need to make sure agents are registered
        if not registry.count():
            from app.agents.agent_registry import register_default_agents
            register_default_agents(registry)
            
        # Find a capable agent (CodeAgent is best for "vibe coding")
        # In a real scenario, we might use a supervisor to decide
        agent = registry.get("code_developer") # Assuming CodeAgent is named 'code_developer' or similar
        
        if not agent:
            # Fallback to finding by capability
            from app.agents.base import AgentCapability
            agent = registry.get_best_for_capability(AgentCapability.CODE_MODIFICATION)
            
        if not agent:
            return "Error: No capable agent found to execute code changes."
            
        logger.info(f"Dispatching to agent: {agent.name}")
        
        # Execute
        # Note: This assumes agent.run(input) signature
        result = agent.run(command)
        return f"Executed by {agent.name}:\n{result}"
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return f"Error executing command: {str(e)}"

def main():
    watcher = FeedbackWatcher(
        doc_name="Vibe Coding Feedback",
        on_command=execute_command
    )
    watcher.start()

if __name__ == "__main__":
    main()
