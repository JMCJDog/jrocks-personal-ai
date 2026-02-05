"""Access Control and Permissions.

Provides role-based and policy-based access control:
- Fine-grained permissions
- Role hierarchies
- Policy evaluation
"""

from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import fnmatch


class PermissionAction(str, Enum):
    """Standard permission actions."""
    
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    ALL = "*"


@dataclass
class Permission:
    """A single permission grant.
    
    Permissions are defined as resource + action combinations.
    
    Example:
        >>> perm = Permission(resource="documents/*", action=PermissionAction.READ)
        >>> perm.matches("documents/report.pdf", PermissionAction.READ)
        True
    """
    
    resource: str  # Resource pattern (supports wildcards)
    action: PermissionAction
    conditions: dict = field(default_factory=dict)  # Optional conditions
    granted: bool = True  # True = allow, False = deny
    
    def matches(self, resource: str, action: PermissionAction) -> bool:
        """Check if this permission matches a resource/action pair.
        
        Args:
            resource: Resource to check.
            action: Action to check.
        
        Returns:
            bool: True if matches.
        """
        # Check action
        if self.action != PermissionAction.ALL and self.action != action:
            return False
        
        # Check resource pattern
        return fnmatch.fnmatch(resource, self.resource)
    
    def to_dict(self) -> dict:
        return {
            "resource": self.resource,
            "action": self.action.value,
            "conditions": self.conditions,
            "granted": self.granted,
        }


@dataclass
class Role:
    """A role with a set of permissions.
    
    Roles group permissions together for easier management.
    Supports role inheritance.
    
    Example:
        >>> admin = Role(name="admin")
        >>> admin.add_permission(Permission("*", PermissionAction.ALL))
    """
    
    name: str
    description: Optional[str] = None
    permissions: list[Permission] = field(default_factory=list)
    inherits: list[str] = field(default_factory=list)  # Parent role names
    metadata: dict = field(default_factory=dict)
    
    def add_permission(self, permission: Permission) -> None:
        """Add a permission to this role."""
        self.permissions.append(permission)
    
    def remove_permission(self, resource: str, action: PermissionAction) -> bool:
        """Remove a permission from this role."""
        for i, perm in enumerate(self.permissions):
            if perm.resource == resource and perm.action == action:
                self.permissions.pop(i)
                return True
        return False
    
    def has_permission(self, resource: str, action: PermissionAction) -> bool:
        """Check if this role has a permission (not considering inheritance)."""
        for perm in self.permissions:
            if perm.matches(resource, action) and perm.granted:
                return True
        return False
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "permissions": [p.to_dict() for p in self.permissions],
            "inherits": self.inherits,
        }


@dataclass
class AccessPolicy:
    """An access policy for decision-making.
    
    Policies can include custom evaluation logic beyond
    simple permission matching.
    """
    
    name: str
    description: Optional[str] = None
    priority: int = 0  # Higher = evaluated first
    condition: Optional[Callable[[dict], bool]] = None
    effect: str = "allow"  # allow or deny
    resources: list[str] = field(default_factory=list)
    actions: list[PermissionAction] = field(default_factory=list)
    
    def evaluate(self, context: dict) -> Optional[bool]:
        """Evaluate this policy against a context.
        
        Args:
            context: Evaluation context with resource, action, subject info.
        
        Returns:
            bool or None: True=allow, False=deny, None=not applicable.
        """
        resource = context.get("resource", "")
        action = context.get("action")
        
        # Check if policy applies to this resource
        resource_match = False
        for pattern in self.resources:
            if fnmatch.fnmatch(resource, pattern):
                resource_match = True
                break
        
        if not resource_match and self.resources:
            return None
        
        # Check if policy applies to this action
        if self.actions and action not in self.actions:
            return None
        
        # Evaluate custom condition
        if self.condition:
            try:
                if not self.condition(context):
                    return None
            except Exception:
                return None
        
        return self.effect == "allow"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "priority": self.priority,
            "effect": self.effect,
            "resources": self.resources,
            "actions": [a.value for a in self.actions],
        }


