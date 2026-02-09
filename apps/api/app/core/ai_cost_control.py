"""
AI Cost Safeguards
Daily token limits, request throttling, caching, and graceful degradation
"""
import hashlib
import json
import time
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from functools import wraps
import asyncio
import logging

from sqlalchemy import Column, String, Integer, Float, Date, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import Base
from app.models.base import TimestampMixin

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class AICostConfig:
    """AI cost control configuration"""
    
    # Daily limits per user
    DAILY_TOKEN_LIMIT: int = 50_000
    DAILY_REQUEST_LIMIT: int = 100
    
    # Per-request limits
    MAX_INPUT_TOKENS: int = 4000
    MAX_OUTPUT_TOKENS: int = 2000
    MAX_CONTEXT_CHUNKS: int = 5
    
    # Throttling
    MIN_REQUEST_INTERVAL_SECONDS: float = 2.0
    BURST_LIMIT: int = 5  # Max requests before throttling
    BURST_WINDOW_SECONDS: int = 10
    
    # Caching
    CACHE_TTL_SECONDS: int = 3600  # 1 hour
    CACHE_SIMILAR_THRESHOLD: float = 0.95
    
    # Cost tracking (per 1K tokens)
    COST_PER_1K_INPUT: float = 0.01  # GPT-4 Turbo pricing
    COST_PER_1K_OUTPUT: float = 0.03
    DAILY_BUDGET_USD: float = 50.0  # Platform-wide
    
    # Degradation thresholds
    SOFT_LIMIT_PERCENT: float = 80  # Start limiting at 80% budget
    HARD_LIMIT_PERCENT: float = 95  # Stop at 95%


AI_COST_CONFIG = AICostConfig()


# ============================================================
# DATABASE MODEL FOR USAGE TRACKING
# ============================================================

class AIUsageLog(Base, TimestampMixin):
    """Track AI usage per user per day"""
    __tablename__ = "ai_usage_logs"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Token usage
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    tokens_total = Column(Integer, default=0)
    
    # Request counts
    request_count = Column(Integer, default=0)
    cached_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Cost tracking
    estimated_cost_usd = Column(Float, default=0.0)
    
    # Timestamps
    last_request_at = Column(DateTime(timezone=True), nullable=True)


class DailyAICost(Base, TimestampMixin):
    """Platform-wide daily AI cost tracking"""
    __tablename__ = "daily_ai_costs"
    
    id = Column(String(36), primary_key=True)
    date = Column(Date, nullable=False, unique=True)
    
    total_tokens = Column(Integer, default=0)
    total_requests = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    
    # Status
    budget_status = Column(String(20), default="normal")  # normal, warning, exceeded


# ============================================================
# IN-MEMORY CACHE FOR AI RESPONSES
# ============================================================

