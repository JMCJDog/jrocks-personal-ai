"""Run and Feedback Loop Watcher.

Entry point to start the Vibe Coding feedback loop.
"""

import logging
import sys
import os
import subprocess
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from app.ingest.providers.feedback_watcher import FeedbackWatcher
from app.agents.agent_registry import get_registry

# Configure logging with Rotation (5MB limit, 1 backup)
logging.basicConfig(
    handlers=[
        RotatingFileHandler(
            "watcher_debug.log", 
            maxBytes=5*1024*1024, 
            backupCount=1,
            encoding='utf-8' # Good practice
        ),
        logging.StreamHandler()
    ],
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("FeedbackLoop")

OLLAMA_EXE_PATH = r"C:\Users\jared\AppData\Local\Programs\Ollama\ollama app.exe"

def ensure_ollama_running():
    """Check if Ollama is running and start it if not."""
    try:
        # Check if running
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq ollama.exe', '/FO', 'CSV'], 
            capture_output=True, 
            text=True
        )
        if "ollama.exe" in result.stdout:
            return True
            
        logger.warning("Ollama not found running. Attempting to start...")
        
        # Start it
        if os.path.exists(OLLAMA_EXE_PATH):
            subprocess.Popen([OLLAMA_EXE_PATH], shell=True)
            logger.info("Ollama started successfully.")
            import time
            time.sleep(5) # Wait for startup
            return True
        else:
            logger.error(f"Ollama executable not found at {OLLAMA_EXE_PATH}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to check/start Ollama: {e}")
        return False

def execute_command(command: str) -> str:
    """Execute a command found in the doc."""
    logger.info(f"Received command: {command}")
    
    # WATCHDOG: Ensure brain is alive
    ensure_ollama_running()
    
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
            agent = registry.get_best_for_capability(AgentCapability.CODE_GENERATION)
            
        if not agent:
            return "Error: No capable agent found to execute code changes."
            
        logger.info(f"Dispatching to agent: {agent.name}")
        
        # Execute
        # Agent uses process(message) -> AgentResponse
        response = agent.process(command)
        
        if response.success:
            return f"Executed by {agent.name}:\n{response.content}"
        else:
            return f"Agent {agent.name} failed:\n{response.content}"
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return f"Error executing command: {str(e)}"

import json
import time

def load_config():
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

def main():
    config = load_config()
    doc_id = config.get("google_doc_id", "1Gxv1doTBhDs7TGo8j9SncT4x_DbM_vDwcrIQ5xlUS-0")
    poll_interval = config.get("poll_interval_seconds", 30)
    
    watcher = FeedbackWatcher(
        doc_name=config.get("doc_name", "Vibe Coding Feedback"),
        poll_interval=poll_interval,
        on_command=execute_command
    )
    watcher.doc_id = doc_id
    
    # DEBUG: Validating read access
    logger.info(f"Targeting Doc ID: {watcher.doc_id}")
    try:
        content = watcher.provider.download_file(watcher.doc_id, "application/vnd.google-apps.document")
        logger.info(f"Startup Read Success!")
    except Exception as e:
        logger.error(f"Startup Read Failed: {e}")
        # Don't return, retry might work later
        
    # Wrap in infinite loop to prevent crash exit
    while True:
        try:
            watcher.start()
        except KeyboardInterrupt:
            logger.info("Stopping watcher...")
            break
        except Exception as e:
            logger.error(f"Watcher crashed: {e}. Restarting in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    main()
