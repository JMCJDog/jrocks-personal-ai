"""Enhanced Observability - Structured logging and metrics.

Provides distributed tracing, metrics collection, and structured
event logging for debugging multi-agent swarm behavior.
"""

from typing import Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from contextlib import contextmanager
from functools import wraps
import json
import uuid
import time
import threading
import logging


# Configure base logger
logger = logging.getLogger("observability")


@dataclass
class SpanContext:
    """Context for distributed tracing spans.
    
    Represents a unit of work with timing and metadata.
    """
    
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    parent_span_id: Optional[str] = None
    operation: str = ""
    service: str = "jrocks-ai"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "ok"  # ok, error
    tags: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> float:
        """Calculate span duration in milliseconds."""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000
    
    def set_tag(self, key: str, value: Any) -> "SpanContext":
        """Set a tag on this span."""
        self.tags[key] = value
        return self
    
    def add_event(self, name: str, attributes: Optional[dict] = None) -> "SpanContext":
        """Add an event to this span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "attributes": attributes or {},
        })
        return self
    
    def set_error(self, error: Exception) -> "SpanContext":
        """Mark span as error with exception details."""
        self.status = "error"
        self.tags["error.type"] = type(error).__name__
        self.tags["error.message"] = str(error)
        return self
    
    def finish(self) -> "SpanContext":
        """Mark span as finished."""
        self.end_time = time.time()
        return self
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "service": self.service,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "events": self.events,
        }


# Thread-local storage for current span context
_current_span = threading.local()


def get_current_span() -> Optional[SpanContext]:
    """Get the current active span."""
    return getattr(_current_span, "span", None)


def set_current_span(span: Optional[SpanContext]) -> None:
    """Set the current active span."""
    _current_span.span = span


@contextmanager
def trace_span(
    operation: str,
    tags: Optional[dict] = None,
    parent: Optional[SpanContext] = None,
):
    """Context manager for creating a traced span.
    
    Example:
        >>> with trace_span("process_request", {"agent": "research"}) as span:
        ...     result = do_work()
        ...     span.set_tag("result_size", len(result))
    """
    # Get parent from context if not provided
    if parent is None:
        parent = get_current_span()
    
    span = SpanContext(
        operation=operation,
        trace_id=parent.trace_id if parent else str(uuid.uuid4()),
        parent_span_id=parent.span_id if parent else None,
        tags=tags or {},
    )
    
    # Set as current span
    previous_span = get_current_span()
    set_current_span(span)
    
    try:
        yield span
        span.finish()
    except Exception as e:
        span.set_error(e)
        span.finish()
        raise
    finally:
        # Restore previous span
        set_current_span(previous_span)
        
        # Log the completed span
        EventLogger.span(span)


def traced(operation: Optional[str] = None, tags: Optional[dict] = None):
    """Decorator to trace a function.
    
    Example:
        >>> @traced("agent.process")
        ... def process(message: str) -> str:
        ...     return "result"
    """
    def decorator(func: Callable) -> Callable:
        op_name = operation or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with trace_span(op_name, tags) as span:
                return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_span(op_name, tags) as span:
                return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


@dataclass
class AgentMetrics:
    """Metrics for agent performance tracking."""
    
    agent_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    last_request_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests
    
    def record_request(
        self,
        success: bool,
        latency_ms: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        """Record a completed request."""
        self.total_requests += 1
        self.last_request_time = datetime.now()
        
        if success:
            self.successful_requests += 1
            self.total_latency_ms += latency_ms
        else:
            self.failed_requests += 1
        
        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
        }


class MetricsCollector:
    """Centralized metrics collection for agents.
    
    Example:
        >>> collector = MetricsCollector()
        >>> collector.record("research_agent", True, 150.0, tokens_in=100)
        >>> print(collector.get_summary())
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self._metrics: dict[str, AgentMetrics] = {}
        self._lock = threading.Lock()
    
    def record(
        self,
        agent_name: str,
        success: bool,
        latency_ms: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        """Record a request for an agent.
        
        Args:
            agent_name: Name of the agent.
            success: Whether request succeeded.
            latency_ms: Request latency in milliseconds.
            tokens_in: Input tokens used.
            tokens_out: Output tokens generated.
        """
        with self._lock:
            if agent_name not in self._metrics:
                self._metrics[agent_name] = AgentMetrics(agent_name=agent_name)
            
            self._metrics[agent_name].record_request(
                success, latency_ms, tokens_in, tokens_out
            )
    
    def get(self, agent_name: str) -> Optional[AgentMetrics]:
        """Get metrics for a specific agent."""
        return self._metrics.get(agent_name)
    
    def get_all(self) -> dict[str, AgentMetrics]:
        """Get all agent metrics."""
        return dict(self._metrics)
    
    def get_summary(self) -> dict:
        """Get summary across all agents."""
        total_requests = sum(m.total_requests for m in self._metrics.values())
        total_success = sum(m.successful_requests for m in self._metrics.values())
        total_latency = sum(m.total_latency_ms for m in self._metrics.values())
        
        return {
            "total_agents": len(self._metrics),
            "total_requests": total_requests,
            "overall_success_rate": (total_success / total_requests * 100) if total_requests > 0 else 100.0,
            "avg_latency_ms": (total_latency / total_success) if total_success > 0 else 0.0,
            "agents": {name: m.to_dict() for name, m in self._metrics.items()},
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()


class EventLogger:
    """Structured event logging for observability.
    
    Outputs JSON-formatted logs for easy parsing and analysis.
    
    Example:
        >>> EventLogger.info("agent.started", agent="research", task_id="123")
        >>> EventLogger.error("agent.failed", error="Connection timeout")
    """
    
    _logger = logging.getLogger("jrocks.events")
    
    @classmethod
    def _log(cls, level: str, event: str, **kwargs) -> None:
        """Internal logging method."""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "event": event,
            **kwargs,
        }
        
        # Add trace context if available
        span = get_current_span()
        if span:
            log_data["trace_id"] = span.trace_id
            log_data["span_id"] = span.span_id
        
        # Log as JSON
        json_str = json.dumps(log_data)
        
        log_method = getattr(cls._logger, level.lower(), cls._logger.info)
        log_method(json_str)
    
    @classmethod
    def debug(cls, event: str, **kwargs) -> None:
        """Log debug event."""
        cls._log("DEBUG", event, **kwargs)
    
    @classmethod
    def info(cls, event: str, **kwargs) -> None:
        """Log info event."""
        cls._log("INFO", event, **kwargs)
    
    @classmethod
    def warning(cls, event: str, **kwargs) -> None:
        """Log warning event."""
        cls._log("WARNING", event, **kwargs)
    
    @classmethod
    def error(cls, event: str, **kwargs) -> None:
        """Log error event."""
        cls._log("ERROR", event, **kwargs)
    
    @classmethod
    def span(cls, span: SpanContext) -> None:
        """Log a completed span."""
        cls._log(
            "INFO" if span.status == "ok" else "ERROR",
            "span.completed",
            **span.to_dict(),
        )
    
    @classmethod
    def agent_request(
        cls,
        agent_name: str,
        request_id: str,
        message: str,
        **kwargs,
    ) -> None:
        """Log an agent request start."""
        cls.info(
            "agent.request.start",
            agent=agent_name,
            request_id=request_id,
            message_preview=message[:100] if message else "",
            **kwargs,
        )
    
    @classmethod
    def agent_response(
        cls,
        agent_name: str,
        request_id: str,
        success: bool,
        latency_ms: float,
        **kwargs,
    ) -> None:
        """Log an agent response completion."""
        level = "info" if success else "error"
        cls._log(
            level.upper(),
            "agent.request.complete",
            agent=agent_name,
            request_id=request_id,
            success=success,
            latency_ms=latency_ms,
            **kwargs,
        )


# Global instances
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def configure_logging(
    level: int = logging.INFO,
    json_output: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """Configure observability logging.
    
    Args:
        level: Logging level.
        json_output: Whether to output JSON format.
        log_file: Optional file path for logs.
    """
    handlers = []
    
    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    handlers.append(console)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        handlers.append(file_handler)
    
    # Configure format
    if json_output:
        formatter = logging.Formatter("%(message)s")
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    for handler in handlers:
        handler.setFormatter(formatter)
    
    # Apply to event logger
    event_logger = logging.getLogger("jrocks.events")
    event_logger.setLevel(level)
    for handler in handlers:
        event_logger.addHandler(handler)
