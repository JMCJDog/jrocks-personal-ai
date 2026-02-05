"""Audit and Logging Infrastructure.

Provides comprehensive audit logging with:
- Event tracking and correlation
- Secure audit trails
- Real-time event streaming
"""

from typing import Optional, Callable, Iterator, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import json
import hashlib
import asyncio


class EventSeverity(str, Enum):
    """Severity levels for audit events."""
    
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"


class EventCategory(str, Enum):
    """Categories of audit events."""
    
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM = "system"
    SECURITY = "security"
    NETWORK = "network"
    USER_ACTION = "user_action"


@dataclass
class AuditEvent:
    """A single audit log event.
    
    Immutable record of an action or occurrence in the system.
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    severity: EventSeverity = EventSeverity.INFO
    category: EventCategory = EventCategory.SYSTEM
    action: str = ""
    actor_id: Optional[str] = None  # Who performed the action
    target_id: Optional[str] = None  # What was acted upon
    resource: Optional[str] = None  # Resource path/identifier
    outcome: str = "success"  # success, failure, denied, error
    details: dict = field(default_factory=dict)
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None  # For linking related events
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate integrity hash."""
        self._hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute integrity hash of the event."""
        data = f"{self.id}:{self.timestamp.isoformat()}:{self.action}:{self.actor_id}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    @property
    def integrity_hash(self) -> str:
        """Get the integrity hash."""
        return self._hash
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "category": self.category.value,
            "action": self.action,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "resource": self.resource,
            "outcome": self.outcome,
            "details": self.details,
            "source_ip": self.source_ip,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "hash": self.integrity_hash,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> "AuditEvent":
        """Create event from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            severity=EventSeverity(data.get("severity", "info")),
            category=EventCategory(data.get("category", "system")),
            action=data.get("action", ""),
            actor_id=data.get("actor_id"),
            target_id=data.get("target_id"),
            resource=data.get("resource"),
            outcome=data.get("outcome", "success"),
            details=data.get("details", {}),
            source_ip=data.get("source_ip"),
            session_id=data.get("session_id"),
            correlation_id=data.get("correlation_id"),
        )


class AuditLog:
    """Audit log storage and query interface.
    
    Provides tamper-evident logging with query capabilities.
    
    Example:
        >>> log = AuditLog()
        >>> log.record(AuditEvent(action="login", actor_id="user123"))
        >>> events = log.query(actor_id="user123", limit=10)
    """
    
    def __init__(self, storage_path: Optional[str] = None) -> None:
        """Initialize audit log.
        
        Args:
            storage_path: Optional path for persistent storage.
        """
        self.storage_path = storage_path
        self._events: list[AuditEvent] = []
        self._index_by_actor: dict[str, list[int]] = {}
        self._index_by_category: dict[str, list[int]] = {}
        self._subscribers: list[Callable[[AuditEvent], None]] = []
    
    def record(self, event: AuditEvent) -> None:
        """Record an audit event.
        
        Args:
            event: The event to record.
        """
        idx = len(self._events)
        self._events.append(event)
        
        # Update indices
        if event.actor_id:
            self._index_by_actor.setdefault(event.actor_id, []).append(idx)
        self._index_by_category.setdefault(event.category.value, []).append(idx)
        
        # Notify subscribers
        for subscriber in self._subscribers:
            try:
                subscriber(event)
            except Exception:
                pass
    
    def log(
        self,
        action: str,
        severity: EventSeverity = EventSeverity.INFO,
        category: EventCategory = EventCategory.SYSTEM,
        **kwargs
    ) -> AuditEvent:
        """Convenience method to create and record an event.
        
        Args:
            action: The action being logged.
            severity: Event severity.
            category: Event category.
            **kwargs: Additional event fields.
        
        Returns:
            AuditEvent: The recorded event.
        """
        event = AuditEvent(
            action=action,
            severity=severity,
            category=category,
            **kwargs
        )
        self.record(event)
        return event
    
    def query(
        self,
        actor_id: Optional[str] = None,
        category: Optional[EventCategory] = None,
        severity: Optional[EventSeverity] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """Query audit events.
        
        Args:
            actor_id: Filter by actor.
            category: Filter by category.
            severity: Filter by minimum severity.
            start_time: Filter by start time.
            end_time: Filter by end time.
            limit: Maximum results.
            offset: Result offset.
        
        Returns:
            list: Matching events.
        """
        # Start with all events or indexed subset
        if actor_id and actor_id in self._index_by_actor:
            indices = self._index_by_actor[actor_id]
            candidates = [self._events[i] for i in indices]
        elif category and category.value in self._index_by_category:
            indices = self._index_by_category[category.value]
            candidates = [self._events[i] for i in indices]
        else:
            candidates = self._events
        
        # Apply filters
        results = []
        severity_order = list(EventSeverity)
        
        for event in candidates:
            if actor_id and event.actor_id != actor_id:
                continue
            if category and event.category != category:
                continue
            if severity:
                if severity_order.index(event.severity) < severity_order.index(severity):
                    continue
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            results.append(event)
        
        # Apply pagination
        return results[offset:offset + limit]
    
    def subscribe(self, callback: Callable[[AuditEvent], None]) -> None:
        """Subscribe to new events.
        
        Args:
            callback: Function to call on new events.
        """
        self._subscribers.append(callback)
    
    def get_by_correlation(self, correlation_id: str) -> list[AuditEvent]:
        """Get all events with the same correlation ID."""
        return [e for e in self._events if e.correlation_id == correlation_id]
    
    @property
    def event_count(self) -> int:
        return len(self._events)


class AuditStream:
    """Real-time audit event streaming.
    
    Provides async streaming of audit events for real-time monitoring.
    
    Example:
        >>> stream = AuditStream(audit_log)
        >>> async for event in stream.subscribe():
        ...     print(event.action)
    """
    
    def __init__(self, audit_log: Optional[AuditLog] = None) -> None:
        """Initialize audit stream.
        
        Args:
            audit_log: Audit log to stream from.
        """
        self.audit_log = audit_log or AuditLog()
        self._queues: list[asyncio.Queue] = []
        
        # Register with audit log
        self.audit_log.subscribe(self._on_event)
    
    def _on_event(self, event: AuditEvent) -> None:
        """Handle new events from the audit log."""
        for queue in self._queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass
    
    async def subscribe(
        self,
        filter_severity: Optional[EventSeverity] = None,
        filter_category: Optional[EventCategory] = None,
    ) -> Iterator[AuditEvent]:
        """Subscribe to the event stream.
        
        Args:
            filter_severity: Only receive events of this severity or higher.
            filter_category: Only receive events of this category.
        
        Yields:
            AuditEvent: Events as they occur.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._queues.append(queue)
        
        severity_order = list(EventSeverity)
        
        try:
            while True:
                event = await queue.get()
                
                # Apply filters
                if filter_severity:
                    if severity_order.index(event.severity) < severity_order.index(filter_severity):
                        continue
                if filter_category and event.category != filter_category:
                    continue
                
                yield event
        finally:
            self._queues.remove(queue)
    
    def emit(self, event: AuditEvent) -> None:
        """Emit an event to the stream.
        
        Args:
            event: Event to emit.
        """
        self.audit_log.record(event)
