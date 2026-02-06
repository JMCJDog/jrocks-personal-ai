"""Core module for JRock's Personal AI.

Contains the SLM engine, persona definition, and consciousness state management.
"""

from .state_persistence import (
    WorkflowCheckpoint, StateStore, FileStateStore,
    CheckpointManager, get_default_store,
)
from .observability import (
    SpanContext, trace_span, traced, AgentMetrics,
    MetricsCollector, EventLogger, get_metrics_collector,
    configure_logging,
)

__all__ = [
    # State Persistence
    "WorkflowCheckpoint",
    "StateStore",
    "FileStateStore",
    "CheckpointManager",
    "get_default_store",
    
    # Observability
    "SpanContext",
    "trace_span",
    "traced",
    "AgentMetrics",
    "MetricsCollector",
    "EventLogger",
    "get_metrics_collector",
    "configure_logging",
]
