"""
Private Beta Middleware & Configuration
Rate limiting, file size limits, AI usage caps, abuse prevention
"""
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Callable
from collections import defaultdict
from dataclasses import dataclass
from functools import wraps

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
import logging

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class BetaLimitsConfig:
    """Private beta limits configuration"""
    
    # Rate Limiting
    REQUESTS_PER_MINUTE: int = 30
    REQUESTS_PER_HOUR: int = 300
    
    # File Upload Limits
    MAX_FILE_SIZE_MB: int = 10
    MAX_FILES_PER_DAY: int = 5
    MAX_TOTAL_STORAGE_MB: int = 100  # Per user
    ALLOWED_EXTENSIONS: set = frozenset({".pdf"})  # MVP: PDF only
    
    # AI Usage Caps
    AI_REQUESTS_PER_HOUR: int = 20
    AI_REQUESTS_PER_DAY: int = 100
    TOKENS_PER_DAY: int = 50000
    MAX_QUESTION_LENGTH: int = 500
    MAX_CONTENT_FOR_QUIZ: int = 30000  # characters
    
    # Quiz Limits
    QUIZ_GENERATIONS_PER_DAY: int = 10
    QUESTIONS_PER_QUIZ_MAX: int = 20
    
    # Abuse Prevention
    MAX_FAILED_LOGINS: int = 5
    LOCKOUT_MINUTES: int = 15
    SUSPICIOUS_PATTERNS_THRESHOLD: int = 10


BETA_CONFIG = BetaLimitsConfig()


