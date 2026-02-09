"""
AI Service Resilience Utilities
Provides retry logic, timeouts, fallbacks, and error handling for AI services
"""
import asyncio
import time
import random
from typing import TypeVar, Callable, Optional, Any, Dict, List
from functools import wraps
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AIServiceError(Exception):
    """Base exception for AI service errors"""
    pass


class AITimeoutError(AIServiceError):
    """AI service timeout"""
    pass


class AIRateLimitError(AIServiceError):
    """AI service rate limited"""
    pass


class AIUnavailableError(AIServiceError):
    """AI service unavailable"""
    pass


# ==================== Retry Configuration ====================

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: tuple = (AITimeoutError, AIRateLimitError, AIUnavailableError)


DEFAULT_RETRY_CONFIG = RetryConfig()


# ==================== Retry Decorator ====================

def with_retry(
    config: RetryConfig = DEFAULT_RETRY_CONFIG,
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying async functions with exponential backoff
    
    Args:
        config: Retry configuration
        on_retry: Optional callback called on each retry (attempt, error, delay)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except config.retry_on as e:
                    last_error = e
                    
                    if attempt == config.max_retries:
                        logger.error(f"All {config.max_retries} retries exhausted for {func.__name__}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                        f"after {delay:.2f}s due to: {type(e).__name__}: {e}"
                    )
                    
                    if on_retry:
                        on_retry(attempt + 1, e, delay)
                    
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    # Non-retryable error
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            
            raise last_error
        
        return wrapper
    return decorator


# ==================== Timeout Decorator ====================

def with_timeout(seconds: float, error_message: str = "Operation timed out"):
    """
    Decorator for adding timeout to async functions
    
    Args:
        seconds: Timeout in seconds
        error_message: Custom error message
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout ({seconds}s) in {func.__name__}")
                raise AITimeoutError(f"{error_message} (>{seconds}s)")
        return wrapper
    return decorator


# ==================== Fallback Decorator ====================

def with_fallback(
    fallback_value: Any = None,
    fallback_func: Optional[Callable] = None,
    log_error: bool = True
):
    """
    Decorator for providing fallback on failure
    
    Args:
        fallback_value: Static fallback value
        fallback_func: Async function to call for fallback (receives original args)
        log_error: Whether to log the original error
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.warning(f"Using fallback for {func.__name__} due to: {e}")
                
                if fallback_func:
                    return await fallback_func(*args, **kwargs)
                return fallback_value
        return wrapper
    return decorator


# ==================== Circuit Breaker ====================

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open to close
    timeout: float = 30.0  # Seconds before trying half-open
    

class CircuitBreaker:
    """
    Circuit breaker pattern for AI services
    
    Prevents cascading failures by failing fast when a service is down.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
    
    def can_execute(self) -> bool:
        """Check if request should be allowed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if time.time() - self.last_failure_time >= self.config.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit {self.name} entering half-open state")
                return True
            return False
        
        # Half-open: allow limited requests
        return True
    
    def record_success(self):
        """Record a successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit {self.name} closed (recovered)")
        else:
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} opened (half-open failure)")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} opened (threshold reached)")


# Global circuit breakers for different AI services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name)
    return _circuit_breakers[name]


def with_circuit_breaker(name: str):
    """Decorator for circuit breaker pattern"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            breaker = get_circuit_breaker(name)
            
            if not breaker.can_execute():
                raise AIUnavailableError(f"Service {name} is temporarily unavailable (circuit open)")
            
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise
        return wrapper
    return decorator


# ==================== Safe User Error Messages ====================

USER_FRIENDLY_ERRORS = {
    AITimeoutError: "The AI service is taking longer than expected. Please try again.",
    AIRateLimitError: "We're experiencing high demand. Please wait a moment and try again.",
    AIUnavailableError: "The AI service is temporarily unavailable. Please try again later.",
    Exception: "An error occurred while processing your request. Please try again."
}


def get_safe_error_message(error: Exception) -> str:
    """Get a safe, user-friendly error message"""
    for error_type, message in USER_FRIENDLY_ERRORS.items():
        if isinstance(error, error_type):
            return message
    return USER_FRIENDLY_ERRORS[Exception]


# ==================== Combined Resilient Call ====================

def resilient_ai_call(
    timeout_seconds: float = 30.0,
    max_retries: int = 3,
    circuit_name: Optional[str] = None,
    fallback_value: Any = None
):
    """
    Combined decorator for resilient AI calls with all protections
    
    Example:
        @resilient_ai_call(timeout_seconds=60, max_retries=3, circuit_name="openai")
        async def generate_quiz(content: str) -> Quiz:
            return await openai.generate(...)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Circuit breaker check
            if circuit_name:
                breaker = get_circuit_breaker(circuit_name)
                if not breaker.can_execute():
                    if fallback_value is not None:
                        logger.warning(f"Circuit open for {circuit_name}, using fallback")
                        return fallback_value
                    raise AIUnavailableError(get_safe_error_message(AIUnavailableError()))
            
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout_seconds
                    )
                    
                    # Record success
                    if circuit_name:
                        get_circuit_breaker(circuit_name).record_success()
                    
                    return result
                    
                except asyncio.TimeoutError:
                    last_error = AITimeoutError(f"Request timed out after {timeout_seconds}s")
                    
                except Exception as e:
                    last_error = e
                
                # Should we retry?
                if attempt < max_retries:
                    delay = min(1.0 * (2 ** attempt), 30.0) * (0.5 + random.random())
                    logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.2f}s")
                    await asyncio.sleep(delay)
            
            # All retries failed
            if circuit_name:
                get_circuit_breaker(circuit_name).record_failure()
            
            if fallback_value is not None:
                logger.warning(f"All retries failed for {func.__name__}, using fallback")
                return fallback_value
            
            raise last_error
        
        return wrapper
    return decorator
