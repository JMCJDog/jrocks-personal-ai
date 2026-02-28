from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from pathlib import Path
import shutil
import time
import logging

from .schemas import (
    ChatRequest,
    ChatResponse,
    SessionResponse,
    ChatHistoryItem,
    ErrorResponse,
)
from ..generation.chatbot import Chatbot, ChatSession
from ..core.model_selector import model_selector


router = APIRouter(tags=["Chat"])

# Per-model chatbot instance cache
_chatbots: dict[str, "Chatbot"] = {}


def get_chatbot(model_name: str = None) -> Chatbot:
    """Get or create a chatbot instance for the given model."""
    from ..core.settings import settings_manager
    if model_name is None:
        model_name = settings_manager.get().default_model.model_name
    if model_name not in _chatbots:
        _chatbots[model_name] = Chatbot(model_name=model_name)
    return _chatbots[model_name]


@router.post(
    "",  # Matches /api/chat  (no trailing slash)
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Chat with JROCK's AI",
    description="Send a message and receive a response from JROCK's AI persona.",
    include_in_schema=False,  # Hide duplicate from docs
)
@router.post(
    "/",  # Matches /api/chat/  (with trailing slash)
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Chat with JROCK's AI",
    description="Send a message and receive a response from JROCK's AI persona."
)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to JROCK's AI."""
    try:
        # Auto-select model if not explicitly provided
        selected_model = model_selector.select(
            message=request.message,
            model_override=request.model,
        )
        bot = get_chatbot(selected_model)
        
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
            images=request.images,
            files=[f.model_dump() for f in request.files] if request.files else None,
            context=request.context,
            metadata=request.metadata
        )
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            metadata={"model_used": selected_model},
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/explain-routing",
    summary="Debug model routing",
    description="Explains which model would be selected for a given message and why."
)
async def explain_routing(message: str) -> dict:
    """Debug endpoint: shows how ModelSelector would route a given message."""
    return model_selector.explain(message)


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
@router.post("/voice")
async def chat_voice(
    file: UploadFile = File(...),
    chatbot: Chatbot = Depends(get_chatbot)
):
    """Voice chat endpoint.
    
    Processes audio input, generates AI response, and returns both 
    text and audio output.
    """
    try:
        from ..generation.stt import STTEngine
        from ..generation.voice import VoiceEngine
        
        stt = STTEngine()
        tts = VoiceEngine()
        
        # 1. Save uploaded audio to temp file
        temp_dir = Path("data/temp/audio")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_audio_path = temp_dir / f"input_{int(time.time())}.wav"
        
        with open(temp_audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Transcribe
        transcription = stt.transcribe(temp_audio_path)
        if not transcription:
            return {"error": "Could not transcribe audio"}
            
        # 3. Generate chatbot response
        response_text = chatbot.chat(transcription)
        
        # 4. Generate speech for response
        audio_response_path = await tts.generate_speech(response_text)
        
        # Return text and audio link (or stream the file)
        # For simplicity, we return the paths and text
        # In a real app, you might use FileResponse for the audio
        return {
            "input_text": transcription,
            "response_text": response_text,
            "audio_url": f"/api/chat/audio/{Path(audio_response_path).name}"
        }
        
    except Exception as e:
        logger.error(f"Voice chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve generated audio files."""
    audio_path = Path("data/output/audio") / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path)
