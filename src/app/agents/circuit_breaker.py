"""Circuit Breaker Pattern - Prevent cascading agent failures.

Implements the circuit breaker pattern to prevent repeated calls to
failing agents, allowing time for recovery while maintaining system stability.
"""

from enum import Enum
from typing import Optional, Callable, Any, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import time


class CircuitState(Enum):
    """Circuit breaker states."""
    
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failing, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changed_at: datetime = field(default_factory=datetime.now)
    total_calls: int = 0
    total_blocked: int = 0
    
    def record_success(self) -> None:
        """Record a successful call."""
        self.success_count += 1
        self.total_calls += 1
        self.last_success_time = datetime.now()
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.total_calls += 1
        self.last_failure_time = datetime.now()
    
    def record_blocked(self) -> None:
        """Record a blocked call (circuit open)."""
        self.total_blocked += 1
    
    def reset_counts(self) -> None:
        """Reset failure/success counts (on state change)."""
        self.failure_count = 0
        self.success_count = 0
        self.state_changed_at = datetime.now()
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.failure_count / self.total_calls) * 100


class CircuitBreakerError(Exception):
    """Raised when circuit is open and blocking requests."""
    
    def __init__(self, name: str, until: datetime):
        self.name = name
        self.until = until
        super().__init__(f"Circuit '{name}' is open until {until.isoformat()}")


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 3  # Successes in half-open before closing
    timeout_seconds: int = 30   # Time before attempting half-open
    half_open_max_calls: int = 3  # Max test calls in half-open state
    
    # Optional failure rate threshold (alternative to count)
    failure_rate_threshold: Optional[float] = None  # e.g., 50.0 for 50%
    min_calls_for_rate: int = 10  # Min calls before rate applies


class CircuitBreaker:
    """Circuit breaker implementation.
    
    Monitors calls to a service/agent and opens the circuit when
    too many failures occur, preventing further calls until recovery.
    
    Example:
        >>> breaker = CircuitBreaker("my_agent")
        >>> 
        >>> try:
        ...     with breaker:
        ...         result = agent.process(message)
        ...     breaker.record_success()
        ... except Exception as e:
        ...     breaker.record_failure()
        ...     raise
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit.
            config: Configuration options.
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN
    
    def _should_open(self) -> bool:
        """Check if circuit should transition to open."""
        # Check count threshold
        if self.stats.failure_count >= self.config.failure_threshold:
            return True
        
        # Check rate threshold if configured
        if (
            self.config.failure_rate_threshold 
            and self.stats.total_calls >= self.config.min_calls_for_rate
        ):
            if self.stats.failure_rate >= self.config.failure_rate_threshold:
                return True
        
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.stats.last_failure_time:
            return True
        
        elapsed = datetime.now() - self.stats.last_failure_time
        return elapsed.total_seconds() >= self.config.timeout_seconds
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state
        self.stats.reset_counts()
        self._half_open_calls = 0
        
        # Log state change
        print(f"Circuit '{self.name}': {old_state.value} -> {new_state.value}")
    
    def allow_request(self) -> bool:
        """Check if a request should be allowed.
        
        Returns:
            bool: True if request can proceed.
        
        Raises:
            CircuitBreakerError: If circuit is open.
        """
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            
            # Still blocked
            self.stats.record_blocked()
            retry_at = (
                self.stats.last_failure_time 
                + timedelta(seconds=self.config.timeout_seconds)
            )
            raise CircuitBreakerError(self.name, retry_at)
        
        # Half-open: allow limited calls
        if self._half_open_calls < self.config.half_open_max_calls:
            self._half_open_calls += 1
            return True
        
        # Too many half-open calls, block
        self.stats.record_blocked()
        raise CircuitBreakerError(
            self.name,
            datetime.now() + timedelta(seconds=5),
        )
    
    def record_success(self) -> None:
        """Record a successful call."""
        self.stats.record_success()
        
        if self.state == CircuitState.HALF_OPEN:
            if self.stats.success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
    
    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record a failed call.
        
        Args:
            error: Optional exception that caused the failure.
        """
        self.stats.record_failure()
        
        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open reopens circuit
            self._transition_to(CircuitState.OPEN)
        elif self.state == CircuitState.CLOSED:
            if self._should_open():
                self._transition_to(CircuitState.OPEN)
    
    def reset(self) -> None:
        """Manually reset the circuit to closed state."""
        self._transition_to(CircuitState.CLOSED)
    
    def __enter__(self):
        """Context manager entry - check if request allowed."""
        self.allow_request()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - record success/failure."""
        if exc_type is None:
            self.record_success()
        else:
            self.record_failure(exc_val)
        return False  # Don't suppress exceptions


# Type variable for decorated function
F = TypeVar('F', bound=Callable[..., Any])


def with_circuit_breaker(
    breaker: CircuitBreaker,
    fallback: Optional[Callable[..., Any]] = None,
) -> Callable[[F], F]:
    """Decorator to wrap a function with circuit breaker protection.
    
    Args:
        breaker: The circuit breaker to use.
        fallback: Optional fallback function when circuit is open.
    
    Returns:
        Decorated function.
    
    Example:
        >>> breaker = CircuitBreaker("external_api")
        >>> 
        >>> @with_circuit_breaker(breaker, fallback=lambda *a, **k: "default")
        ... def call_api(query: str) -> str:
        ...     return external_api.search(query)
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                breaker.allow_request()
            except CircuitBreakerError:
                if fallback:
                    return fallback(*args, **kwargs)
                raise
            
            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure(e)
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                breaker.allow_request()
            except CircuitBreakerError:
                if fallback:
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    return fallback(*args, **kwargs)
                raise
            
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure(e)
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers.
    
    Example:
        >>> registry = CircuitBreakerRegistry()
        >>> breaker = registry.get_or_create("agent_a")
        >>> with breaker:
        ...     do_something()
    """
    
    def __init__(self, default_config: Optional[CircuitBreakerConfig] = None):
        """Initialize registry.
        
        Args:
            default_config: Default config for new breakers.
        """
        self._breakers: dict[str, CircuitBreaker] = {}
        self.default_config = default_config or CircuitBreakerConfig()
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker.
        
        Args:
            name: Breaker identifier.
            config: Optional config (uses default if not provided).
        
        Returns:
            CircuitBreaker: The circuit breaker.
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name,
                config or self.default_config,
            )
        return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self._breakers.get(name)
    
    def list_all(self) -> list[CircuitBreaker]:
        """Get all registered circuit breakers."""
        return list(self._breakers.values())
    
    def get_open_circuits(self) -> list[CircuitBreaker]:
        """Get all circuits currently in open state."""
        return [b for b in self._breakers.values() if b.is_open]
    
    def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        for breaker in self._breakers.values():
            breaker.reset()
    
    def get_stats(self) -> dict[str, dict]:
        """Get statistics for all breakers."""
        return {
            name: {
                "state": breaker.state.value,
                "failure_count": breaker.stats.failure_count,
                "success_count": breaker.stats.success_count,
                "total_calls": breaker.stats.total_calls,
                "total_blocked": breaker.stats.total_blocked,
                "failure_rate": breaker.stats.failure_rate,
            }
            for name, breaker in self._breakers.items()
        }


# Global registry instance
_global_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CircuitBreakerRegistry()
    return _global_registry
