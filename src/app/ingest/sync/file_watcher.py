"""File system watcher for detecting new chat exports.

Uses watchdog library to monitor directories for new export files
and routes them to the appropriate provider for processing.
"""

import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, Field

from ..providers import (
    AnthropicProvider,
    ChatConversation,
    ChatHistoryProvider,
    GoogleProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderType,
)
from .sync_config import SyncConfig

logger = logging.getLogger(__name__)


class WatcherConfig(BaseModel):
    """Configuration for file watcher behavior.
    
    Attributes:
        debounce_seconds: Wait time before processing (for multi-file writes)
        recursive: Whether to watch subdirectories
        poll_interval: Fallback polling interval in seconds
    """
    
    debounce_seconds: float = 2.0
    recursive: bool = True
    poll_interval: float = 1.0


class ProcessingResult(BaseModel):
    """Result of processing a single file."""
    
    success: bool
    file_path: Path
    provider: ProviderType | None = None
    conversations_count: int = 0
    error: str | None = None
    processed_at: datetime = Field(default_factory=datetime.now)


class FileWatcher:
    """Watches directories for new chat export files.
    
    Monitors configured directories and automatically detects
    which provider should handle each file based on content.
    """
    
    def __init__(
        self,
        sync_config: SyncConfig,
        watcher_config: WatcherConfig | None = None,
        on_process: Callable[[list[ChatConversation]], None] | None = None,
    ):
        """Initialize the file watcher.
        
        Args:
            sync_config: Sync configuration with paths
            watcher_config: Watcher-specific configuration
            on_process: Callback for processed conversations
        """
        self.sync_config = sync_config
        self.watcher_config = watcher_config or WatcherConfig()
        self.on_process = on_process
        
        # Initialize providers
        self._providers: list[ChatHistoryProvider] = [
            OpenAIProvider(),
            AnthropicProvider(),
            GoogleProvider(),
            OllamaProvider(),
        ]
        
        self._running = False
        self._processed_files: set[Path] = set()
    
    def detect_provider(self, path: Path) -> ChatHistoryProvider | None:
        """Detect which provider can handle a file.
        
        Args:
            path: Path to the file
            
        Returns:
            The matching provider, or None if no match
        """
        for provider in self._providers:
            if provider.can_parse(path):
                return provider
        return None
    
    def process_file(self, path: Path) -> ProcessingResult:
        """Process a single export file.
        
        Args:
            path: Path to the export file
            
        Returns:
            ProcessingResult with status and details
        """
        try:
            provider = self.detect_provider(path)
            if not provider:
                return ProcessingResult(
                    success=False,
                    file_path=path,
                    error="No provider found for this file format",
                )
            
            logger.info(f"Processing {path} with {provider.provider_type.value} provider")
            
            conversations = provider.parse(path)
            
            if self.on_process:
                self.on_process(conversations)
            
            # Move to processed folder
            self._move_to_processed(path)
            self._processed_files.add(path)
            
            return ProcessingResult(
                success=True,
                file_path=path,
                provider=provider.provider_type,
                conversations_count=len(conversations),
            )
            
        except Exception as e:
            logger.error(f"Error processing {path}: {e}")
            self._move_to_failed(path)
            return ProcessingResult(
                success=False,
                file_path=path,
                error=str(e),
            )
    
    def scan_directory(self, directory: Path) -> list[ProcessingResult]:
        """Scan a directory for unprocessed export files.
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of processing results
        """
        results = []
        
        if not directory.exists():
            logger.warning(f"Watch directory does not exist: {directory}")
            return results
        
        patterns = ["*.zip", "*.json", "*.jsonl"]
        
        for pattern in patterns:
            if self.watcher_config.recursive:
                files = directory.rglob(pattern)
            else:
                files = directory.glob(pattern)
            
            for file_path in files:
                if file_path in self._processed_files:
                    continue
                if ".processed" in str(file_path) or ".failed" in str(file_path):
                    continue
                
                result = self.process_file(file_path)
                results.append(result)
        
        return results
    
    def scan_all(self) -> list[ProcessingResult]:
        """Scan all configured watch directories.
        
        Returns:
            Combined list of processing results
        """
        all_results = []
        
        # Scan default watch path
        results = self.scan_directory(self.sync_config.default_watch_path)
        all_results.extend(results)
        
        # Scan provider-specific paths
        for provider_name, settings in self.sync_config.providers.items():
            if not settings.enabled:
                continue
            
            for watch_path in settings.watch_paths:
                results = self.scan_directory(watch_path)
                all_results.extend(results)
        
        return all_results
    
    async def start(self) -> None:
        """Start watching directories for changes.
        
        This uses polling mode for cross-platform compatibility.
        For real-time watching, consider using watchdog library.
        """
        self._running = True
        logger.info("Starting file watcher...")
        
        # Ensure directories exist
        self.sync_config.ensure_directories()
        
        while self._running:
            results = self.scan_all()
            
            for result in results:
                if result.success:
                    logger.info(
                        f"Processed {result.file_path.name}: "
                        f"{result.conversations_count} conversations"
                    )
            
            await asyncio.sleep(self.watcher_config.poll_interval)
    
    def stop(self) -> None:
        """Stop watching directories."""
        self._running = False
        logger.info("Stopping file watcher...")
    
    def _move_to_processed(self, path: Path) -> None:
        """Move a successfully processed file to the processed folder."""
        if self.sync_config.providers.get(
            self.detect_provider(path).provider_type.value if self.detect_provider(path) else "",
            {}
        ):
            dest = self.sync_config.processed_folder / path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(dest))
    
    def _move_to_failed(self, path: Path) -> None:
        """Move a failed file to the failed folder."""
        dest = self.sync_config.failed_folder / path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))
