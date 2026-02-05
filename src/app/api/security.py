"""Security API Router - Endpoints for security infrastructure.

Provides REST API access to entities, audit logs, and monitoring.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime


# Request/Response Models
class EntityCreateRequest(BaseModel):
    """Create entity request."""
    entity_type: str = Field(default="unknown")
    name: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class EntityResponse(BaseModel):
    """Entity response."""
    id: str
    entity_type: str
    name: Optional[str]
    identities: list[dict] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class IdentityAddRequest(BaseModel):
    """Add identity request."""
    entity_id: str
    identity_type: str
    value: str
    primary: bool = False


class AuditLogRequest(BaseModel):
    """Log event request."""
    action: str
    severity: str = "info"
    category: str = "system"
    actor_id: Optional[str] = None
    target_id: Optional[str] = None
    details: dict = Field(default_factory=dict)


class AuditQueryRequest(BaseModel):
    """Query audit events."""
    actor_id: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    limit: int = 100


class AlertListResponse(BaseModel):
    """List of alerts."""
    alerts: list[dict]
    total: int


class GraphStatsResponse(BaseModel):
    """Entity graph statistics."""
    entity_count: int
    relationship_count: int
    entities_by_type: dict[str, int]


# Create router
router = APIRouter(prefix="/api/security", tags=["security"])


# Lazy-loaded services
_entity_graph = None
_audit_log = None
_monitoring = None


def get_entity_graph():
    """Get or create entity graph."""
    global _entity_graph
    if _entity_graph is None:
        from ..security.entities import EntityGraph
        _entity_graph = EntityGraph()
    return _entity_graph


def get_audit_log():
    """Get or create audit log."""
    global _audit_log
    if _audit_log is None:
        from ..security.audit import AuditLog
        _audit_log = AuditLog()
    return _audit_log


def get_monitoring():
    """Get or create monitoring service."""
    global _monitoring
    if _monitoring is None:
        from ..security.monitoring import MonitoringService
        _monitoring = MonitoringService()
    return _monitoring


# Entity endpoints
@router.post("/entities", response_model=EntityResponse)
async def create_entity(request: EntityCreateRequest):
    """Create a new entity."""
    from ..security.entities import Entity, EntityType
    
    graph = get_entity_graph()
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        entity_type = EntityType.UNKNOWN
    
    entity = Entity(
        entity_type=entity_type,
        name=request.name,
        description=request.description,
    )
    for tag in request.tags:
        entity.add_tag(tag)
    
    graph.add_entity(entity)
    
    # Log the creation
    audit = get_audit_log()
    audit.log(
        action="entity.create",
        target_id=entity.id,
        details={"entity_type": entity_type.value},
    )
    
    return EntityResponse(
        id=entity.id,
        entity_type=entity.entity_type.value,
        name=entity.name,
        identities=[],
        tags=list(entity.tags),
    )


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: str):
    """Get an entity by ID."""
    graph = get_entity_graph()
    entity = graph.get_entity(entity_id)
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return EntityResponse(
        id=entity.id,
        entity_type=entity.entity_type.value,
        name=entity.name,
        identities=[i.to_dict() for i in entity.identities],
        tags=list(entity.tags),
    )


@router.post("/entities/identity")
async def add_identity(request: IdentityAddRequest):
    """Add an identity to an entity."""
    from ..security.entities import Identity
    
    graph = get_entity_graph()
    entity = graph.get_entity(request.entity_id)
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    identity = Identity(
        type=request.identity_type,
        value=request.value,
        primary=request.primary,
    )
    entity.add_identity(identity)
    
    return {"status": "ok", "identity_id": identity.id}


@router.get("/entities/search")
async def search_entities(
    entity_type: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 50,
):
    """Search for entities."""
    from ..security.entities import EntityType
    
    graph = get_entity_graph()
    results = []
    
    if entity_type:
        try:
            et = EntityType(entity_type)
            for entity in graph.search_by_type(et):
                results.append(entity.to_dict())
                if len(results) >= limit:
                    break
        except ValueError:
            pass
    elif tag:
        for entity in graph.search_by_tag(tag):
            results.append(entity.to_dict())
            if len(results) >= limit:
                break
    
    return {"entities": results, "count": len(results)}


@router.get("/graph/stats", response_model=GraphStatsResponse)
async def get_graph_stats():
    """Get entity graph statistics."""
    from ..security.entities import EntityType
    
    graph = get_entity_graph()
    
    by_type = {}
    for et in EntityType:
        count = sum(1 for _ in graph.search_by_type(et))
        if count > 0:
            by_type[et.value] = count
    
    return GraphStatsResponse(
        entity_count=graph.entity_count,
        relationship_count=graph.relationship_count,
        entities_by_type=by_type,
    )


# Audit endpoints
@router.post("/audit/log")
async def log_event(request: AuditLogRequest):
    """Log an audit event."""
    from ..security.audit import EventSeverity, EventCategory
    
    audit = get_audit_log()
    
    try:
        severity = EventSeverity(request.severity)
    except ValueError:
        severity = EventSeverity.INFO
    
    try:
        category = EventCategory(request.category)
    except ValueError:
        category = EventCategory.SYSTEM
    
    event = audit.log(
        action=request.action,
        severity=severity,
        category=category,
        actor_id=request.actor_id,
        target_id=request.target_id,
        details=request.details,
    )
    
    return {"status": "ok", "event_id": event.id}


@router.get("/audit/events")
async def query_events(
    actor_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
):
    """Query audit events."""
    from ..security.audit import EventCategory
    
    audit = get_audit_log()
    
    cat = None
    if category:
        try:
            cat = EventCategory(category)
        except ValueError:
            pass
    
    events = audit.query(actor_id=actor_id, category=cat, limit=limit)
    
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events),
    }


# Monitoring endpoints
@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
):
    """List monitoring alerts."""
    from ..security.monitoring import AlertStatus, AlertSeverity
    
    monitoring = get_monitoring()
    
    st = None
    if status:
        try:
            st = AlertStatus(status)
        except ValueError:
            pass
    
    sev = None
    if severity:
        try:
            sev = AlertSeverity(severity)
        except ValueError:
            pass
    
    alerts = monitoring.get_alerts(status=st, severity=sev, limit=limit)
    
    return AlertListResponse(
        alerts=[a.to_dict() for a in alerts],
        total=len(alerts),
    )


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, by: Optional[str] = None):
    """Acknowledge an alert."""
    monitoring = get_monitoring()
    
    for alert in monitoring._alerts:
        if alert.id == alert_id:
            alert.acknowledge(by)
            return {"status": "acknowledged"}
    
    raise HTTPException(status_code=404, detail="Alert not found")


@router.get("/monitoring/stats")
async def monitoring_stats():
    """Get monitoring statistics."""
    monitoring = get_monitoring()
    
    return {
        "total_alerts": monitoring.alert_count,
        "active_alerts": monitoring.active_alert_count,
        "rules_count": len(monitoring._rules),
    }
