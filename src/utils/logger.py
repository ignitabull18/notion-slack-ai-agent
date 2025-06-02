"""
Logging utilities for the Notion-Slack AI Agent.
"""
import logging
import sys
from typing import Optional
from pathlib import Path
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'message', 'exc_info', 'exc_text', 
                          'stack_info'):
                log_entry[key] = value
        
        return json.dumps(log_entry)

def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
    enable_console: bool = True
) -> None:
    """
    Setup logging configuration for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging output
        json_format: Whether to use JSON formatting
        enable_console: Whether to enable console logging
    """
    # Clear any existing handlers
    logging.getLogger().handlers.clear()
    
    # Set root logger level
    logging.getLogger().setLevel(getattr(logging, level.upper()))
    
    handlers = []
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        
        if json_format:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
        
        handlers.append(console_handler)
    
    # File handler
    if log_file:
        # Ensure log directory exists
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        
        if json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
                )
            )
        
        handlers.append(file_handler)
    
    # Configure root logger
    for handler in handlers:
        handler.setLevel(getattr(logging, level.upper()))
        logging.getLogger().addHandler(handler)
    
    # Configure specific loggers
    configure_library_loggers()

def configure_library_loggers():
    """Configure logging levels for external libraries."""
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("slack_sdk").setLevel(logging.INFO)
    logging.getLogger("notion_client").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

class ContextLogger:
    """Logger with automatic context injection."""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with injected context."""
        # Merge context with kwargs
        merged_context = {**self.context, **kwargs}
        
        # Create a new log record with extra context
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            __file__,
            0,
            message,
            (),
            None,
            **merged_context
        )
        
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, message, **kwargs)

def get_context_logger(name: str, **context) -> ContextLogger:
    """
    Get a context logger that automatically injects context into log messages.
    
    Args:
        name: Logger name
        **context: Context to inject into all log messages
    
    Returns:
        ContextLogger instance
    """
    logger = get_logger(name)
    return ContextLogger(logger, **context)

# Logging decorators
def log_function_call(logger: Optional[logging.Logger] = None):
    """
    Decorator to log function calls with arguments and return values.
    
    Args:
        logger: Optional logger instance. If None, uses function's module logger.
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        def wrapper(*args, **kwargs):
            # Log function entry
            logger.debug(
                f"Calling {func.__name__}",
                function=func.__name__,
                args=str(args)[:200],  # Truncate for readability
                kwargs=str(kwargs)[:200]
            )
            
            try:
                result = func(*args, **kwargs)
                logger.debug(
                    f"Function {func.__name__} completed successfully",
                    function=func.__name__,
                    result_type=type(result).__name__
                )
                return result
            except Exception as e:
                logger.error(
                    f"Function {func.__name__} failed",
                    function=func.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator

def log_performance(logger: Optional[logging.Logger] = None, threshold_ms: float = 1000):
    """
    Decorator to log function performance.
    
    Args:
        logger: Optional logger instance
        threshold_ms: Log warning if function takes longer than this (milliseconds)
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        import time
        
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                log_level = logging.WARNING if duration_ms > threshold_ms else logging.DEBUG
                logger.log(
                    log_level,
                    f"Function {func.__name__} took {duration_ms:.2f}ms",
                    function=func.__name__,
                    duration_ms=duration_ms,
                    slow_call=duration_ms > threshold_ms
                )
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Function {func.__name__} failed after {duration_ms:.2f}ms",
                    function=func.__name__,
                    duration_ms=duration_ms,
                    error=str(e),
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator

# Security logging helpers
def log_security_event(event_type: str, details: dict, severity: str = "INFO"):
    """
    Log security-related events with standardized format.
    
    Args:
        event_type: Type of security event (auth_failure, rate_limit, etc.)
        details: Event details dictionary
        severity: Log severity level
    """
    security_logger = get_logger("security")
    
    log_entry = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "security_event": True,
        **details
    }
    
    level = getattr(logging, severity.upper(), logging.INFO)
    security_logger.log(level, f"Security event: {event_type}", **log_entry)

def log_api_call(service: str, operation: str, success: bool, duration_ms: float, **details):
    """
    Log API calls with standardized format.
    
    Args:
        service: Service name (notion, slack, etc.)
        operation: Operation performed
        success: Whether the call was successful
        duration_ms: Call duration in milliseconds
        **details: Additional details
    """
    api_logger = get_logger(f"api.{service}")
    
    log_entry = {
        "service": service,
        "operation": operation,
        "success": success,
        "duration_ms": duration_ms,
        "api_call": True,
        **details
    }
    
    level = logging.INFO if success else logging.ERROR
    status = "succeeded" if success else "failed"
    
    api_logger.log(
        level,
        f"{service.title()} API call {status}: {operation}",
        **log_entry
    )