class AIResponseCache:
    """Cache AI responses to avoid repeated calls"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self._lock = asyncio.Lock()
    
    def _make_key(self, query: str, context_hash: str = "") -> str:
        """Create cache key from query and context"""
        combined = f"{query.lower().strip()}:{context_hash}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    async def get(self, query: str, context_hash: str = "") -> Optional[Dict]:
        """Get cached response if exists and not expired"""
        async with self._lock:
            key = self._make_key(query, context_hash)
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            if time.time() - entry["timestamp"] > AI_COST_CONFIG.CACHE_TTL_SECONDS:
                del self.cache[key]
                return None
            
            logger.info(f"Cache hit for query: {query[:50]}...")
            return entry["response"]
    
    async def set(self, query: str, response: Dict, context_hash: str = ""):
        """Cache a response"""
        async with self._lock:
            # Evict old entries if at capacity
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
                del self.cache[oldest_key]
            
            key = self._make_key(query, context_hash)
            self.cache[key] = {
                "response": response,
                "timestamp": time.time(),
                "query": query[:100]
            }
    
    async def get_similar(self, query: str) -> Optional[Dict]:
        """Find similar cached query (for fuzzy matching)"""
        # Simple implementation - in production, use vector similarity
        query_words = set(query.lower().split())
        
        async with self._lock:
            best_match = None
            best_score = 0
            
            for key, entry in self.cache.items():
                if time.time() - entry["timestamp"] > AI_COST_CONFIG.CACHE_TTL_SECONDS:
                    continue
                
                cached_words = set(entry["query"].lower().split())
                if not cached_words:
                    continue
                
                # Jaccard similarity
                intersection = len(query_words & cached_words)
                union = len(query_words | cached_words)
                score = intersection / union if union > 0 else 0
                
                if score > best_score and score >= AI_COST_CONFIG.CACHE_SIMILAR_THRESHOLD:
                    best_score = score
                    best_match = entry["response"]
            
            if best_match:
                logger.info(f"Similar cache hit (score={best_score:.2f})")
            
            return best_match


# Global cache instance
ai_cache = AIResponseCache()


# ============================================================
# USAGE TRACKER
# ============================================================

class AIUsageTracker:
    """Track and enforce AI usage limits"""
    
    def __init__(self):
        self.user_usage: Dict[str, Dict] = {}
        self.platform_cost_today: float = 0.0
        self._lock = asyncio.Lock()
    
    async def check_user_limits(self, user_id: str) -> tuple[bool, str]:
        """Check if user is within limits"""
        async with self._lock:
            today = date.today().isoformat()
            key = f"{user_id}:{today}"
            
            usage = self.user_usage.get(key, {"tokens": 0, "requests": 0})
            
            if usage["tokens"] >= AI_COST_CONFIG.DAILY_TOKEN_LIMIT:
                return False, "You've reached your daily AI limit. Resets at midnight."
            
            if usage["requests"] >= AI_COST_CONFIG.DAILY_REQUEST_LIMIT:
                return False, "Maximum daily AI requests reached. Try again tomorrow."
            
            return True, ""
    
    async def check_platform_budget(self) -> tuple[bool, str]:
        """Check platform-wide budget"""
        budget_used = (self.platform_cost_today / AI_COST_CONFIG.DAILY_BUDGET_USD) * 100
        
        if budget_used >= AI_COST_CONFIG.HARD_LIMIT_PERCENT:
            return False, "AI service is temporarily limited. Please try again later."
        
        if budget_used >= AI_COST_CONFIG.SOFT_LIMIT_PERCENT:
            # Soft limit - allow but log warning
            logger.warning(f"Platform AI budget at {budget_used:.1f}%")
        
        return True, ""
    
    async def record_usage(
        self, 
        user_id: str, 
        tokens_input: int, 
        tokens_output: int,
        from_cache: bool = False
    ):
        """Record AI usage"""
        async with self._lock:
            today = date.today().isoformat()
            key = f"{user_id}:{today}"
            
            if key not in self.user_usage:
                self.user_usage[key] = {"tokens": 0, "requests": 0, "cached": 0}
            
            if from_cache:
                self.user_usage[key]["cached"] += 1
            else:
                total_tokens = tokens_input + tokens_output
                self.user_usage[key]["tokens"] += total_tokens
                self.user_usage[key]["requests"] += 1
                
                # Calculate cost
                cost = (
                    (tokens_input / 1000) * AI_COST_CONFIG.COST_PER_1K_INPUT +
                    (tokens_output / 1000) * AI_COST_CONFIG.COST_PER_1K_OUTPUT
                )
                self.platform_cost_today += cost
                
                logger.info(
                    f"AI usage: user={user_id}, tokens={total_tokens}, "
                    f"cost=${cost:.4f}, day_total=${self.platform_cost_today:.2f}"
                )
    
    async def get_user_remaining(self, user_id: str) -> Dict:
        """Get user's remaining quota"""
        today = date.today().isoformat()
        key = f"{user_id}:{today}"
        usage = self.user_usage.get(key, {"tokens": 0, "requests": 0})
        
        return {
            "tokens_remaining": AI_COST_CONFIG.DAILY_TOKEN_LIMIT - usage["tokens"],
            "requests_remaining": AI_COST_CONFIG.DAILY_REQUEST_LIMIT - usage["requests"],
            "tokens_used": usage["tokens"],
            "requests_used": usage["requests"]
        }


# Global tracker
ai_tracker = AIUsageTracker()


# ============================================================
# THROTTLING DECORATOR
# ============================================================

class RequestThrottler:
    """Per-user request throttling"""
    
    def __init__(self):
        self.last_request: Dict[str, float] = {}
        self.burst_requests: Dict[str, list] = {}
        self._lock = asyncio.Lock()
    
    async def check_throttle(self, user_id: str) -> tuple[bool, float]:
        """Check if request should be throttled"""
        async with self._lock:
            now = time.time()
            
            # Clean old burst data
            window_start = now - AI_COST_CONFIG.BURST_WINDOW_SECONDS
            self.burst_requests[user_id] = [
                t for t in self.burst_requests.get(user_id, [])
                if t > window_start
            ]
            
            # Check burst limit
            if len(self.burst_requests[user_id]) >= AI_COST_CONFIG.BURST_LIMIT:
                wait_time = self.burst_requests[user_id][0] - window_start
                return False, wait_time
            
            # Check minimum interval
            last = self.last_request.get(user_id, 0)
            elapsed = now - last
            
            if elapsed < AI_COST_CONFIG.MIN_REQUEST_INTERVAL_SECONDS:
                wait_time = AI_COST_CONFIG.MIN_REQUEST_INTERVAL_SECONDS - elapsed
                return False, wait_time
            
            # Record request
            self.last_request[user_id] = now
            self.burst_requests[user_id].append(now)
            
            return True, 0


