# Architecture Review for Scale

## Current Architecture Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│                     CURRENT ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────────┐    ┌──────────────┐            │
│  │ Next.js │───▶│   FastAPI   │───▶│  PostgreSQL  │            │
│  │ Frontend│    │   Backend   │    │  (SQLite)    │            │
│  └─────────┘    └──────┬──────┘    └──────────────┘            │
│                        │                                        │
│                        ├──────────▶ FAISS (In-Memory)           │
│                        │                                        │
│                        ├──────────▶ OpenAI/Ollama API           │
│                        │                                        │
│                        └──────────▶ File Storage (Local)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔴 Bottlenecks Identified

### 1. Database: SQLite → PostgreSQL (CRITICAL for Production)

**Current Issue:** SQLite doesn't handle concurrent writes well

**When It Breaks:** >10 concurrent users

**Fix Required Before Launch:**
```python
# .env changes
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/upsc_db

# Add connection pooling
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

**Recommendation:** Switch to PostgreSQL NOW (before beta)

---

### 2. Vector Store: FAISS In-Memory

**Current Issue:** 
- Vectors lost on restart
- No user isolation built-in
- Single server only

**When It Breaks:** >1000 documents or server restart

**Fix Options:**

| Option | Effort | Scalability | Recommendation |
|--------|--------|-------------|----------------|
| FAISS + Periodic Save | Low | Medium | OK for MVP |
| ChromaDB (persistent) | Low | Medium | Good for MVP |
| Qdrant (self-hosted) | Medium | High | Post-MVP |
| Pinecone (managed) | Low | Very High | If budget allows |

**MVP Recommendation:** 
```python
# Use ChromaDB with persistence
import chromadb
client = chromadb.PersistentClient(path="./data/chroma")
```

---

### 3. AI Service: Direct API Calls

**Current Issue:**
- No queue for long tasks
- Timeouts on slow AI responses
- No retry mechanism

**When It Breaks:** AI latency spike → user timeouts

**Already Addressed:** `resilience.py` and `ai_cost_control.py` handle this

**Additional Recommendation:**
```python
# For quiz generation (>10s), use background task
@router.post("/quiz/generate")
async def generate_quiz(request: QuizRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(process_quiz_generation, job_id, request)
    return {"job_id": job_id, "status": "processing"}

@router.get("/quiz/status/{job_id}")
async def get_quiz_status(job_id: str):
    # Return status and result when ready
```

---

### 4. Background Jobs: FastAPI BackgroundTasks

**Current Issue:**
- Jobs lost on server restart
- No monitoring
- No retry

**When It Breaks:** Server restart during PDF processing

**MVP OK:** FastAPI BackgroundTasks work for low volume

**Post-MVP:** Upgrade to Celery + Redis
```python
# Install: pip install celery[redis]
from celery import Celery

celery_app = Celery("upsc", broker="redis://localhost:6379/0")

@celery_app.task
def process_document(doc_id: str):
    # Process in background
```

---

### 5. File Storage: Local Filesystem

**Current Issue:**
- Files lost if server changes
- Not CDN-ready
- Manual backup needed

**When It Breaks:** Server migration

**MVP OK:** Local storage is fine

**Post-Launch:** Move to S3-compatible storage
```python
import boto3

s3 = boto3.client('s3', 
    endpoint_url="https://s3.amazonaws.com",
    aws_access_key_id="...",
    aws_secret_access_key="..."
)

async def upload_to_s3(file_content: bytes, filename: str) -> str:
    key = f"documents/{uuid4()}/{filename}"
    s3.put_object(Bucket="upsc-docs", Key=key, Body=file_content)
    return f"s3://upsc-docs/{key}"
```

---

## 🟢 What's Already Good

| Component | Status | Notes |
|-----------|--------|-------|
| API Structure | ✅ | Clean FastAPI with routers |
| Auth | ✅ | JWT-based, refresh tokens |
| Async DB | ✅ | Using async SQLAlchemy |
| Logging | ✅ | Structured logging added |
| Rate Limiting | ✅ | Beta limits implemented |
| Error Handling | ✅ | Resilience patterns added |

---

## 📊 Scaling Phases

### Phase 1: Launch (0-100 users)
```
Current setup is fine with these changes:
- PostgreSQL instead of SQLite
- ChromaDB for vector persistence
- Basic monitoring (logs + Sentry)
```

### Phase 2: Growth (100-1,000 users)
```
- Add Redis for caching + sessions
- Move to managed database (RDS/Supabase)
- Add CDN for static files
- Consider Celery for background jobs
```

### Phase 3: Scale (1,000-10,000 users)
```
- Horizontal API scaling (multiple instances)
- Managed vector DB (Pinecone/Qdrant Cloud)
- Database read replicas
- Queue-based AI processing
- CDN for file delivery
```

### Phase 4: Enterprise (10,000+ users)
```
- Kubernetes deployment
- Multi-region
- Dedicated AI infrastructure
- Advanced caching layers
- Event-driven architecture
```

---

## 🏗️ Recommended Production Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   RECOMMENDED ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐                                                   │
│  │  Vercel  │ (Frontend)                                        │
│  └────┬─────┘                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────┐    ┌───────────────────────────────────┐         │
│  │ Railway/ │───▶│         FastAPI Backend           │         │
│  │ Render   │    │  (2+ instances with load balancer)│         │
│  └──────────┘    └───────────────┬───────────────────┘         │
│                                  │                              │
│       ┌──────────────────────────┼──────────────────────┐      │
│       │                          │                      │      │
│       ▼                          ▼                      ▼      │
│  ┌──────────┐            ┌──────────────┐        ┌──────────┐ │
│  │  Redis   │            │  PostgreSQL  │        │ Qdrant/  │ │
│  │ (Cache)  │            │  (Supabase)  │        │ Pinecone │ │
│  └──────────┘            └──────────────┘        └──────────┘ │
│                                                                 │
│       ┌──────────────────────────────────────────────────┐     │
│       │                  S3/Cloudflare R2                │     │
│       │                  (File Storage)                  │     │
│       └──────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✅ Changes Required Before Launch

### Must Do (Before Beta)
| Change | Effort | Why |
|--------|--------|-----|
| PostgreSQL | 1 day | SQLite won't scale |
| Persist vectors | 2 hours | Survive restarts |
| Add Sentry | 1 hour | Error monitoring |

### Should Do (Within 2 Weeks)
| Change | Effort | Why |
|--------|--------|-----|
| Redis caching | 4 hours | Performance |
| S3 storage | 4 hours | File persistence |
| Health checks | 2 hours | Monitoring |

### Can Wait (Post-Launch)
| Change | Effort | Why |
|--------|--------|-----|
| Celery | 1 day | Background jobs |
| Managed vector DB | 2 days | Scale beyond 10K docs |
| Read replicas | 2 days | Database scaling |

---

## 💰 Estimated Infrastructure Costs

### MVP (0-100 users)
| Service | Provider | Cost/Month |
|---------|----------|------------|
| Backend | Railway | $5-20 |
| Database | Supabase Free | $0 |
| Frontend | Vercel Free | $0 |
| AI | OpenAI | $20-50 |
| **Total** | | **$25-70** |

### Growth (100-1,000 users)
| Service | Provider | Cost/Month |
|---------|----------|------------|
| Backend | Railway Pro | $20-50 |
| Database | Supabase Pro | $25 |
| Redis | Upstash | $10 |
| Storage | R2 | $5 |
| AI | OpenAI | $100-300 |
| **Total** | | **$160-390** |

---

## 🎯 Summary

### For MVP Launch:
1. ✅ Switch to PostgreSQL
2. ✅ Add ChromaDB persistence
3. ✅ Set up error monitoring
4. ✅ Deploy with single instance

### Current architecture is FINE for:
- First 500 users
- First 2,000 documents
- First 10,000 AI queries/day

### Don't over-engineer. Launch first, scale as needed.
