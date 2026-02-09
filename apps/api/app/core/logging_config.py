"""
Structured Logging Configuration for FastAPI Backend
Features:
- Request latency logging
- AI call duration + token tracking
- Error stack traces
- Correlation ID per request
"""
import logging
import sys
import time
import uuid
import traceback
from typing import Optional, Any, Dict
from datetime import datetime
from contextvars import ContextVar
from functools import wraps
import json

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


# ==================== Custom JSON Formatter ====================

class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(""),
        }
        
        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stacktrace": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None
            }
        
        # Add location
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName
        }
        
        return json.dumps(log_data, default=str)


# ==================== Logger with Correlation ID ====================

class CorrelatedLogger:
    """Logger wrapper that includes correlation ID"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log(self, level: int, msg: str, extra_data: Optional[Dict] = None, **kwargs):
        extra = {"extra_data": extra_data or {}}
        extra["extra_data"]["correlation_id"] = correlation_id_var.get("")
        self.logger.log(level, msg, extra=extra, **kwargs)
    
    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, exc_info: bool = False, **kwargs):
        self._log(logging.ERROR, msg, exc_info=exc_info, **kwargs)
    
    def critical(self, msg: str, exc_info: bool = True, **kwargs):
        self._log(logging.CRITICAL, msg, exc_info=exc_info, **kwargs)


def get_logger(name: str) -> CorrelatedLogger:
    """Get a correlated logger instance"""
    return CorrelatedLogger(name)


# ==================== Request Logging Middleware ====================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests with latency and correlation ID"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        correlation_id_var.set(correlation_id)
        
        # Start timing
        start_time = time.perf_counter()
        
        # Log request
        logger = get_logger("http.request")
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra_data={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_query": str(request.query_params),
                "user_agent": request.headers.get("user-agent"),
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=True,
                extra_data={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "latency_ms": round(latency_ms, 2),
                    "error": str(e),
                }
            )
            raise
        
        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path} -> {response.status_code}",
            extra_data={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "latency_ms": round(latency_ms, 2),
            }
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


# ==================== AI Call Logging ====================

def log_ai_call(
    model: str,
    operation: str,
    tokens_input: int = 0,
    tokens_output: int = 0,
    duration_ms: float = 0,
    success: bool = True,
    error: Optional[str] = None,
    extra: Optional[Dict] = None
):
    """Log AI/LLM API calls with token usage and duration"""
    logger = get_logger("ai.calls")
    
    log_data = {
        "ai_model": model,
        "ai_operation": operation,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "tokens_total": tokens_input + tokens_output,
        "duration_ms": round(duration_ms, 2),
        "success": success,
        **(extra or {})
    }
    
    if error:
        log_data["error"] = error
        logger.error(f"AI call failed: {operation}", extra_data=log_data)
    else:
        logger.info(f"AI call completed: {operation}", extra_data=log_data)


def ai_call_logger(model: str, operation: str):
    """Decorator for logging AI calls"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                # Try to extract token counts from result
                tokens_input = getattr(result, 'prompt_tokens', 0)
                tokens_output = getattr(result, 'completion_tokens', 0)
                
                log_ai_call(
                    model=model,
                    operation=operation,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
                
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_ai_call(
                    model=model,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
                raise
        return wrapper
    return decorator


# ==================== Error Logging ====================

def log_exception(
    error: Exception,
    context: str = "",
    extra: Optional[Dict] = None
):
    """Log an exception with full stack trace"""
    logger = get_logger("app.errors")
    
    logger.error(
        f"Exception in {context}: {type(error).__name__}: {str(error)}",
        exc_info=True,
        extra_data={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            **(extra or {})
        }
    )


# ==================== Setup Function ====================

def setup_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    log_to_file: Optional[str] = None
):
    """
    Configure logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON formatting (recommended for production)
        log_to_file: Optional file path for logging
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))
    
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_to_file:
        file_handler = logging.FileHandler(log_to_file)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    # Reduce noise from libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return root_logger


# ==================== FastAPI Integration ====================

def add_logging_middleware(app):
    """Add logging middleware to FastAPI app"""
    app.add_middleware(RequestLoggingMiddleware)
