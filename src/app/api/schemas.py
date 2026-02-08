"""Pydantic schemas for JRock's Personal AI API.

Defines request and response models for all API endpoints.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


# --- Chat Schemas ---

class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    
    message: str = Field(..., description="The user's message", min_length=1)
    session_id: Optional[str] = Field(None, description="Session ID to continue a conversation")
    images: Optional[list[str]] = Field(None, description="List of base64 encoded images for vision support")
    include_context: bool = Field(True, description="Whether to use RAG context")
    context: Optional[dict] = Field(None, description="Additional context for the agent (e.g. target_agent)")
    
    model_config = {"json_schema_extra": {"examples": [
        {"message": "What is in this image?", "images": ["base64_data_here"], "include_context": True}
    ]}}


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""
    
    response: str = Field(..., description="The AI's response")
    session_id: str = Field(..., description="Session ID for continuing the conversation")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class ChatHistoryItem(BaseModel):
    """A single message in chat history."""
    
    role: str
    content: str
    timestamp: datetime


class SessionResponse(BaseModel):
    """Response with session information."""
    
    session_id: str
    messages: list[ChatHistoryItem]
    created_at: datetime


# --- Ingest Schemas ---

class IngestTextRequest(BaseModel):
    """Request body for text ingestion."""
    
    text: str = Field(..., description="Text content to ingest", min_length=1)
    source_name: str = Field("direct_input", description="Name/identifier for this text source")
    chunk_size: int = Field(500, description="Target chunk size in characters", ge=100, le=2000)


class IngestResponse(BaseModel):
    """Response body for ingestion endpoints."""
    
    success: bool
    chunks_added: int
    source: str
    message: str


class IngestStatsResponse(BaseModel):
    """Response body for ingestion stats."""
    
    collection_name: str
    total_chunks: int
    embedding_model: str


# --- Search Schemas ---

class SearchRequest(BaseModel):
    """Request body for knowledge search."""
    
    query: str = Field(..., description="Search query", min_length=1)
    n_results: int = Field(5, description="Number of results to return", ge=1, le=20)


class SearchResult(BaseModel):
    """A single search result."""
    
    content: str
    source: str
    distance: Optional[float] = None


class SearchResponse(BaseModel):
    """Response body for search endpoint."""
    
    query: str
    results: list[SearchResult]
    total_results: int


# --- Health & Status Schemas ---

class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    model_available: bool = False


class ErrorResponse(BaseModel):
    """Error response."""
    
    error: str
    detail: Optional[str] = None