# ============================================================
# IN-MEMORY RATE LIMITER (Use Redis in production)
# ============================================================

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.ai_requests: Dict[str, list] = defaultdict(list)
        self.tokens_used: Dict[str, int] = defaultdict(int)
        self.files_uploaded: Dict[str, list] = defaultdict(list)
        self.failed_logins: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(
        self, 
        user_id: str, 
        limit: int, 
        window_seconds: int
    ) -> tuple[bool, int]:
        """Check if user is within rate limit"""
        async with self._lock:
            now = time.time()
            key = f"{user_id}"
            
            # Clean old entries
            self.requests[key] = [
                t for t in self.requests[key] 
                if now - t < window_seconds
            ]
            
            # Check limit
            current_count = len(self.requests[key])
            if current_count >= limit:
                retry_after = int(window_seconds - (now - self.requests[key][0]))
                return False, retry_after
            
            # Record request
            self.requests[key].append(now)
            return True, 0
    
    async def check_ai_limit(self, user_id: str) -> tuple[bool, str]:
        """Check AI usage limits"""
        async with self._lock:
            now = time.time()
            hour_ago = now - 3600
            day_ago = now - 86400
            
            # Clean old entries
            self.ai_requests[user_id] = [
                t for t in self.ai_requests[user_id] if now - t < 86400
            ]
            
            # Check hourly
            hourly_count = sum(1 for t in self.ai_requests[user_id] if t > hour_ago)
            if hourly_count >= BETA_CONFIG.AI_REQUESTS_PER_HOUR:
                return False, "Hourly AI limit reached. Try again in an hour."
            
            # Check daily
            if len(self.ai_requests[user_id]) >= BETA_CONFIG.AI_REQUESTS_PER_DAY:
                return False, "Daily AI limit reached. Try again tomorrow."
            
            # Check tokens
            if self.tokens_used[user_id] >= BETA_CONFIG.TOKENS_PER_DAY:
                return False, "Daily token limit reached. Try again tomorrow."
            
            return True, ""
    
    async def record_ai_usage(self, user_id: str, tokens: int = 0):
        """Record AI API usage"""
        async with self._lock:
            self.ai_requests[user_id].append(time.time())
            self.tokens_used[user_id] += tokens
    
    async def check_file_upload(self, user_id: str) -> tuple[bool, str]:
        """Check file upload limits"""
        async with self._lock:
            now = time.time()
            day_ago = now - 86400
            
            # Clean old entries
            self.files_uploaded[user_id] = [
                t for t in self.files_uploaded[user_id] if now - t < 86400
            ]
            
            if len(self.files_uploaded[user_id]) >= BETA_CONFIG.MAX_FILES_PER_DAY:
                return False, f"Daily upload limit ({BETA_CONFIG.MAX_FILES_PER_DAY} files) reached."
            
            return True, ""
    
    async def record_file_upload(self, user_id: str):
        """Record file upload"""
        async with self._lock:
            self.files_uploaded[user_id].append(time.time())
    
    async def check_failed_login(self, ip: str) -> tuple[bool, int]:
        """Check if IP is locked out"""
        async with self._lock:
            now = time.time()
            lockout_window = BETA_CONFIG.LOCKOUT_MINUTES * 60
            
            # Clean old entries
            self.failed_logins[ip] = [
                t for t in self.failed_logins[ip] if now - t < lockout_window
            ]
            
            if len(self.failed_logins[ip]) >= BETA_CONFIG.MAX_FAILED_LOGINS:
                remaining = int(lockout_window - (now - self.failed_logins[ip][0]))
                return False, remaining
            
            return True, 0
    
    async def record_failed_login(self, ip: str):
        """Record failed login attempt"""
        async with self._lock:
            self.failed_logins[ip].append(time.time())
    
    async def reset_daily_limits(self):
        """Reset daily limits (call from scheduler)"""
        async with self._lock:
            self.tokens_used.clear()
            # Keep hourly data for smoother experience


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============================================================
# RATE LIMITING MIDDLEWARE
# ============================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for all requests"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Get user identifier (IP for anonymous, user_id for authenticated)
        user_id = self._get_user_identifier(request)
        
        # Check rate limit
        allowed, retry_after = await rate_limiter.check_rate_limit(
            user_id,
            BETA_CONFIG.REQUESTS_PER_MINUTE,
            60
        )
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(BETA_CONFIG.REQUESTS_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(
            BETA_CONFIG.REQUESTS_PER_MINUTE - 1
        )
        
        return response
    
    def _get_user_identifier(self, request: Request) -> str:
        """Get user identifier from request"""
        # Try to get from auth header
        auth_header = request.headers.get("authorization", "")
        if auth_header:
            return hashlib.md5(auth_header.encode()).hexdigest()[:16]
        
        # Fallback to IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        return f"ip:{client_ip}"


# ============================================================
# AI USAGE LIMITER DECORATOR
# ============================================================

def ai_rate_limited(func: Callable) -> Callable:
    """Decorator to limit AI endpoint usage"""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract user from kwargs
        request = kwargs.get("request") or (args[0] if args else None)
        user = kwargs.get("current_user")
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        
        # Check AI limits
        allowed, message = await rate_limiter.check_ai_limit(user.id)
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=message,
                headers={"X-AI-Limit-Exceeded": "true"}
            )
        
        # Execute function
        result = await func(*args, **kwargs)
        
        # Record usage (estimate tokens)
        estimated_tokens = 1000  # Default estimate
        if hasattr(result, "usage"):
            estimated_tokens = getattr(result.usage, "total_tokens", 1000)
        
        await rate_limiter.record_ai_usage(user.id, estimated_tokens)
        
        return result
    
    return wrapper


# ============================================================
# FILE UPLOAD VALIDATION
# ============================================================

async def validate_file_upload(
    file_content: bytes,
    filename: str,
    user_id: str,
    user_storage_used: int = 0  # From database
) -> tuple[bool, str]:
    """Validate file upload against beta limits"""
    
    # Check file extension
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext not in BETA_CONFIG.ALLOWED_EXTENSIONS:
        return False, f"Only PDF files allowed during beta. Got: {ext}"
    
    # Check file size
    file_size_mb = len(file_content) / (1024 * 1024)
    if file_size_mb > BETA_CONFIG.MAX_FILE_SIZE_MB:
        return False, f"File too large. Maximum {BETA_CONFIG.MAX_FILE_SIZE_MB}MB allowed."
    
    # Check daily upload limit
    allowed, message = await rate_limiter.check_file_upload(user_id)
    if not allowed:
        return False, message
    
    # Check total storage
    total_storage_mb = (user_storage_used + len(file_content)) / (1024 * 1024)
    if total_storage_mb > BETA_CONFIG.MAX_TOTAL_STORAGE_MB:
        return False, f"Storage limit ({BETA_CONFIG.MAX_TOTAL_STORAGE_MB}MB) reached."
    
    return True, ""


