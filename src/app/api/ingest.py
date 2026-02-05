"""Ingest API routes for JRock's Personal AI.

Provides endpoints for uploading and processing documents and data.
"""

from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File

from .schemas import (
    IngestTextRequest,
    IngestResponse,
    IngestStatsResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    ErrorResponse,
)
from ..ingest.document_processor import DocumentProcessor
from ..ingest.embedding_pipeline import EmbeddingPipeline


router = APIRouter(tags=["Ingest"])

# Global pipeline instance
_pipeline: Optional[EmbeddingPipeline] = None
_processor: Optional[DocumentProcessor] = None


def get_pipeline() -> EmbeddingPipeline:
    """Get or create the global embedding pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = EmbeddingPipeline()
    return _pipeline


def get_processor() -> DocumentProcessor:
    """Get or create the global document processor."""
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor


@router.post(
    "/text",
    response_model=IngestResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Ingest text content",
    description="Process and store text content in the knowledge base."
)
async def ingest_text(request: IngestTextRequest) -> IngestResponse:
    """Ingest text content into the knowledge base.
    
    Args:
        request: The text ingestion request.
    
    Returns:
        IngestResponse: Result of the ingestion.
    """
    try:
        processor = DocumentProcessor(chunk_size=request.chunk_size)
        doc = processor.process_text(request.text, request.source_name)
        
        pipeline = get_pipeline()
        chunks_added = pipeline.add_document(doc)
        
        return IngestResponse(
            success=True,
            chunks_added=chunks_added,
            source=request.source_name,
            message=f"Successfully ingested {chunks_added} chunks from '{request.source_name}'"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/file",
    response_model=IngestResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Upload and ingest a file",
    description="Upload a document file (PDF, TXT, MD) to the knowledge base."
)
async def ingest_file(
    file: UploadFile = File(..., description="The file to upload")
) -> IngestResponse:
    """Upload and ingest a document file.
    
    Args:
        file: The uploaded file.
    
    Returns:
        IngestResponse: Result of the ingestion.
    """
    # Check file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".txt", ".md", ".pdf"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: .txt, .md, .pdf"
        )
    
    try:
        # Save to temp location
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Process the file
        processor = get_processor()
        doc = processor.process_file(tmp_path)
        
        # Clean up temp file
        Path(tmp_path).unlink()
        
        # Store in vector database
        pipeline = get_pipeline()
        chunks_added = pipeline.add_document(doc)
        
        return IngestResponse(
            success=True,
            chunks_added=chunks_added,
            source=file.filename,
            message=f"Successfully ingested {chunks_added} chunks from '{file.filename}'"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search the knowledge base",
    description="Semantic search over the ingested knowledge."
)
async def search_knowledge(request: SearchRequest) -> SearchResponse:
    """Search the knowledge base.
    
    Args:
        request: The search request.
    
    Returns:
        SearchResponse: Search results.
    """
    try:
        pipeline = get_pipeline()
        results = pipeline.search(request.query, n_results=request.n_results)
        
        search_results = [
            SearchResult(
                content=r["content"],
                source=r.get("metadata", {}).get("source", "unknown"),
                distance=r.get("distance"),
            )
            for r in results
        ]
        
        return SearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/stats",
    response_model=IngestStatsResponse,
    summary="Get ingestion statistics",
    description="Get statistics about the knowledge base."
)
async def get_stats() -> IngestStatsResponse:
    """Get knowledge base statistics.
    
    Returns:
        IngestStatsResponse: Statistics about the knowledge base.
    """
    try:
        pipeline = get_pipeline()
        stats = pipeline.get_stats()
        
        return IngestStatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
