"""Data ingestion module for JRock's Personal AI.

Unified interface for processing all supported data types:
- Documents (PDF, TXT, MD)
- Images (JPEG, PNG, etc.)
- Social media exports (Twitter, LinkedIn)
- Code repositories (with git history)
- Audio/video (with transcription)
- Chat history (WhatsApp, Telegram, Discord)
"""

from .document_processor import DocumentProcessor, ProcessedDocument, process_document
from .embedding_pipeline import EmbeddingPipeline, get_pipeline
from .image_processor import ImageProcessor, ProcessedImage, process_image
from .social_processor import SocialMediaProcessor, SocialProfile, process_social_export
from .code_processor import CodeRepositoryProcessor, ProcessedRepository, process_repository
from .media_processor import AudioVideoProcessor, ProcessedMedia, transcribe_media
from .chat_processor import ChatHistoryProcessor, ChatThread, process_chat_export


__all__ = [
    # Document processing
    "DocumentProcessor",
    "ProcessedDocument",
    "process_document",
    
    # Embeddings
    "EmbeddingPipeline",
    "get_pipeline",
    
    # Image processing
    "ImageProcessor",
    "ProcessedImage",
    "process_image",
    
    # Social media
    "SocialMediaProcessor",
    "SocialProfile",
    "process_social_export",
    
    # Code repositories
    "CodeRepositoryProcessor",
    "ProcessedRepository",
    "process_repository",
    
    # Audio/video
    "AudioVideoProcessor",
    "ProcessedMedia",
    "transcribe_media",
    
    # Chat history
    "ChatHistoryProcessor",
    "ChatThread",
    "process_chat_export",
]
