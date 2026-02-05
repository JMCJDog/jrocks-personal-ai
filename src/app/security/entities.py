"""Entity and Identity Data Structures.

Provides flexible, extensible models for representing
entities, identities, and their relationships.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import hashlib
import json


class EntityType(str, Enum):
    """Types of entities in the system."""
    
    PERSON = "person"
    ORGANIZATION = "organization"
    DEVICE = "device"
    SERVICE = "service"
    LOCATION = "location"
    DOCUMENT = "document"
    NETWORK = "network"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence level for data accuracy."""
    
    VERIFIED = "verified"      # Confirmed accurate
    HIGH = "high"              # Very likely accurate
    MEDIUM = "medium"          # Somewhat confident
    LOW = "low"                # Uncertain
    UNVERIFIED = "unverified"  # No verification


class RelationType(str, Enum):
    """Types of relationships between entities."""
    
    OWNS = "owns"
    MEMBER_OF = "member_of"
    LOCATED_AT = "located_at"
    CONNECTED_TO = "connected_to"
    ASSOCIATED_WITH = "associated_with"
    CREATED_BY = "created_by"
    DERIVED_FROM = "derived_from"
    ALIAS_OF = "alias_of"


@dataclass
class Attribute:
    """A single attribute of an entity."""
    
    key: str
    value: Any
    confidence: ConfidenceLevel = ConfidenceLevel.UNVERIFIED
    source: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Identity:
    """A unique identity/identifier for an entity.
    
    Entities can have multiple identities (email, phone, username, etc.)
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "unknown"  # email, phone, username, ip, mac, fingerprint, etc.
    value: str = ""
    verified: bool = False
    primary: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    @property
    def hash(self) -> str:
        """Generate a hash of this identity for matching."""
        data = f"{self.type}:{self.value}".encode()
        return hashlib.sha256(data).hexdigest()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "value": self.value,
            "verified": self.verified,
            "primary": self.primary,
            "hash": self.hash,
        }


@dataclass
class Entity:
    """A flexible entity model for any identifiable object.
    
    Designed to be extended for specific use cases while
    maintaining a consistent structure.
    
    Example:
        >>> entity = Entity(entity_type=EntityType.PERSON)
        >>> entity.add_identity(Identity(type="email", value="..."))
        >>> entity.set_attribute("name", "John Doe", ConfidenceLevel.VERIFIED)
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: EntityType = EntityType.UNKNOWN
    name: Optional[str] = None
    description: Optional[str] = None
    identities: list[Identity] = field(default_factory=list)
    attributes: dict[str, Attribute] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def add_identity(self, identity: Identity) -> None:
        """Add an identity to this entity."""
        self.identities.append(identity)
        self.updated_at = datetime.now()
    
    def get_primary_identity(self) -> Optional[Identity]:
        """Get the primary identity if set."""
        for identity in self.identities:
            if identity.primary:
                return identity
        return self.identities[0] if self.identities else None
    
    def set_attribute(
        self,
        key: str,
        value: Any,
        confidence: ConfidenceLevel = ConfidenceLevel.UNVERIFIED,
        source: Optional[str] = None,
    ) -> None:
        """Set an attribute on this entity."""
        self.attributes[key] = Attribute(
            key=key,
            value=value,
            confidence=confidence,
            source=source,
        )
        self.updated_at = datetime.now()
    
    def get_attribute(self, key: str) -> Optional[Any]:
        """Get an attribute value."""
        attr = self.attributes.get(key)
        return attr.value if attr else None
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to this entity."""
        self.tags.add(tag.lower())
        self.updated_at = datetime.now()
    
    def has_tag(self, tag: str) -> bool:
        """Check if entity has a tag."""
        return tag.lower() in self.tags
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "description": self.description,
            "identities": [i.to_dict() for i in self.identities],
            "attributes": {k: v.to_dict() for k, v in self.attributes.items()},
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        """Create entity from dictionary."""
        entity = cls(
            id=data.get("id", str(uuid.uuid4())),
            entity_type=EntityType(data.get("entity_type", "unknown")),
            name=data.get("name"),
            description=data.get("description"),
        )
        entity.tags = set(data.get("tags", []))
        entity.metadata = data.get("metadata", {})
        return entity


@dataclass
class Relationship:
    """A relationship between two entities."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.ASSOCIATED_WITH
    weight: float = 1.0  # Strength of relationship
    confidence: ConfidenceLevel = ConfidenceLevel.UNVERIFIED
    bidirectional: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "confidence": self.confidence.value,
            "bidirectional": self.bidirectional,
        }


