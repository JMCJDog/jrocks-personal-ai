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

    def _get_new_commands(self, current_content: str) -> list[str]:
        """Extract new commands from content diff.
        
        Simple logic: Look for lines that don't start with "[Done]" or "[Processing]"
        and weren't in the last content.
        
        For reliability in this v1, we'll just look for the LAST line that isn't empty
        and isn't marked as processed.
        """
        lines = [line.strip() for line in current_content.split('\n') if line.strip()]
        
        new_commands = []
        for line in lines:
            # Skip processed lines
            if line.startswith("[") and "]" in line:
                continue
                
            # If we haven't seen this content before (naive check)
            # A better way is to rely on the agent to mark it DONE in the doc.
            # But we can't write back to the doc easily with current Provider (it's read-focused).
            # So we will rely on local memory of what we've processed if write-back isn't ready.
            
            # Actually, to make this usable without write-back:
            # We only process the LAST line if it matches a "Command pattern" 
            # or just treat all non-processed lines as new?
            
            # Let's assume we will implement write-back or just log it for now.
            new_commands.append(line)
            
        return new_commands

    def _update_doc_status(self, command: str, result: str):
        """Append status to the doc.
        
        NOTE: GoogleDriveProvider currently supports READ-ONLY.
        We need to extend it or use a raw service call here for write-back.
        """
        # TODO: Implement append logic in GoogleDriveProvider
        logger.info(f"Would append to doc: [Done] {command} -> {result}")
        # self.provider.append_text(self.doc_id, f"\n[Done] {result}")

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
                        
                        # Diff logic
                        # This is tricky without strict structure. 
                        # We'll cheat: look for "COMMAND: " prefix or just take the huge diff?
                        # Let's just find lines present NOW that weren't BEFORE.
                        old_lines = set(self.last_content.split('\n'))
                        new_lines = set(current_content.split('\n'))
                        
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
