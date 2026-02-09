# UPSC AI Platform - Scalability Guide

## Overview

This guide provides actionable steps for scaling the UPSC AI Platform to handle increased load, optimize costs, and ensure reliable performance.

---

## 1. 🚀 Caching Strategy

### 1.1 Redis Caching Layer

**Install Redis:**
```bash
pip install redis aioredis
```

**Implementation:**

```python
# app/core/cache.py
import json
import hashlib
from typing import Optional, Any
from datetime import timedelta
import aioredis

class CacheService:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = None
        self.redis_url = redis_url
    
    async def connect(self):
        self.redis = await aioredis.from_url(self.redis_url)
    
    async def get(self, key: str) -> Optional[Any]:
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        await self.redis.set(key, json.dumps(value), ex=ttl)
    
    async def delete(self, key: str):
        await self.redis.delete(key)
    
    def cache_key(self, prefix: str, *args) -> str:
        """Generate consistent cache key"""
        content = ":".join(str(a) for a in args)
        return f"{prefix}:{hashlib.md5(content.encode()).hexdigest()}"

# Singleton
cache = CacheService()
```

### 1.2 What to Cache

| Data Type | TTL | Priority |
|-----------|-----|----------|
| Syllabus data | 24 hours | High |
| Static content | 1 hour | High |
| Quiz questions | 30 min | Medium |
| User session data | 15 min | Medium |
| AI responses | 5 min | Low |
| Vector search results | 10 min | High |

### 1.3 Cache Decorator

```python
# app/core/decorators.py
from functools import wraps
from app.core.cache import cache

def cached(prefix: str, ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = cache.cache_key(prefix, *args, *kwargs.values())
            
            # Try cache first
            result = await cache.get(key)
            if result:
                return result
            
            # Execute and cache
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator

# Usage:
@cached("syllabus", ttl=86400)
async def get_syllabus(exam_type: str):
    # DB query here
    pass
```

---

## 2. 📬 Async Queue System

### 2.1 Celery + Redis Setup

**Install:**
```bash
pip install celery[redis]
```

**Configuration:**

```python
# app/core/celery_app.py
from celery import Celery

celery_app = Celery(
    "upsc_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_routes={
        "app.tasks.ai.*": {"queue": "ai"},
        "app.tasks.export.*": {"queue": "export"},
        "app.tasks.notification.*": {"queue": "notifications"},
    },
)
```

### 2.2 Background Tasks

```python
# app/tasks/ai_tasks.py
from app.core.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3)
def generate_quiz_async(self, user_id: str, topic_id: str, num_questions: int):
    """Generate quiz in background"""
    try:
        # AI generation logic
        quiz = generate_quiz(topic_id, num_questions)
        # Store in DB
        save_quiz(user_id, quiz)
        # Notify user
        send_notification(user_id, "Quiz ready!")
    except Exception as e:
        self.retry(countdown=60)

@celery_app.task
def process_document_async(document_id: str):
    """Process uploaded document for RAG"""
    # Extract text
    # Generate embeddings
    # Store in vector DB
    pass

@celery_app.task
def export_user_data_async(export_id: str):
    """Process data export request"""
    pass
```

### 2.3 Worker Commands

```bash
# Start workers
celery -A app.core.celery_app worker --loglevel=info --queues=ai -c 2
celery -A app.core.celery_app worker --loglevel=info --queues=export -c 1
celery -A app.core.celery_app worker --loglevel=info --queues=notifications -c 1

# Beat scheduler for periodic tasks
celery -A app.core.celery_app beat --loglevel=info
```

---

## 3. 🔍 Vector Database Scaling

### 3.1 Current: ChromaDB (Development)

Good for up to 100K vectors on single machine.

### 3.2 Scale Option 1: Qdrant (Recommended)

**Why Qdrant?**
- Horizontal scaling
- Filtering support
- Production-ready
- gRPC support for speed

**Setup:**
```yaml
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
```

**Client:**
```python
# app/services/vector_store.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class VectorStore:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
    
    async def create_collection(self, name: str, vector_size: int = 1536):
        self.client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
    
    async def upsert(self, collection: str, points: list):
        self.client.upsert(collection_name=collection, points=points)
    
    async def search(self, collection: str, vector: list, limit: int = 10):
        return self.client.search(
            collection_name=collection,
            query_vector=vector,
            limit=limit
        )
```

### 3.3 Scale Option 2: Pinecone (Managed)

For fully managed, serverless vector search:

```python
import pinecone

pinecone.init(api_key="xxx", environment="us-west1-gcp")
index = pinecone.Index("upsc-content")

# Upsert
index.upsert(vectors=[("id1", [0.1, 0.2, ...], {"topic": "polity"})])

# Query
results = index.query(vector=[0.1, 0.2, ...], top_k=10, filter={"topic": "polity"})
```

### 3.4 Scaling Strategy

| Users | Vectors | Solution |
|-------|---------|----------|
| < 1K | < 100K | ChromaDB (local) |
| 1K - 10K | 100K - 1M | Qdrant (single node) |
| 10K - 100K | 1M - 10M | Qdrant (cluster) or Pinecone |
| > 100K | > 10M | Pinecone (managed) |

---

## 4. 💰 Cost Optimization

### 4.1 LLM Cost Reduction