throttler = RequestThrottler()


# ============================================================
# COMBINED COST-AWARE AI CALL
# ============================================================

def cost_aware_ai_call(
    cache_enabled: bool = True,
    check_budget: bool = True
):
    """
    Decorator for AI calls with cost safeguards
    
    Applies:
    - User token/request limits
    - Platform budget limits
    - Request throttling
    - Response caching
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user")
            if not user:
                raise ValueError("current_user required for cost tracking")
            
            # 1. Check throttle
            allowed, wait_time = await throttler.check_throttle(user.id)
            if not allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {wait_time:.1f} seconds between requests",
                    headers={"Retry-After": str(int(wait_time) + 1)}
                )
            
            # 2. Check user limits
            allowed, message = await ai_tracker.check_user_limits(user.id)
            if not allowed:
                from fastapi import HTTPException
                remaining = await ai_tracker.get_user_remaining(user.id)
                raise HTTPException(
                    status_code=429,
                    detail=message,
                    headers={"X-Tokens-Remaining": str(remaining["tokens_remaining"])}
                )
            
            # 3. Check platform budget
            if check_budget:
                allowed, message = await ai_tracker.check_platform_budget()
                if not allowed:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=503, detail=message)
            
            # 4. Check cache
            if cache_enabled:
                query = kwargs.get("question") or kwargs.get("query", "")
                cached = await ai_cache.get(query)
                if cached:
                    await ai_tracker.record_usage(user.id, 0, 0, from_cache=True)
                    return cached
            
            # 5. Execute AI call
            result = await func(*args, **kwargs)
            
            # 6. Record usage
            tokens_input = getattr(result, "tokens_input", 1000)
            tokens_output = getattr(result, "tokens_output", 500)
            await ai_tracker.record_usage(user.id, tokens_input, tokens_output)
            
            # 7. Cache result
            if cache_enabled:
                await ai_cache.set(query, result)
            
            return result
        
        return wrapper
    return decorator


# ============================================================
# GRACEFUL DEGRADATION
# ============================================================

class GracefulDegradation:
    """Provide fallback responses when AI is unavailable"""
    
    FALLBACK_RESPONSES = {
        "rag_query": "I'm temporarily unable to analyze your documents. "
                     "Please try again in a few minutes, or review the source material directly.",
        
        "quiz_generation": "Quiz generation is temporarily limited. "
                          "Please try with a smaller content selection or try again later.",
        
        "explanation": "I'm unable to provide a detailed explanation right now. "
                      "Here are the key points from your study material: {context_summary}",
    }
    
    @classmethod
    def get_fallback(cls, operation: str, context: Dict = None) -> str:
        """Get fallback response for an operation"""
        template = cls.FALLBACK_RESPONSES.get(operation, 
            "This feature is temporarily unavailable. Please try again later.")
        
        if context:
            try:
                return template.format(**context)
            except KeyError:
                return template.replace("{context_summary}", "See your uploaded materials.")
        
        return template
    
    @classmethod
    async def degraded_quiz(cls, content: str, question_count: int = 5) -> Dict:
        """Generate simple quiz without AI when limits exceeded"""
        # Basic keyword extraction for simple questions
        words = content.split()
        key_terms = [w for w in words if len(w) > 6 and w[0].isupper()][:question_count]
        
        questions = []
        for i, term in enumerate(key_terms):
            questions.append({
                "question": f"Which of the following is related to {term}?",
                "options": [
                    f"Related to {term}",
                    "Not mentioned in the material",
                    "Opposite concept",
                    "Unrelated topic"
                ],
                "correct": 0,
                "explanation": "Please review the study material for details."
            })
        
        return {
            "questions": questions,
            "degraded": True,
            "message": "This is a simplified quiz. Full AI-generated quizzes will be available soon."
        }


# ============================================================
# API ENDPOINT FOR USAGE INFO
# ============================================================

"""
# Add to your router:

@router.get("/ai/usage")
async def get_ai_usage(current_user: User = Depends(get_current_user)):
    '''Get current user's AI usage and remaining quota'''
    remaining = await ai_tracker.get_user_remaining(current_user.id)
    
    return {
        "daily_limit": {
            "tokens": AI_COST_CONFIG.DAILY_TOKEN_LIMIT,
            "requests": AI_COST_CONFIG.DAILY_REQUEST_LIMIT
        },
        "used": {
            "tokens": remaining["tokens_used"],
            "requests": remaining["requests_used"]
        },
        "remaining": {
            "tokens": remaining["tokens_remaining"],
            "requests": remaining["requests_remaining"]
        },
        "resets_at": "midnight UTC"
    }
"""
