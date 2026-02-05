"""Configuration models for chat history sync.

Defines settings for sync behavior, provider-specific options,
and schedule configurations.
"""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SyncFrequency(str, Enum):
    """Sync frequency options."""
    
    MANUAL = "manual"        # Only sync on demand
    HOURLY = "hourly"        # Every hour
    DAILY = "daily"          # Once per day
    REALTIME = "realtime"    # Watch folder for changes


class ProviderSyncSettings(BaseModel):
    """Settings for a specific provider's sync behavior.
    
    Attributes:
        enabled: Whether sync is enabled for this provider
        watch_paths: Directories to watch for new exports
        frequency: How often to check for new exports
        file_patterns: Glob patterns to match export files
        auto_delete: Whether to delete source files after processing
        metadata: Additional provider-specific settings
    """
    
    enabled: bool = True
    watch_paths: list[Path] = Field(default_factory=list)
    frequency: SyncFrequency = SyncFrequency.MANUAL
    file_patterns: list[str] = Field(default_factory=lambda: ["*.zip", "*.json"])
    auto_delete: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SyncConfig(BaseModel):
    """Global sync configuration.
    
    Attributes:
        default_watch_path: Default folder to watch for all providers
        processed_folder: Where to move processed files
        failed_folder: Where to move failed files
        enable_file_watcher: Whether to use file system watching
        providers: Per-provider settings
        dedup_strategy: How to handle duplicate conversations
        retention_days: How long to keep processed file records
    """
    
    # Paths
    default_watch_path: Path = Field(
        default_factory=lambda: Path.home() / "Documents" / "AI-Exports"
    )
    processed_folder: Path = Field(
        default_factory=lambda: Path.home() / "Documents" / "AI-Exports" / ".processed"
    )
    failed_folder: Path = Field(
        default_factory=lambda: Path.home() / "Documents" / "AI-Exports" / ".failed"
    )
    
    # Behavior
    enable_file_watcher: bool = True
    dedup_strategy: str = "update"  # "update", "skip", "keep_all"
    retention_days: int = 30
    
    # Provider-specific settings
    providers: dict[str, ProviderSyncSettings] = Field(default_factory=dict)
    
    def get_provider_settings(self, provider: str) -> ProviderSyncSettings:
        """Get settings for a specific provider, with defaults."""
        if provider not in self.providers:
            self.providers[provider] = ProviderSyncSettings(
                watch_paths=[self.default_watch_path / provider]
            )
        return self.providers[provider]
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.default_watch_path.mkdir(parents=True, exist_ok=True)
        self.processed_folder.mkdir(parents=True, exist_ok=True)
        self.failed_folder.mkdir(parents=True, exist_ok=True)
        
        for provider, settings in self.providers.items():
            for watch_path in settings.watch_paths:
                watch_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def default(cls) -> "SyncConfig":
        """Create default configuration with all providers enabled."""
        config = cls()
        
        # Set up default provider configurations
        config.providers["openai"] = ProviderSyncSettings(
            watch_paths=[config.default_watch_path / "openai"],
            file_patterns=["*.zip", "conversations.json"],
        )
        config.providers["anthropic"] = ProviderSyncSettings(
            watch_paths=[config.default_watch_path / "anthropic"],
            file_patterns=["*.zip", "*.json"],
        )
        config.providers["google"] = ProviderSyncSettings(
            watch_paths=[config.default_watch_path / "google"],
            file_patterns=["*.zip", "takeout-*.zip"],
        )
        config.providers["ollama"] = ProviderSyncSettings(
            watch_paths=[config.default_watch_path / "ollama"],
            file_patterns=["*.json", "*.jsonl"],
        )
        
        return config
