"""Feedback Loop Webhook Endpoint.

Receives events from the external feedback loop service and injects them
into the system (chat history, logs, etc.).
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from ..api.chat import get_chatbot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/feedback", tags=["webhooks", "feedback"])

class FeedbackEvent(BaseModel):
    """Event received from the feedback loop."""
    event_type: str  # e.g., "command.detected", "execution.started", "execution.completed"
    command: str
    result: Optional[str] = None
    agent_name: Optional[str] = None
    timestamp: datetime = datetime.now()
    metadata: Dict[str, Any] = {}

@router.post("/")
async def receive_feedback_event(event: FeedbackEvent, background_tasks: BackgroundTasks):
    """Receive an event from the feedback loop."""
    logger.info(f"Received feedback event: {event.event_type} - {event.command}")
    
    # DEBUG TRACE
    try:
        with open("debug_feedback.txt", "a") as f:
            f.write(f"{datetime.now()}: Received {event.event_type} - {event.command}\n")
    except Exception as e:
        logger.error(f"Failed to write debug file: {e}")
    
    # Process based on event type
    try:
        if event.event_type in ["command.detected", "execution.started", "execution.completed", "execution.failed"]:
             background_tasks.add_task(inject_into_chat, event)
            
    except Exception as e:
        logger.error(f"Error processing feedback event: {e}")
        
    return {"status": "received"}

def inject_into_chat(event: FeedbackEvent):
    """Inject the event into the chatbot history so it appears in UI."""
    try:
        bot = get_chatbot()
        
        # Strategy: Find the most recent session from DB that is NOT the feedback loop session
        # This is a heuristic to find the user's active session.
        target_session_id = "feedback-loop-session"
        
        try:
            recent_sessions = bot.memory_manager.get_recent_sessions(limit=5)
            for s in recent_sessions:
                if s['session_id'] != "feedback-loop-session":
                    target_session_id = s['session_id']
                    break
        except Exception:
            pass # Fallback to feedback-loop-session

        # Special case: If no user session found, use feedback-loop-session
        logger.info(f"Injecting feedback event into session: {target_session_id}")
        
        session = bot.get_session(target_session_id)
        if not session:
            session = bot.create_session(target_session_id)
            
        # Add messages
        if event.event_type == "command.detected":
            session.add_message("user", f"⚡ [Feedback Loop] Command Detected: {event.command}")
            # Also persist immediately
            bot.memory_manager.add_message(session.session_id, "user", f"⚡ [Feedback Loop] Command Detected: {event.command}")
        
        elif event.event_type == "execution.started":
             msg = f"⚙️ Executing with {event.agent_name}..."
             session.add_message("assistant", msg)
             bot.memory_manager.add_message(session.session_id, "assistant", msg)
             
        elif event.event_type == "execution.completed":
            content = f"✅ **Result from {event.agent_name}:**\n\n{event.result}"
            session.add_message("assistant", content)
            bot.memory_manager.add_message(session.session_id, "assistant", content)
            
        elif event.event_type == "execution.failed":
            msg = f"❌ Execution failed: {event.result}"
            session.add_message("assistant", msg)
            bot.memory_manager.add_message(session.session_id, "assistant", msg)
            
    except Exception as e:
        logger.error(f"Failed to inject feedback event into chat: {e}")
        print(f"CRITICAL ERROR INJECTING CHAT: {e}")
