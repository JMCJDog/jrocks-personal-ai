"""Agent Registry - Centralized agent registration and discovery.

Provides a registry for managing agents with capability-based lookup,
lifecycle management, and dynamic agent discovery.
"""

from typing import Optional, Type
from dataclasses import dataclass, field
from datetime import datetime

from .base import BaseAgent, AgentCapability, AgentConfig


@dataclass
class AgentEntry:
    """Entry for a registered agent."""
    
    agent: BaseAgent
    registered_at: datetime = field(default_factory=datetime.now)
    enabled: bool = True
    priority: int = 0  # Higher = preferred
    
    @property
    def name(self) -> str:
        return self.agent.name
    
    @property
    def capabilities(self) -> list[AgentCapability]:
        return self.agent.capabilities


class AgentRegistry:
    """Centralized registry for agent management.
    
    Provides agent registration, discovery by capability,
    and lifecycle management.
    
    Example:
        >>> registry = AgentRegistry()
        >>> registry.register(ResearchAgent())
        >>> agents = registry.get_by_capability(AgentCapability.RAG_RETRIEVAL)
    """
    
    def __init__(self) -> None:
        """Initialize the registry."""
        self._agents: dict[str, AgentEntry] = {}
    
    def register(
        self,
        agent: BaseAgent,
        priority: int = 0,
        replace: bool = False,
    ) -> AgentEntry:
        """Register an agent.
        
        Args:
            agent: The agent instance to register.
            priority: Agent priority (higher = preferred).
            replace: Whether to replace if agent name already exists.
        
        Returns:
            AgentEntry: The registered entry.
        
        Raises:
            ValueError: If agent already registered and replace is False.
        """
        name = agent.name
        
        if name in self._agents and not replace:
            raise ValueError(f"Agent already registered: {name}")
        
        entry = AgentEntry(agent=agent, priority=priority)
        self._agents[name] = entry
        return entry
    
    def unregister(self, name: str) -> bool:
        """Unregister an agent.
        
        Args:
            name: Agent name.
        
        Returns:
            bool: True if agent was unregistered.
        """
        if name in self._agents:
            del self._agents[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name.
        
        Args:
            name: Agent name.
        
        Returns:
            BaseAgent or None.
        """
        entry = self._agents.get(name)
        return entry.agent if entry and entry.enabled else None
    
    def get_by_capability(
        self,
        capability: AgentCapability,
        only_enabled: bool = True,
    ) -> list[BaseAgent]:
        """Get all agents with a specific capability.
        
        Args:
            capability: The capability to filter by.
            only_enabled: Only include enabled agents.
        
        Returns:
            list[BaseAgent]: Matching agents, sorted by priority.
        """
        entries = [
            entry for entry in self._agents.values()
            if capability in entry.capabilities
            and (entry.enabled or not only_enabled)
        ]
        
        # Sort by priority descending
        entries.sort(key=lambda e: e.priority, reverse=True)
        
        return [entry.agent for entry in entries]
    
    def get_best_for_capability(
        self,
        capability: AgentCapability,
    ) -> Optional[BaseAgent]:
        """Get the highest priority agent for a capability.
        
        Args:
            capability: The required capability.
        
        Returns:
            BaseAgent or None.
        """
        agents = self.get_by_capability(capability)
        return agents[0] if agents else None
    
    def list_all(self, only_enabled: bool = True) -> list[BaseAgent]:
        """Get all registered agents.
        
        Args:
            only_enabled: Only include enabled agents.
        
        Returns:
            list[BaseAgent]: All agents.
        """
        return [
            entry.agent for entry in self._agents.values()
            if entry.enabled or not only_enabled
        ]
    
    def list_names(self) -> list[str]:
        """Get all registered agent names."""
        return list(self._agents.keys())
    
    def list_capabilities(self) -> set[AgentCapability]:
        """Get all capabilities across all agents."""
        capabilities = set()
        for entry in self._agents.values():
            if entry.enabled:
                capabilities.update(entry.capabilities)
        return capabilities
    
    def enable(self, name: str) -> bool:
        """Enable an agent.
        
        Args:
            name: Agent name.
        
        Returns:
            bool: True if agent was enabled.
        """
        if name in self._agents:
            self._agents[name].enabled = True
            return True
        return False
    
    def disable(self, name: str) -> bool:
        """Disable an agent temporarily.
        
        Args:
            name: Agent name.
        
        Returns:
            bool: True if agent was disabled.
        """
        if name in self._agents:
            self._agents[name].enabled = False
            return True
        return False
    
    def get_capabilities_map(self) -> dict[AgentCapability, list[str]]:
        """Get a map of capabilities to agent names.
        
        Returns:
            dict: Mapping from capability to list of agent names.
        """
        result: dict[AgentCapability, list[str]] = {}
        
        for entry in self._agents.values():
            if not entry.enabled:
                continue
            for cap in entry.capabilities:
                if cap not in result:
                    result[cap] = []
                result[cap].append(entry.name)
        
        return result
    
    def count(self, only_enabled: bool = True) -> int:
        """Get the number of registered agents."""
        if only_enabled:
            return sum(1 for e in self._agents.values() if e.enabled)
        return len(self._agents)
    
    def clear(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
    
    def __contains__(self, name: str) -> bool:
        return name in self._agents
    
    def __len__(self) -> int:
        return self.count()
    
    def __repr__(self) -> str:
        return f"AgentRegistry(agents={self.count()}, capabilities={len(self.list_capabilities())})"


# Global registry instance
_global_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Get the global agent registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry


def register_default_agents(registry: Optional[AgentRegistry] = None) -> AgentRegistry:
    """Register all default agents to a registry.
    
    Args:
        registry: Registry to use, or global if None.
    
    Returns:
        AgentRegistry: The registry with agents registered.
    """
    from .research import ResearchAgent
    from .code import CodeAgent
    from .content import ContentAgent
    from .memory import MemoryAgent
    from .chat_sync import ChatHistorySyncAgent
    from .cowork import CoworkAgent
    
    if registry is None:
        registry = get_registry()
    
    registry.register(ResearchAgent(), priority=10)
    registry.register(CodeAgent(), priority=10)
    registry.register(ContentAgent(), priority=10)
    registry.register(MemoryAgent(), priority=10)
    registry.register(CoworkAgent(), priority=15)
    
    # Register Sync Agent
    registry.register(ChatHistorySyncAgent(), priority=5)
    
    return registry
