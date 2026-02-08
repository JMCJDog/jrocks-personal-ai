import mailbox
import email
from pathlib import Path
from typing import Optional, List, Generator
from bs4 import BeautifulSoup
import logging
from datetime import datetime

from ..document_processor import ProcessedDocument, DocumentProcessor

logger = logging.getLogger(__name__)

class MailboxProvider:
    """Provider for ingesting .mbox files (e.g. Google Takeout)."""

    def __init__(
        self, 
        mbox_path: str,
        user_email: str = "jared", # targeted via command line usually
        doc_processor: Optional[DocumentProcessor] = None
    ):
        self.mbox_path = Path(mbox_path)
        self.user_email = user_email
        self.doc_processor = doc_processor or DocumentProcessor()
        self.style_corpus_path = Path("data/jrock_style_corpus.txt")
        self.style_corpus_path.parent.mkdir(parents=True, exist_ok=True)

    def process_mailbox(self, limit: int = 0) -> dict:
        """Process the mailbox.
        
        Args:
            limit: Max messages to process. 0 for all.
            
        Returns:
            Stats dict.
        """
        if not self.mbox_path.exists():
            raise FileNotFoundError(f"Mbox file not found: {self.mbox_path}")

        logger.info(f"Opening mailbox: {self.mbox_path}...")
        mbox = mailbox.mbox(str(self.mbox_path))
        
        stats = {
            "total": 0,
            "processed": 0,
            "sent_by_me": 0,
            "errors": 0
        }
        
        # Open style corpus in append mode
        with open(self.style_corpus_path, "a", encoding="utf-8") as f_style:
            for i, message in enumerate(mbox):
                if limit and i >= limit:
                    break
                    
                stats["total"] += 1
                try:
                    content, metadata = self._extract_content(message)
                    
                    if not content.strip():
                        continue

                    # Check if sent by user
                    from_header = metadata.get("from", "").lower()
                    if self.user_email.lower() in from_header:
                        stats["sent_by_me"] += 1
                        # Save to corpus
                        f_style.write(f"--- Email: {metadata.get('subject')} ---\n")
                        f_style.write(content + "\n\n")

                    # Convert to ProcessedDocument for RAG
                    # We'll return these or yield them? 
                    # For now just let's assume we want to do something with them.
                    # The EmbeddingPipeline needs them. 
                    # But here we act as a Provider. 
                    # Ideally we yield documents.
                    
                    stats["processed"] += 1
                    if i % 100 == 0:
                        print(f"Processed {i} emails...")
                        
                except Exception as e:
                    logger.error(f"Error processing message {i}: {e}")
                    stats["errors"] += 1

        return stats

    def yield_documents(self, limit: int = 0) -> Generator[ProcessedDocument, None, None]:
        """Yield processed documents for RAG."""
        if not self.mbox_path.exists():
            return

        mbox = mailbox.mbox(str(self.mbox_path))
        count = 0
        
        for message in mbox:
            try:
                content, metadata = self._extract_content(message)
                if not content.strip():
                    continue

                doc = self.doc_processor.process_text(
                    text=content,
                    source_name=f"email_{metadata.get('date_str')}"
                )
                
                doc.metadata.update(metadata)
                doc.metadata["type"] = "email"
                
                yield doc
                
                count += 1
                if limit and count >= limit:
                    break
            except Exception:
                continue

    def _extract_content(self, message) -> tuple[str, dict]:
        """Extract text content and metadata from a message."""
        subject = message.get("subject", "No Subject")
        from_ = message.get("from", "Unknown")
        to = message.get("to", "Unknown")
        date = message.get("date", "")
        
        body = ""
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode(errors="ignore")
                    except:
                        pass
                elif content_type == "text/html":
                    try:
                        html = part.get_payload(decode=True).decode(errors="ignore")
                        soup = BeautifulSoup(html, "html.parser")
                        body += soup.get_text(separator="\n")
                    except:
                        pass
        else:
            try:
                body = message.get_payload(decode=True).decode(errors="ignore")
            except:
                pass
                
        # Clean body
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        cleaned_body = "\n".join(lines)
        
        metadata = {
            "subject": subject,
            "from": from_,
            "to": to,
            "date_str": date,
            "content_length": len(cleaned_body)
        }
        
        return cleaned_body, metadata
