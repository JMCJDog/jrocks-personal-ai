"""Security and Identity Infrastructure.

Provides extensible data structures for:
- Entity/identity management
- Audit and monitoring
- Access control
- Threat detection patterns
"""

from .entities import (
    Entity,
    Identity,
    EntityType,
    Relationship,
    EntityGraph,
)
from .audit import (
    AuditEvent,
    AuditLog,
    EventSeverity,
    AuditStream,
)
from .access import (
    Permission,
    Role,
    AccessPolicy,
    AccessController,
)
from .monitoring import (
    Observer,
    ObservationEvent,
    PatternMatcher,
    AlertRule,
    MonitoringService,
)


__all__ = [
    # Entities
    "Entity",
    "Identity",
    "EntityType",
    "Relationship",
    "EntityGraph",
    
    # Audit
    "AuditEvent",
    "AuditLog",
    "EventSeverity",
    "AuditStream",
    
    # Access
    "Permission",
    "Role",
    "AccessPolicy",
    "AccessController",
    
    # Monitoring
    "Observer",
    "ObservationEvent",
    "PatternMatcher",
    "AlertRule",
    "MonitoringService",
]
