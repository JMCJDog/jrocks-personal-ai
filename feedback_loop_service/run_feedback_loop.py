"""Run and Feedback Loop Watcher.

Entry point to start the Vibe Coding feedback loop.
"""

import logging
import sys
import os
import subprocess
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# Add src to path
# run_feedback_loop.py is in Projects/jrocks-personal-ai/feedback_loop_service
# src is in Projects/jrocks-personal-ai/src
# so we need to go up one level to project root, then down to src?
# actually, no.
# script: .../feedback_loop_service/run_feedback_loop.py
# parent: .../feedback_loop_service
# parent.parent: .../Projects/jrocks-personal-ai
# src: .../Projects/jrocks-personal-ai/src
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
# Verify preventing duplicates
if str(Path(__file__).resolve().parent.parent / "src") not in sys.path:
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

def send_feedback_event(event_type: str, command: str, result: str = None, agent_name: str = None):
    """Send feedback event to the main API."""
    try:
        import httpx
        payload = {
            "event_type": event_type,
            "command": command,
            "result": result,
            "agent_name": agent_name,
            "timestamp": datetime.now().isoformat()
        }
        # Fire and forget-ish
        try:
            httpx.post("http://localhost:8000/api/webhooks/feedback/", json=payload, timeout=2.0)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"Webhook failed (backend likely down): {e}")
        except Exception as e:
            logger.warning(f"Failed to send feedback webhook: {e}")
    except ImportError:
        logger.warning("httpx not installed, skipping webhook")

def execute_command(command: str) -> str:
    """Execute a command found in the doc."""
    logger.info(f"Received command: {command}")
    
    # Notify UI: Command Detected
    send_feedback_event("command.detected", command)
    
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
            msg = "Error: No capable agent found to execute code changes."
            send_feedback_event("execution.failed", command, result=msg, agent_name="System")
            return msg
            
        logger.info(f"Dispatching to agent: {agent.name}")
        send_feedback_event("execution.started", command, agent_name=agent.name)
        
        # Execute
        # Agent uses process(message) -> AgentResponse
        response = agent.process(command)
        
        if response.success:
            result = f"Executed by {agent.name}:\n{response.content}"
            send_feedback_event("execution.completed", command, result=response.content, agent_name=agent.name)
            return result
        else:
            result = f"Agent {agent.name} failed:\n{response.content}"
            send_feedback_event("execution.failed", command, result=response.content, agent_name=agent.name)
            return result
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        msg = f"Error executing command: {str(e)}"
        send_feedback_event("execution.failed", command, result=msg, agent_name="System")
        return msg

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
