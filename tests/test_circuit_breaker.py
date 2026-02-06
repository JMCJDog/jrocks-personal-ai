"""Tests for the circuit breaker module."""

import pytest
import asyncio

from app.agents.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
    CircuitBreakerRegistry,
    with_circuit_breaker,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""
    
    def test_initial_state(self):
        """Test initial state is closed."""
        breaker = CircuitBreaker("test")
        
        assert breaker.is_closed
        assert not breaker.is_open
        assert breaker.state == CircuitState.CLOSED
    
    def test_allow_request_when_closed(self):
        """Test requests allowed when closed."""
        breaker = CircuitBreaker("test")
        
        assert breaker.allow_request() is True
    
    def test_opens_after_threshold_failures(self):
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)
        
        # Record failures up to threshold
        for _ in range(3):
            breaker.record_failure()
        
        assert breaker.is_open
        assert breaker.state == CircuitState.OPEN
    
    def test_blocks_requests_when_open(self):
        """Test requests blocked when circuit is open."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=60)
        breaker = CircuitBreaker("test", config)
        
        breaker.record_failure()  # Opens the circuit
        
        with pytest.raises(CircuitBreakerError) as exc_info:
            breaker.allow_request()
        
        assert exc_info.value.name == "test"
    
    def test_half_open_after_timeout(self):
        """Test transition to half-open after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0,  # Immediate timeout for testing
        )
        breaker = CircuitBreaker("test", config)
        
        breaker.record_failure()  # Opens
        assert breaker.is_open
        
        # Try request after "timeout"
        breaker.allow_request()
        assert breaker.is_half_open
    
    def test_closes_after_success_in_half_open(self):
        """Test circuit closes after successes in half-open."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0,
        )
        breaker = CircuitBreaker("test", config)
        
        # Open the circuit
        breaker.record_failure()
        
        # Transition to half-open
        breaker.allow_request()
        assert breaker.is_half_open
        
        # Record successes
        breaker.record_success()
        breaker.record_success()
        
        assert breaker.is_closed
    
    def test_reopens_on_failure_in_half_open(self):
        """Test circuit reopens on failure in half-open."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0,
        )
        breaker = CircuitBreaker("test", config)
        
        breaker.record_failure()  # Open
        breaker.allow_request()   # Half-open
        breaker.record_failure()  # Should reopen
        
        assert breaker.is_open
    
    def test_context_manager_success(self):
        """Test context manager records success."""
        breaker = CircuitBreaker("test")
        
        with breaker:
            pass  # Successful operation
        
        assert breaker.stats.success_count == 1
    
    def test_context_manager_failure(self):
        """Test context manager records failure."""
        breaker = CircuitBreaker("test")
        
        with pytest.raises(ValueError):
            with breaker:
                raise ValueError("test error")
        
        assert breaker.stats.failure_count == 1
    
    def test_manual_reset(self):
        """Test manual reset to closed."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker("test", config)
        
        breaker.record_failure()  # Open
        assert breaker.is_open
        
        breaker.reset()
        assert breaker.is_closed


class TestCircuitBreakerDecorator:
    """Tests for with_circuit_breaker decorator."""
    
    def test_decorator_sync(self):
        """Test decorator with sync function."""
        breaker = CircuitBreaker("sync_test")
        
        @with_circuit_breaker(breaker)
        def my_func(x: int) -> int:
            return x * 2
        
        result = my_func(5)
        
        assert result == 10
        assert breaker.stats.success_count == 1
    
    def test_decorator_with_fallback(self):
        """Test decorator with fallback when circuit open."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=60)
        breaker = CircuitBreaker("fallback_test", config)
        
        # Open the circuit
        breaker.record_failure()
        
        @with_circuit_breaker(breaker, fallback=lambda x: "fallback")
        def my_func(x: str) -> str:
            return f"result: {x}"
        
        result = my_func("test")
        assert result == "fallback"
    
    @pytest.mark.asyncio
    async def test_decorator_async(self):
        """Test decorator with async function."""
        breaker = CircuitBreaker("async_test")
        
        @with_circuit_breaker(breaker)
        async def my_async_func(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 3
        
        result = await my_async_func(4)
        
        assert result == 12
        assert breaker.stats.success_count == 1


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""
    
    def test_get_or_create(self):
        """Test getting or creating a breaker."""
        registry = CircuitBreakerRegistry()
        
        breaker1 = registry.get_or_create("service_a")
        breaker2 = registry.get_or_create("service_a")
        
        assert breaker1 is breaker2
    
    def test_different_names_different_breakers(self):
        """Test different names create different breakers."""
        registry = CircuitBreakerRegistry()
        
        breaker_a = registry.get_or_create("service_a")
        breaker_b = registry.get_or_create("service_b")
        
        assert breaker_a is not breaker_b
    
    def test_list_all(self):
        """Test listing all breakers."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("a")
        registry.get_or_create("b")
        registry.get_or_create("c")
        
        all_breakers = registry.list_all()
        assert len(all_breakers) == 3
    
    def test_get_open_circuits(self):
        """Test getting open circuits."""
        registry = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        
        breaker_a = registry.get_or_create("a")
        breaker_b = registry.get_or_create("b")
        
        breaker_a.record_failure()  # Opens
        
        open_circuits = registry.get_open_circuits()
        assert len(open_circuits) == 1
        assert open_circuits[0].name == "a"
    
    def test_reset_all(self):
        """Test resetting all breakers."""
        registry = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        
        for name in ["a", "b", "c"]:
            breaker = registry.get_or_create(name)
            breaker.record_failure()  # Opens
        
        assert len(registry.get_open_circuits()) == 3
        
        registry.reset_all()
        
        assert len(registry.get_open_circuits()) == 0
    
    def test_get_stats(self):
        """Test getting stats for all breakers."""
        registry = CircuitBreakerRegistry()
        breaker = registry.get_or_create("test")
        breaker.record_success()
        breaker.record_failure()
        
        stats = registry.get_stats()
        
        assert "test" in stats
        assert stats["test"]["success_count"] == 1
        assert stats["test"]["failure_count"] == 1