class EntityGraph:
    """Graph structure for managing entities and relationships.
    
    Provides efficient storage and querying of entity networks.
    
    Example:
        >>> graph = EntityGraph()
        >>> graph.add_entity(person)
        >>> graph.add_entity(organization)
        >>> graph.add_relationship(person.id, organization.id, RelationType.MEMBER_OF)
    """
    
    def __init__(self) -> None:
        """Initialize the entity graph."""
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}
        self._adjacency: dict[str, set[str]] = {}  # entity_id -> set of related entity_ids
        self._identity_index: dict[str, str] = {}  # identity_hash -> entity_id
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the graph."""
        self._entities[entity.id] = entity
        self._adjacency[entity.id] = set()
        
        # Index identities
        for identity in entity.identities:
            self._identity_index[identity.hash] = entity.id
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)
    
    def find_by_identity(
        self,
        identity_type: str,
        identity_value: str
    ) -> Optional[Entity]:
        """Find an entity by one of its identities."""
        hash_key = hashlib.sha256(
            f"{identity_type}:{identity_value}".encode()
        ).hexdigest()
        
        entity_id = self._identity_index.get(hash_key)
        if entity_id:
            return self._entities.get(entity_id)
        return None
    
    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        **kwargs
    ) -> Relationship:
        """Add a relationship between entities."""
        rel = Relationship(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            **kwargs
        )
        
        self._relationships[rel.id] = rel
        self._adjacency.setdefault(source_id, set()).add(target_id)
        
        if rel.bidirectional:
            self._adjacency.setdefault(target_id, set()).add(source_id)
        
        return rel
    
    def get_related(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None
    ) -> Iterator[Entity]:
        """Get entities related to the given entity."""
        related_ids = self._adjacency.get(entity_id, set())
        
        for rel_id in related_ids:
            entity = self._entities.get(rel_id)
            if entity:
                yield entity
    
    def get_relationships(self, entity_id: str) -> Iterator[Relationship]:
        """Get all relationships for an entity."""
        for rel in self._relationships.values():
            if rel.source_id == entity_id or rel.target_id == entity_id:
                yield rel
    
    def search_by_type(self, entity_type: EntityType) -> Iterator[Entity]:
        """Find all entities of a given type."""
        for entity in self._entities.values():
            if entity.entity_type == entity_type:
                yield entity
    
    def search_by_tag(self, tag: str) -> Iterator[Entity]:
        """Find all entities with a given tag."""
        tag = tag.lower()
        for entity in self._entities.values():
            if tag in entity.tags:
                yield entity
    
    def search_by_attribute(
        self,
        key: str,
        value: Any,
        exact: bool = True
    ) -> Iterator[Entity]:
        """Find entities by attribute value."""
        for entity in self._entities.values():
            attr = entity.attributes.get(key)
            if attr:
                if exact:
                    if attr.value == value:
                        yield entity
                else:
                    if str(value).lower() in str(attr.value).lower():
                        yield entity
    
    def to_dict(self) -> dict:
        """Export the graph as a dictionary."""
        return {
            "entities": [e.to_dict() for e in self._entities.values()],
            "relationships": [r.to_dict() for r in self._relationships.values()],
        }
    
    @property
    def entity_count(self) -> int:
        return len(self._entities)
    
    @property
    def relationship_count(self) -> int:
        return len(self._relationships)