**Strategy 1: Response Caching**
```python
# Cache identical or similar queries
@cached("llm_response", ttl=300)
async def get_ai_response(query_hash: str, context_hash: str):
    return await call_llm(query, context)
```

**Strategy 2: Model Tiering**
```python
class LLMRouter:
    """Route to appropriate model based on task complexity"""
    
    def select_model(self, task_type: str, complexity: str):
        if task_type == "simple_qa":
            return "gpt-3.5-turbo"  # $0.002/1K tokens
        elif task_type == "quiz_generation":
            return "gpt-4-turbo"    # $0.01/1K tokens
        elif complexity == "high":
            return "gpt-4"          # $0.03/1K tokens
        return "gpt-3.5-turbo"
```

**Strategy 3: Prompt Optimization**
- Keep prompts under 500 tokens
- Use few-shot instead of long instructions
- Batch similar requests

### 4.2 Infrastructure Cost Reduction

| Component | Dev Cost | Prod Optimization |
|-----------|----------|-------------------|
| Database | $0 (SQLite) | $15/mo (managed Postgres) |
| Redis | $0 (local) | $10/mo (Railway) |
| Vector DB | $0 (Chroma) | $25/mo (Qdrant Cloud) |
| API Server | $0 (local) | $20/mo (Railway) |
| Workers | - | $10/mo (background jobs) |
| **Total** | **$0** | **~$80/mo** |

### 4.3 Auto-Scaling Configuration

```yaml
# railway.json
{
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/v1/health",
    "restartPolicyType": "ON_FAILURE"
  },
  "autoscaling": {
    "minInstances": 1,
    "maxInstances": 5,
    "targetCPU": 70
  }
}
```

---

## 5. 📊 Monitoring & Observability

### 5.1 Prometheus Metrics

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter(
    "http_requests_total", 
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency",
    ["endpoint"]
)

ACTIVE_USERS = Gauge("active_users", "Currently active users")
CACHE_HIT_RATE = Gauge("cache_hit_rate", "Cache hit percentage")
```

### 5.2 Health Check Endpoints

```python
@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    checks = {
        "database": await check_db(db),
        "redis": await check_redis(),
        "vector_db": await check_vector_db(),
    }
    
    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    raise HTTPException(503, {"status": "not_ready", "checks": checks})
```

---

## 6. 🔄 Database Optimization

### 6.1 Connection Pooling

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

### 6.2 Read Replicas

```python
# app/core/database.py
class DatabaseRouter:
    def __init__(self):
        self.write_engine = create_async_engine(WRITE_DB_URL)
        self.read_engine = create_async_engine(READ_DB_URL)
    
    def get_engine(self, write: bool = False):
        return self.write_engine if write else self.read_engine
```

### 6.3 Query Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_quiz_user_date ON quiz_attempts(user_id, created_at DESC);
CREATE INDEX idx_content_topic ON contents(topic_id, is_published);
```

---

## 7. 📋 Implementation Checklist

### Phase 1: Quick Wins (Week 1)
- [ ] Add Redis caching for syllabus and content
- [ ] Implement response caching for AI endpoints
- [ ] Add database indexes
- [ ] Set up health checks

### Phase 2: Background Processing (Week 2)
- [ ] Set up Celery with Redis
- [ ] Move AI generation to background tasks
- [ ] Move data exports to background
- [ ] Add notification queue

### Phase 3: Vector DB Scaling (Week 3)
- [ ] Migrate to Qdrant
- [ ] Implement vector search caching
- [ ] Add collection partitioning

### Phase 4: Monitoring (Week 4)
- [ ] Add Prometheus metrics
- [ ] Set up Grafana dashboards
- [ ] Configure alerting
- [ ] Add log aggregation

---

## 8. 🏗️ Architecture Diagram

```
                                    ┌─────────────────┐
                                    │   Load Balancer │
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
            ┌───────▼───────┐       ┌───────▼───────┐       ┌───────▼───────┐
            │   API Pod 1   │       │   API Pod 2   │       │   API Pod N   │
            └───────┬───────┘       └───────┬───────┘       └───────┬───────┘
                    │                        │                        │
                    └────────────────────────┼────────────────────────┘
                                             │
        ┌────────────────────────────────────┼────────────────────────────────────┐
        │                                    │                                     │
┌───────▼───────┐                  ┌────────▼────────┐                   ┌────────▼────────┐
│ Redis Cache   │                  │ PostgreSQL      │                   │ Qdrant          │
│ (Session/Cache)│                  │ (Primary + Read)│                   │ (Vector Store)  │
└───────────────┘                  └─────────────────┘                   └─────────────────┘
        │
        │
┌───────▼──────────────┐
│ Celery Workers       │
│ ├─ AI Queue          │
│ ├─ Export Queue      │
│ └─ Notification Queue│
└──────────────────────┘
```

---

## Summary

| Optimization | Impact | Effort | Priority |
|--------------|--------|--------|----------|
| Redis Caching | High | Low | 🔴 Critical |
| Background Queues | High | Medium | 🔴 Critical |
| Vector DB Migration | Medium | Medium | 🟡 High |
| LLM Cost Optimization | High | Low | 🔴 Critical |
| Database Indexing | Medium | Low | 🟡 High |
| Monitoring | Medium | Medium | 🟢 Medium |

Start with caching and background queues for immediate impact!
