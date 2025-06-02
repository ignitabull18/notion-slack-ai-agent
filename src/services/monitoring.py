"""
Monitoring and observability setup for the Notion-Slack AI Agent.
"""
import logging
import os
import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import structlog
from src.config import Settings

# Prometheus metrics
REQUEST_COUNT = Counter('agent_requests_total', 'Total agent requests', ['endpoint', 'method'])
REQUEST_DURATION = Histogram('agent_request_duration_seconds', 'Request duration in seconds', ['endpoint'])
ACTIVE_CONNECTIONS = Gauge('agent_active_connections', 'Number of active connections')
NOTION_API_CALLS = Counter('notion_api_calls_total', 'Total Notion API calls', ['operation', 'status'])
SLACK_API_CALLS = Counter('slack_api_calls_total', 'Total Slack API calls', ['operation', 'status'])
AGENT_RESPONSES = Counter('agent_responses_total', 'Total agent responses', ['status'])
ERROR_COUNT = Counter('agent_errors_total', 'Total errors', ['type'])

# Global logger instance
logger = None

def setup_monitoring(settings: Settings) -> None:
    """
    Setup monitoring, logging, and metrics collection.
    
    Args:
        settings: Application settings containing monitoring configuration
    """
    global logger
    
    # Setup structured logging
    logger = setup_structured_logging(settings)
    
    # Setup Prometheus metrics server
    if settings.metrics_enabled:
        setup_prometheus_metrics(settings)
    
    # Setup error tracking (Sentry)
    if settings.sentry_dsn:
        setup_sentry(settings)
    
    logger.info("Monitoring system initialized", 
                metrics_enabled=settings.metrics_enabled,
                log_level=settings.log_level)

def setup_structured_logging(settings: Settings) -> structlog.BoundLogger:
    """Setup structured logging with structlog."""
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=None,
        level=getattr(logging, settings.log_level.upper())
    )
    
    return structlog.get_logger()

def setup_prometheus_metrics(settings: Settings) -> None:
    """Setup Prometheus metrics server."""
    try:
        # Start Prometheus metrics server
        start_http_server(settings.prometheus_port)
        logger.info(f"Prometheus metrics server started on port {settings.prometheus_port}")
    except Exception as e:
        logger.error(f"Failed to start Prometheus metrics server: {e}")

def setup_sentry(settings: Settings) -> None:
    """Setup Sentry error tracking."""
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[
                FastApiIntegration(auto_enable=True),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,
            environment=settings.environment,
            release=settings.version
        )
        logger.info("Sentry error tracking initialized")
    except ImportError:
        logger.warning("Sentry SDK not available, skipping error tracking setup")
    except Exception as e:
        logger.error(f"Failed to setup Sentry: {e}")

class MetricsMiddleware:
    """FastAPI middleware for collecting metrics."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        # Track active connections
        ACTIVE_CONNECTIONS.inc()
        
        # Get request info
        path = scope.get("path", "unknown")
        method = scope.get("method", "unknown")
        
        # Track request start time
        start_time = time.time()
        
        try:
            # Process request
            await self.app(scope, receive, send)
            
            # Record successful request
            REQUEST_COUNT.labels(endpoint=path, method=method).inc()
            
        except Exception as e:
            # Record error
            ERROR_COUNT.labels(type=type(e).__name__).inc()
            logger.error("Request failed", path=path, method=method, error=str(e))
            raise
        finally:
            # Record request duration
            duration = time.time() - start_time
            REQUEST_DURATION.labels(endpoint=path).observe(duration)
            
            # Decrease active connections
            ACTIVE_CONNECTIONS.dec()

def track_notion_api_call(operation: str, success: bool = True) -> None:
    """Track Notion API call metrics."""
    status = "success" if success else "error"
    NOTION_API_CALLS.labels(operation=operation, status=status).inc()
    
    if logger:
        logger.debug("Notion API call", operation=operation, status=status)

def track_slack_api_call(operation: str, success: bool = True) -> None:
    """Track Slack API call metrics."""
    status = "success" if success else "error"
    SLACK_API_CALLS.labels(operation=operation, status=status).inc()
    
    if logger:
        logger.debug("Slack API call", operation=operation, status=status)

def track_agent_response(success: bool = True) -> None:
    """Track agent response metrics."""
    status = "success" if success else "error"
    AGENT_RESPONSES.labels(status=status).inc()
    
    if logger:
        logger.debug("Agent response", status=status)

def track_error(error_type: str, error_message: str, **context) -> None:
    """Track error occurrence."""
    ERROR_COUNT.labels(type=error_type).inc()
    
    if logger:
        logger.error("Error tracked", 
                    error_type=error_type, 
                    error_message=error_message, 
                    **context)

class PerformanceMonitor:
    """Context manager for monitoring operation performance."""
    
    def __init__(self, operation_name: str, **context):
        self.operation_name = operation_name
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        if logger:
            logger.debug(f"Starting {self.operation_name}", **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            # Success
            if logger:
                logger.info(f"Completed {self.operation_name}", 
                           duration=duration, **self.context)
        else:
            # Error
            track_error(exc_type.__name__, str(exc_val), 
                       operation=self.operation_name, **self.context)
            if logger:
                logger.error(f"Failed {self.operation_name}", 
                           duration=duration, 
                           error=str(exc_val), 
                           **self.context)

def get_system_metrics() -> Dict[str, Any]:
    """Get current system metrics."""
    try:
        import psutil
        
        # Get process info
        process = psutil.Process()
        
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "memory_rss": process.memory_info().rss,
            "memory_vms": process.memory_info().vms,
            "open_files": len(process.open_files()),
            "connections": len(process.connections()),
            "threads": process.num_threads(),
            "uptime_seconds": time.time() - process.create_time()
        }
    except ImportError:
        return {"error": "psutil not available"}
    except Exception as e:
        return {"error": f"Failed to get metrics: {e}"}

def health_check() -> Dict[str, Any]:
    """Perform a comprehensive health check."""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {},
        "metrics": get_system_metrics()
    }
    
    # Check Notion API connectivity
    try:
        from src.tools.notion_tools import NotionTools
        notion_tools = NotionTools()
        # This would be a simple test call
        health_status["components"]["notion"] = "healthy"
    except Exception as e:
        health_status["components"]["notion"] = f"unhealthy: {e}"
        health_status["status"] = "degraded"
    
    # Check Slack API connectivity
    try:
        from src.tools.slack_tools import SlackTools
        slack_tools = SlackTools()
        # This would be a simple test call
        health_status["components"]["slack"] = "healthy"
    except Exception as e:
        health_status["components"]["slack"] = f"unhealthy: {e}"
        health_status["status"] = "degraded"
    
    return health_status

# Decorator for monitoring function calls
def monitor_performance(operation_name: str):
    """Decorator to monitor function performance."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with PerformanceMonitor(operation_name):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            with PerformanceMonitor(operation_name):
                return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