class AccessController:
    """Central access control manager.
    
    Evaluates permissions and policies to make access decisions.
    
    Example:
        >>> controller = AccessController()
        >>> controller.add_role(admin_role)
        >>> controller.assign_role("user123", "admin")
        >>> controller.is_allowed("user123", "settings", PermissionAction.UPDATE)
        True
    """
    
    def __init__(self) -> None:
        """Initialize access controller."""
        self._roles: dict[str, Role] = {}
        self._policies: list[AccessPolicy] = []
        self._subject_roles: dict[str, set[str]] = {}  # subject_id -> role names
    
    def add_role(self, role: Role) -> None:
        """Register a role.
        
        Args:
            role: Role to add.
        """
        self._roles[role.name] = role
    
    def get_role(self, name: str) -> Optional[Role]:
        """Get a role by name."""
        return self._roles.get(name)
    
    def add_policy(self, policy: AccessPolicy) -> None:
        """Add an access policy.
        
        Args:
            policy: Policy to add.
        """
        self._policies.append(policy)
        self._policies.sort(key=lambda p: -p.priority)
    
    def assign_role(self, subject_id: str, role_name: str) -> bool:
        """Assign a role to a subject.
        
        Args:
            subject_id: Subject identifier.
            role_name: Role to assign.
        
        Returns:
            bool: True if successful.
        """
        if role_name not in self._roles:
            return False
        
        self._subject_roles.setdefault(subject_id, set()).add(role_name)
        return True
    
    def revoke_role(self, subject_id: str, role_name: str) -> bool:
        """Remove a role from a subject."""
        if subject_id in self._subject_roles:
            self._subject_roles[subject_id].discard(role_name)
            return True
        return False
    
    def get_roles(self, subject_id: str) -> set[str]:
        """Get all roles for a subject."""
        return self._subject_roles.get(subject_id, set())
    
    def _get_effective_roles(self, role_name: str) -> set[str]:
        """Get a role and all its inherited roles."""
        roles = {role_name}
        role = self._roles.get(role_name)
        
        if role:
            for parent in role.inherits:
                roles.update(self._get_effective_roles(parent))
        
        return roles
    
    def is_allowed(
        self,
        subject_id: str,
        resource: str,
        action: PermissionAction,
        context: Optional[dict] = None,
    ) -> bool:
        """Check if a subject is allowed to perform an action.
        
        Args:
            subject_id: Subject identifier.
            resource: Resource being accessed.
            action: Action being performed.
            context: Additional context for policy evaluation.
        
        Returns:
            bool: True if allowed.
        """
        eval_context = {
            "subject_id": subject_id,
            "resource": resource,
            "action": action,
            **(context or {}),
        }
        
        # Check policies first (they have priority)
        for policy in self._policies:
            result = policy.evaluate(eval_context)
            if result is not None:
                return result
        
        # Check role permissions
        subject_roles = self._subject_roles.get(subject_id, set())
        
        for role_name in subject_roles:
            effective_roles = self._get_effective_roles(role_name)
            
            for eff_role_name in effective_roles:
                role = self._roles.get(eff_role_name)
                if role and role.has_permission(resource, action):
                    return True
        
        return False
    
    def check_permission(
        self,
        subject_id: str,
        resource: str,
        action: PermissionAction,
    ) -> None:
        """Check permission and raise if denied.
        
        Args:
            subject_id: Subject identifier.
            resource: Resource being accessed.
            action: Action being performed.
        
        Raises:
            PermissionError: If access is denied.
        """
        if not self.is_allowed(subject_id, resource, action):
            raise PermissionError(
                f"Access denied: {subject_id} cannot {action.value} on {resource}"
            )


# Default role definitions
def create_default_roles() -> dict[str, Role]:
    """Create standard default roles."""
    
    admin = Role(
        name="admin",
        description="Full system access",
        permissions=[
            Permission("*", PermissionAction.ALL),
        ]
    )
    
    user = Role(
        name="user",
        description="Standard user access",
        permissions=[
            Permission("profile/*", PermissionAction.READ),
            Permission("profile/*", PermissionAction.UPDATE),
            Permission("documents/*", PermissionAction.READ),
        ]
    )
    
    guest = Role(
        name="guest",
        description="Limited read-only access",
        permissions=[
            Permission("public/*", PermissionAction.READ),
        ]
    )
    
    return {
        "admin": admin,
        "user": user,
        "guest": guest,
    }
