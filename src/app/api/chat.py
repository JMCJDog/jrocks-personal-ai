"""Chat API routes for JRock's Personal AI.

Provides endpoints for interactive conversations with JROCK's AI.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException

from .schemas import (
    ChatRequest,
    ChatResponse,
    SessionResponse,
    ChatHistoryItem,
    ErrorResponse,
)
from ..generation.chatbot import Chatbot, ChatSession


router = APIRouter(tags=["Chat"])

# Global chatbot instance (initialized on first use)
_chatbot: Optional[Chatbot] = None


def get_chatbot() -> Chatbot:
    """Get or create the global chatbot instance."""
    global _chatbot
    if _chatbot is None:
        _chatbot = Chatbot()
    return _chatbot


@router.post(
    "/",
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Chat with JROCK's AI",
    description="Send a message and receive a response from JROCK's AI persona."
)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to JROCK's AI.
    
    Args:
        request: The chat request with message and optional session ID.
    
    Returns:
        ChatResponse: The AI's response with session information.
    """
    try:
        bot = get_chatbot()
        
        # Get or create session
        session_id = request.session_id
        if session_id and bot.get_session(session_id) is None:
            session_id = None
        
        if not session_id:
            session = bot.create_session()
            session_id = session.session_id
        
        # Generate response
        response_text = bot.chat(
            message=request.message,
            session_id=session_id,
            include_context=request.include_context,
        )
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/intro",
    response_model=dict,
    summary="Get AI introduction",
    description="Get an introduction message from JROCK's AI."
)
async def get_intro() -> dict:
    """Get an introduction from the AI."""
    bot = get_chatbot()
    return {"message": bot.get_intro()}


@router.get(
    "/session/{session_id}",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get session history",
    description="Retrieve the conversation history for a session."
)
async def get_session(session_id: str) -> SessionResponse:
    """Get a session's conversation history.
    
    Args:
        session_id: The session ID to retrieve.
    
    Returns:
        SessionResponse: The session history.
    """
    bot = get_chatbot()
    session = bot.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = [
        ChatHistoryItem(
            role=m.role,
            content=m.content,
            timestamp=m.timestamp
        )
        for m in session.messages
    ]
    
    return SessionResponse(
        session_id=session.session_id,
        messages=messages,
        created_at=session.created_at,
    )


@router.delete(
    "/session/{session_id}",
    response_model=dict,
    summary="Reset session",
    description="Clear the conversation history for a session."
)
async def reset_session(session_id: str) -> dict:
    """Reset a session's conversation history.
    
    Args:
        session_id: The session ID to reset.
    
    Returns:
        dict: Confirmation message.
    """
    bot = get_chatbot()
    session = bot.get_session(session_id)
    
    if session:
        session.messages.clear()
        return {"message": f"Session {session_id} has been reset"}
    
    return {"message": "Session not found or already empty"}