# ============================================================
# ABUSE PREVENTION
# ============================================================

class AbusePrevention:
    """Detect and prevent abuse patterns"""
    
    SUSPICIOUS_PATTERNS = [
        r"ignore previous instructions",
        r"pretend you are",
        r"act as if",
        r"you are now",
        r"disregard all",
        r"forget your instructions",
        r"<script",
        r"javascript:",
        r"onerror=",
        r"SELECT.*FROM",
        r"DROP TABLE",
        r"1=1",
        r"--.*$",
    ]
    
    def __init__(self):
        self.violations: Dict[str, list] = defaultdict(list)
    
    def check_input(self, user_id: str, text: str) -> tuple[bool, str]:
        """Check user input for abuse patterns"""
        import re
        
        text_lower = text.lower()
        
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                self.violations[user_id].append({
                    "time": time.time(),
                    "pattern": pattern,
                    "text_sample": text[:100]
                })
                
                # Check if user should be blocked
                recent_violations = [
                    v for v in self.violations[user_id]
                    if time.time() - v["time"] < 3600
                ]
                
                if len(recent_violations) >= BETA_CONFIG.SUSPICIOUS_PATTERNS_THRESHOLD:
                    logger.warning(f"User {user_id} blocked for abuse")
                    return False, "Your account has been temporarily restricted."
                
                logger.warning(f"Suspicious pattern from {user_id}: {pattern}")
                return True, ""  # Log but allow (soft block after threshold)
        
        return True, ""
    
    def sanitize_for_llm(self, text: str) -> str:
        """Sanitize text before sending to LLM"""
        import re
        import html
        
        # HTML escape
        text = html.escape(text)
        
        # Remove potential injection patterns
        for pattern in self.SUSPICIOUS_PATTERNS:
            text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)
        
        # Limit length
        if len(text) > BETA_CONFIG.MAX_QUESTION_LENGTH:
            text = text[:BETA_CONFIG.MAX_QUESTION_LENGTH] + "..."
        
        return text


abuse_prevention = AbusePrevention()


# ============================================================
# FASTAPI INTEGRATION
# ============================================================

def add_beta_middleware(app):
    """Add all beta protection middleware to FastAPI app"""
    
    # Rate limiting
    app.add_middleware(RateLimitMiddleware)
    
    logger.info("Beta protection middleware added")


# ============================================================
# UPDATED ENDPOINTS EXAMPLE
# ============================================================

"""
# In your endpoint file, use the decorators:

from app.middleware.beta_limits import ai_rate_limited, abuse_prevention

@router.post("/query")
@ai_rate_limited
async def rag_query(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Sanitize input
    sanitized_question = abuse_prevention.sanitize_for_llm(request.question)
    
    # Check for abuse
    ok, msg = abuse_prevention.check_input(current_user.id, request.question)
    if not ok:
        raise HTTPException(status_code=403, detail=msg)
    
    # Proceed with query...
"""


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

"""
# Add to .env for easy adjustment:

# Rate Limits
RATE_LIMIT_REQUESTS_PER_MINUTE=30
RATE_LIMIT_AI_PER_HOUR=20
RATE_LIMIT_AI_PER_DAY=100

# File Limits
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_DAY=5
MAX_STORAGE_PER_USER_MB=100

# AI Limits
AI_TOKENS_PER_DAY=50000
QUIZ_GENERATIONS_PER_DAY=10
"""
