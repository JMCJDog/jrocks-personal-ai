"""Document Processor - Extract and chunk text from various document formats.

Supports PDF, text files, markdown, and other document types for
ingestion into the personal AI knowledge base.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
import hashlib


@dataclass
class DocumentChunk:
    """A chunk of processed document content."""
    
    content: str
    source: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)
    
    @property
    def id(self) -> str:
        """Generate a unique ID for this chunk."""
        hash_input = f"{self.source}:{self.chunk_index}:{self.content[:100]}"
        return hashlib.md5(hash_input.encode()).hexdigest()


@dataclass
class ProcessedDocument:
    """A fully processed document with all its chunks."""
    
    source_path: str
    title: str
    chunks: list[DocumentChunk] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    @property
    def total_chunks(self) -> int:
        """Get the total number of chunks."""
        return len(self.chunks)
    
    @property
    def total_characters(self) -> int:
        """Get the total character count across all chunks."""
        return sum(len(c.content) for c in self.chunks)


class DocumentProcessor:
    """Process documents for ingestion into the knowledge base.
    
    Handles text extraction, chunking, and metadata extraction
    from various document formats.
    
    Example:
        >>> processor = DocumentProcessor(chunk_size=500)
        >>> doc = processor.process_file("path/to/document.pdf")
        >>> for chunk in doc.chunks:
        ...     print(chunk.content)
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        """Initialize the document processor.
        
        Args:
            chunk_size: Target size for each chunk in characters.
            chunk_overlap: Number of characters to overlap between chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Supported extensions and their handlers
        self._handlers = {
            ".txt": self._extract_text,
            ".md": self._extract_text,
            ".pdf": self._extract_pdf,
        }
    
    def process_file(self, file_path: str | Path) -> ProcessedDocument:
        """Process a single file.
        
        Args:
            file_path: Path to the file to process.
        
        Returns:
            ProcessedDocument: The processed document with chunks.
        
        Raises:
            ValueError: If the file type is not supported.
            FileNotFoundError: If the file doesn't exist.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        ext = path.suffix.lower()
        if ext not in self._handlers:
            raise ValueError(f"Unsupported file type: {ext}")
        
        # Extract text content
        text_content = self._handlers[ext](path)
        
        # Chunk the content
        chunks = self._chunk_text(text_content, str(path))
        
        return ProcessedDocument(
            source_path=str(path),
            title=path.stem,
            chunks=chunks,
            metadata={
                "file_type": ext,
                "file_size": path.stat().st_size,
            }
        )
    
    def process_text(
        self,
        text: str,
        source_name: str = "direct_input"
    ) -> ProcessedDocument:
        """Process raw text content.
        
        Args:
            text: The text content to process.
            source_name: A name to identify this text source.
        
        Returns:
            ProcessedDocument: The processed document with chunks.
        """
        chunks = self._chunk_text(text, source_name)
        
        return ProcessedDocument(
            source_path=source_name,
            title=source_name,
            chunks=chunks,
            metadata={"type": "raw_text"}
        )
    
    def _extract_text(self, path: Path) -> str:
        """Extract text from a plain text file.
        
        Args:
            path: Path to the text file.
        
        Returns:
            str: The file contents.
        """
        return path.read_text(encoding="utf-8")
    
    def _extract_pdf(self, path: Path) -> str:
        """Extract text from a PDF file.
        
        Args:
            path: Path to the PDF file.
        
        Returns:
            str: Extracted text content.
        """
        try:
            from pypdf import PdfReader
            
            reader = PdfReader(str(path))
            text_parts = []
            
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            return "\n\n".join(text_parts)
            
        except ImportError:
            raise ImportError(
                "pypdf is required for PDF processing. "
                "Install it with: pip install pypdf"
            )
    
    def _chunk_text(
        self,
        text: str,
        source: str
    ) -> list[DocumentChunk]:
        """Split text into overlapping chunks.
        
        Args:
            text: The text to chunk.
            source: The source identifier.
        
        Returns:
            list: List of DocumentChunk objects.
        """
        # Clean and normalize text
        text = text.strip()
        if not text:
            return []
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Determine end position
            end = start + self.chunk_size
            
            # Try to break at a sentence or paragraph boundary
            if end < len(text):
                # Look for paragraph break
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + self.chunk_size // 2:
                    end = para_break + 2
                else:
                    # Look for sentence break
                    for punct in [".", "!", "?"]:
                        sent_break = text.rfind(punct, start, end)
                        if sent_break > start + self.chunk_size // 2:
                            end = sent_break + 1
                            break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append(DocumentChunk(
                    content=chunk_text,
                    source=source,
                    chunk_index=chunk_index,
                    metadata={"start_char": start, "end_char": end}
                ))
                chunk_index += 1
            
            # Move start position, accounting for overlap
            start = end - self.chunk_overlap
            
            # Prevent infinite loop
            if start >= len(text) - self.chunk_overlap:
                break
        
        return chunks


# Convenience function
def process_document(
    file_path: str,
    chunk_size: int = 500
) -> ProcessedDocument:
    """Process a document file.
    
    Args:
        file_path: Path to the document.
        chunk_size: Target chunk size.
    
    Returns:
        ProcessedDocument: The processed document.
    """
    processor = DocumentProcessor(chunk_size=chunk_size)
    return processor.process_file(file_path)
