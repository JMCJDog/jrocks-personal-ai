"""Feedback Watcher - Polls Google Docs for Vibe Coding commands.

Monitors a specific Google Doc for new natural language commands,
executes them using the CodeAgent/Orchestrator, and updates the doc with status.
"""

import time
import logging
import os
from typing import Optional, Callable
from datetime import datetime

from .google_drive_provider import GoogleDriveProvider
# We'll need to import the orchestrator or code agent dynamically
# to avoid circular imports if they use providers

logger = logging.getLogger(__name__)

class FeedbackWatcher:
    """Watches a Google Doc for feedback commands."""

    RESPONSE_START = ">>> VIBE AGENT RESPONSE >>>"
    RESPONSE_END = "<<< END RESPONSE <<<"

    def __init__(
        self,
        doc_name: str = "Vibe Coding Feedback",
        poll_interval: int = 30,
        provider: Optional[GoogleDriveProvider] = None,
        on_command: Optional[Callable[[str], str]] = None
    ) -> None:
        """Initialize the watcher.
        
        Args:
            doc_name: Name of the Google Doc to watch.
            poll_interval: Seconds between checks.
            provider: GoogleDriveProvider instance.
            on_command: Callback function(command) -> result_message.
        """
        self.doc_name = doc_name
        self.poll_interval = poll_interval
        self.provider = provider or GoogleDriveProvider()
        self.on_command = on_command
        self.doc_id: Optional[str] = None
        self.last_content: str = ""
        self.running = False
        
    def find_or_create_doc(self) -> str:
        """Find the feedback doc or create one (creation not impl in provider yet)."""
        # Search for existing doc
        files = self.provider.search_files(
            query=f"name = '{self.doc_name}' and mimeType = 'application/vnd.google-apps.document' and trashed = false",
            limit=1
        )
        
        if files:
            logger.info(f"Found existing feedback doc: {files[0]['name']} ({files[0]['id']})")
            return files[0]['id']
        
        raise FileNotFoundError(f"Could not find Google Doc named '{self.doc_name}'. Please create it manually.")

    def _remove_system_blocks(self, text: str) -> str:
        """Remove all content between system response markers."""
        while self.RESPONSE_START in text and self.RESPONSE_END in text:
            start_idx = text.find(self.RESPONSE_START)
            end_idx = text.find(self.RESPONSE_END) + len(self.RESPONSE_END)
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                # Remove the block
                text = text[:start_idx] + text[end_idx:]
            else:
                break
        return text

    def _update_doc_status(self, command: str, result: str):
        """Append status to the doc with markers."""
        # Implement append logic in GoogleDriveProvider
        logger.info(f"Would append to doc: [Done] {command} -> {result}")
        try:
            formatted_response = (
                f"\n\n{self.RESPONSE_START}\n"
                f"[Done] {command}\n"
                f"Result:\n{result}\n"
                f"{self.RESPONSE_END}\n"
            )
            self.provider.append_text(self.doc_id, formatted_response)
        except Exception as e:
            logger.error(f"Failed to write back to doc: {e}")

    def start(self):
        """Start the polling loop."""
        self.running = True
        logger.info(f"Starting Vibe Feedback Watcher for '{self.doc_name}'...")
        
        try:
            self.doc_id = self.find_or_create_doc()
            
            # Initial read
            self.last_content = self.provider.download_file(
                self.doc_id, 
                "application/vnd.google-apps.document"
            )
            logger.info("Initial sync complete. Waiting for commands...")
            
            while self.running:
                try:
                    current_content = self.provider.download_file(
                        self.doc_id,
                        "application/vnd.google-apps.document"
                    )
                    
                    if current_content != self.last_content:
                        logger.info("Change detected in document!")
                        
                        # CLEAN Diff logic:
                        # 1. Remove all system response blocks from BOTH current and last content (if needed)
                        # Actually, we just need to ignore system blocks in the NEW content to find user commands.
                        # But to compare apples to apples, let's clean both.
                        
                        clean_current = self._remove_system_blocks(current_content)
                        clean_last = self._remove_system_blocks(self.last_content)
                        
                        old_lines = set(clean_last.split('\n'))
                        new_lines = set(clean_current.split('\n'))
                        
                        added_lines = list(new_lines - old_lines)
                        
                        for cmd in added_lines:
                            cmd = cmd.strip()
                            if not cmd: continue
                            
                            logger.info(f"New command found: {cmd}")
                            
                            if self.on_command:
                                result = self.on_command(cmd)
                                self._update_doc_status(cmd, result)
                        
                        self.last_content = current_content
                        
                except Exception as e:
                    logger.error(f"Error in poll loop: {e}")
                    
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Stopping watcher...")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
