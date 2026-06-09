# StudyABHI — Implementation Plan (For Sonnet Execution)

> **Project root:** `d:\ForImpPerson\upsc-ai-platform`  
> **For:** Abhitha (UPSC aspirant, single user)  
> **AI Provider:** NVIDIA build.nvidia.com (free tier)  
> **Stack:** FastAPI + Next.js + SQLite + FAISS  
> Execute phases in order. Test each phase before moving to the next.

---

## Context & Decisions (Read First)

### Existing State
- **77 study material PDFs** (886MB) in `study-materials/` — NCERTs, Vision IAS PT365 books across History, Geography, Polity, Economy, Science, Environment, IR, Sociology, Social Issues
- **Database** (`upsc.db`, 3.8MB): 2 users (Chirag + Abhitha), 16 documents uploaded, 5595 chunks extracted, 3 quizzes, 1 study plan — **start fresh**, this is test data
- **3 SQLite DBs exist** (`upsc.db`, `upsc_dev.db`, `database.db`) — delete all, start with clean `upsc.db`
- **NVIDIA API key** already configured in `.env` — keep using it, just don't hardcode in repo
- **Empty scaffolding** exists: `services/rag-service/`, `services/quiz-generator/`, `services/summarizer/`, most of `packages/` — delete these

### Architecture (Single User, No Cloud)
```
Next.js Frontend → FastAPI Backend → SQLite (local)
                                   → FAISS (persisted to disk)  
                                   → NVIDIA APIs (chat, embeddings, quiz gen)
```

No Docker, no Redis, no PostgreSQL, no Kubernetes needed.

### NVIDIA APIs to Use
| Purpose | API Endpoint | Model |
|---------|-------------|-------|
| Chat/Tutor/Quiz/Summary | `https://integrate.api.nvidia.com/v1/chat/completions` | `moonshotai/kimi-k2.5` |
| Embeddings | `https://integrate.api.nvidia.com/v1/embeddings` | `nvidia/nv-embedqa-e5-v5` |

---

## Phase 1: Backend Foundation Fix

**Goal:** Upload PDF → auto-chunk → auto-embed → RAG query returns real AI answer.

### Task 1.1 — Replace Local Embeddings with NVIDIA API

**File:** `apps/api/app/services/rag/embeddings.py`

Replace the `EmbeddingModel` class. Remove `sentence_transformers` import. New class should:
- Call `POST https://integrate.api.nvidia.com/v1/embeddings` with `model: "nvidia/nv-embedqa-e5-v5"`
- Auth header: `Bearer {settings.NVIDIA_API_KEY}`
- Accept `List[str]`, return `np.ndarray`
- Batch in groups of 50 (API limit)
- Input type should be `"passage"` for indexing, `"query"` for search
- The embedding dimension is 1024 (update `FAISSVectorStore` default from 384 to 1024)
- Handle errors gracefully with retries

**File:** `apps/api/requirements.txt`
- Remove line: `sentence-transformers>=2.5.0`
- Keep: `faiss-cpu>=1.8.0`, `numpy>=1.26.0`

**File:** `apps/api/app/core/config.py`
- Add field: `NVIDIA_EMBED_MODEL: str = "nvidia/nv-embedqa-e5-v5"`
- Add field: `NVIDIA_EMBED_DIM: int = 1024`
- Add field: `VECTOR_STORAGE_PATH: str = "data/vectors"`

### Task 1.2 — Create Singleton RAG Pipeline

**File:** `apps/api/app/main.py`

In `lifespan()`:
- On startup: create `EmbeddingPipeline` and `RAGPipeline` instances, store on `app.state.rag_pipeline`
- Load persisted FAISS index from `data/vectors/` if it exists
- On shutdown: save FAISS index to disk
- Wrap in try/except so server still starts even if vectors don't exist yet

**File:** `apps/api/app/core/dependencies.py`

Add dependency function:
```python
from fastapi import Request
from app.services.rag.pipeline import RAGPipeline

def get_rag_pipeline(request: Request) -> RAGPipeline:
    pipeline = getattr(request.app.state, 'rag_pipeline', None)
    if pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    return pipeline
```

**File:** `apps/api/app/api/v1/endpoints/rag.py`

Refactor ALL endpoints to use `Depends(get_rag_pipeline)` instead of creating new pipelines inline. Remove all inline `EmbeddingPipeline(...)` and `create_rag_pipeline(...)` calls.

### Task 1.3 — Fix Background Task DB Session

**File:** `apps/api/app/api/v1/endpoints/documents.py`

The `_process_document_background` function receives a request-scoped `db` session that dies after the HTTP response. Fix:

```python
async def _process_document_background(doc_id: str, app_state):
    """Background task with its own DB session."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            service = DocumentService(db)
            await service.process_document(doc_id)
            await db.commit()
            
            # Auto-embed: get chunks and add to vector store
            rag_pipeline = getattr(app_state, 'rag_pipeline', None)
            if rag_pipeline:
                chunks_data = await service.get_document_chunks_for_embedding(doc_id)
                if chunks_data:
                    await rag_pipeline.embedding_pipeline.index_chunks(chunks_data)
                    logger.info(f"Auto-embedded {len(chunks_data)} chunks for doc {doc_id}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Background processing failed: {doc_id} - {e}")
```

Update the callers to pass `request.app.state` instead of `db`:
```python
background_tasks.add_task(_process_document_background, doc.id, request.app.state)
```

Add `request: Request` parameter to the `upload_document` and `trigger_processing` endpoints.

### Task 1.4 — Wire Quiz & Summarizer to Real LLM

**File:** `apps/api/app/api/v1/endpoints/quiz.py`

Find where LLM client is created. Ensure it uses:
```python
if settings.LLM_PROVIDER == "nvidia" and settings.NVIDIA_API_KEY:
    llm_client = NvidiaKimiClient()
else:
    llm_client = MockLLMClient()
```

**File:** `apps/api/app/api/v1/endpoints/tutor.py`

Same pattern — ensure `create_ai_tutor()` gets a real `NvidiaKimiClient`.

**File:** `apps/api/app/services/ai/summarizer.py`

Check the `create_summarizer()` factory function. Ensure it supports `nvidia` provider.

### Task 1.5 — Clean Up Debug Statements

**File:** `apps/api/app/services/rag/pipeline.py`

Remove these lines (~518-527):
```python
print(f"DEBUG: Search Query: {question}")
print(f"DEBUG: Raw Results Count: {len(search_results)}")
for i, res in enumerate(search_results):
    print(f"DEBUG: Result {i}: Score={res.score}, Source={res.metadata.source}")
print(f"DEBUG: Relevant Results after filter ({self.min_relevance_score}): {len(relevant_results)}")
```
Replace with `logger.debug(...)` equivalents.

### Task 1.6 — Database Fresh Start

- Delete files: `apps/api/upsc.db`, `apps/api/upsc_dev.db`, `apps/api/database.db`
- Ensure `apps/api/data/vectors/` directory exists (create if not)
- The app auto-creates tables on startup via `init_db()` in `main.py`

### Task 1.7 — Environment Config

**File:** `apps/api/.env`

Update to (keep existing NVIDIA_API_KEY value but add new fields):
```env
# Application
APP_NAME="StudyABHI"
APP_VERSION="1.0.0"
DEBUG=true
ENVIRONMENT=development

# Server
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# Database
DATABASE_URL=sqlite+aiosqlite:///./upsc.db

# JWT
SECRET_KEY=<keep existing value>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# AI Services - NVIDIA
LLM_PROVIDER=nvidia
LLM_MODEL=moonshotai/kimi-k2.5
NVIDIA_API_KEY=<keep existing value>
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=moonshotai/kimi-k2.5
NVIDIA_EMBED_MODEL=nvidia/nv-embedqa-e5-v5
NVIDIA_EMBED_DIM=1024

# Vector Storage
VECTOR_STORAGE_PATH=data/vectors
```

### Phase 1 Test
```
1. Delete old DBs, start fresh
2. uvicorn app.main:app --reload --port 8000
3. POST /api/v1/auth/register {"email":"abhitha@studyabhi.com","password":"test1234","full_name":"Abhitha"}
4. POST /api/v1/auth/login → get token
5. POST /api/v1/documents/upload (upload a small PDF)
6. Wait 15-30s for background processing + embedding
7. POST /api/v1/rag/query {"question":"<question about the PDF>"}
8. Verify: real AI answer with citations
9. POST /api/v1/chat/general {"question":"What is Article 370?"}
10. Verify: real AI answer (no mock)
11. Restart server → repeat step 7 → vectors persist
```

---

## Phase 2: Frontend ↔ Backend Wiring

**Goal:** Every button does something real. No mock data.

### Task 2.1 — Fix Study Page Response Mapping

**File:** `apps/web/src/app/(protected)/study/[id]/page.tsx`

Line ~116-122: The frontend expects `{ answer, sources }` from `/rag/query`. The backend returns `{ answer, citations, query, context_chunks, model, confidence }`.

Fix the response type and mapping:
```typescript
const response = await api.post<{
    answer: string;
    citations: Array<{chunk_id: string; source: string; snippet: string; relevance_score: number; page_number?: number}>;
}>('/rag/query', {
    question: userMessage.content,
    document_ids: [documentId],
});

// Map citations to the Citation interface used in messages
const mappedCitations = response.data.citations?.map(c => ({
    page: c.page_number || 0,
    text: c.snippet || c.source,
    chunk_id: c.chunk_id,
})) || [];
```

### Task 2.2 — Remove Mock Data from Dashboard

**File:** `apps/web/src/app/(protected)/dashboard/page.tsx`

Lines ~78-97: The catch block sets fake data. Replace with proper empty state:
```typescript
} catch (error) {
    console.error('Failed to fetch dashboard:', error);
    setData({
        stats: { study_hours_week: 0, quizzes_completed: 0, topics_covered: 0, total_topics: 0, avg_score: 0 },
        today_tasks: [],
        recent_documents: [],
        streak_days: 0,
    });
}
```

### Task 2.3 — Create Dedicated AI Chat Page

**Create:** `apps/web/src/app/(protected)/chat/page.tsx`

A general AI chat page (no document required). Similar UI to study page but:
- No document sidebar
- Posts to `/api/v1/chat/general/stream` for streaming SSE
- Full-screen chat layout
- Welcome message: "Hi Abhitha! Ask me anything about UPSC preparation 📚"
- Suggested questions about popular UPSC topics

### Task 2.4 — Fix Sidebar Links

**File:** `apps/web/src/components/layout/Sidebar.tsx`

Ensure navigation items are:
1. Dashboard (`/dashboard`)
2. AI Tutor / Chat (`/chat`) — NEW page from 2.3
3. Upload Materials (`/upload`)
4. My Materials / Study (`/materials`)
5. Quiz (`/quiz`)
6. Study Roadmap (`/roadmap`)
7. Settings (`/settings`)

Remove any links to non-functional pages.

### Task 2.5 — Fix Quiz End-to-End

**Files:** `apps/web/src/app/(protected)/quiz/page.tsx`, `quiz/generate/`, `quiz/[id]/`

- Verify quiz generation calls the correct endpoint
- Verify quiz taking renders real AI-generated questions
- Verify quiz submission and scoring works
- Fix any response shape mismatches between frontend and backend

### Phase 2 Test
```
1. Login → Dashboard shows real stats (or clean zeros/empty state)
2. Upload a PDF → auto-processes → navigate to study page → ask question → get real answer
3. Navigate to /chat → ask "What are Fundamental Rights?" → get real answer
4. Navigate to Quiz → generate quiz → take it → see score
5. All sidebar links go to working pages
```

---

## Phase 3: Roadmap & Learning Loop

**Goal:** AI-generated study plan, quiz results feed back into roadmap.

### Task 3.1 — Wire Roadmap to NVIDIA LLM

**File:** `apps/api/app/services/roadmap_service.py`
**File:** `apps/api/app/api/v1/endpoints/roadmap.py`

- Find where the roadmap/study plan is generated
- Ensure it uses `NvidiaKimiClient` for generation
- Use UPSC syllabus data from `upsc_syllabus_data.py` as context
- Generate a realistic, personalized study plan based on exam date + subjects

### Task 3.2 — Quiz → Proficiency Update

**File:** `apps/api/app/services/quiz_service.py`

After `complete_attempt()`:
- Extract topic tags from the quiz
- Update `TopicProficiency` model: score < 60% → needs_review, > 80% → proficient
- This creates the feedback loop

### Task 3.3 — Roadmap Frontend Fix

**File:** `apps/web/src/app/(protected)/roadmap/page.tsx`

- Ensure it fetches from real API endpoints
- Daily tasks checkable
- Show progress over time

### Phase 3 Test
```
1. Navigate to Roadmap → see generated plan (or create new one)
2. Complete a quiz with low score on a topic
3. Verify that topic shows as "needs review"
```

---

## Phase 4: UI Polish & Personalization

**Goal:** Make Abhitha love opening this app.

### Task 4.1 — Personalize Landing Page

**File:** `apps/web/src/app/page.tsx`

This is NOT a SaaS product. Redesign for a personal companion feel:
- Remove "Join thousands of aspirants" copy
- Warm, personal greeting: "Your UPSC preparation companion"
- Direct login button (she's the only user)
- Beautiful gradient background, subtle animations
- Inspirational quote from an Indian leader

### Task 4.2 — Personalize Dashboard

**File:** `apps/web/src/app/(protected)/dashboard/page.tsx`

- Greeting: "Good morning, Abhitha! 👋" (use user's first name from auth)
- Curated motivational quotes from Indian leaders (APJ Abdul Kalam, Ambedkar, etc.)
- "Today's Focus" section from roadmap
- Study streak visualization

### Task 4.3 — Dark Mode & Visual Consistency

- Review all pages in dark mode — fix any contrast issues
- Add subtle page transition animations
- Loading skeletons instead of plain spinners
- Consistent color palette across all pages

### Task 4.4 — Empty States

Every page needs a beautiful empty state instead of blank screens:
- No documents → "Upload your first study material to get started"
- No quizzes → "Generate your first quiz from uploaded materials"
- No roadmap → "Let's create your personalized study plan"

### Phase 4 Test
```
Visual review of all pages in light + dark mode. App feels premium and personal.
```

---

## Phase 5: Content Pre-loading & Setup

**Goal:** Fresh install has content ready. One-click startup.

### Task 5.1 — Seed Script

**Create:** `apps/api/scripts/seed.py`

Script that:
1. Creates Abhitha's user account (email: `abhitha@studyabhi.com`, password: configurable)
2. Processes the UPSC syllabus PDF (`upsc-syllabus.pdf` in project root)
3. Seeds UPSC syllabus structure into DB from `upsc_syllabus_data.py`
4. Optionally: processes a few key study materials from `study-materials/` (e.g., `Polity/Polity6.pdf`, `History/History6.pdf`)

### Task 5.2 — Windows Startup Scripts

**Create:** `setup.bat` in project root
- Creates Python venv, installs deps
- Installs Node deps
- Creates `.env` from `.env.example` if not exists
- Runs seed script

**Create:** `start.bat` in project root
- Starts FastAPI backend (in one terminal)
- Starts Next.js frontend (in another terminal)
- Prints: "Open http://localhost:3000 to start studying!"

### Task 5.3 — Simple User README

**Create:** `SETUP_GUIDE.md` in project root
- Written for a non-technical person
- Step 1: Install Python, Step 2: Install Node.js, Step 3: Run setup.bat, Step 4: Run start.bat
- With screenshots if possible

### Phase 5 Test
```
1. Delete all DBs and node_modules
2. Run setup.bat → everything installs
3. Run start.bat → both servers start
4. Open localhost:3000 → login with seeded account → content is ready
```

---

## Phase 6: Cleanup & Finalization

### Task 6.1 — Delete Dead Code

Delete these empty/useless directories and files:
- `services/rag-service/` (only has README)
- `services/quiz-generator/` (only has README)
- `services/summarizer/` (only has README)
- `apps/api/check_users.py`
- `apps/api/check_db.py`
- `apps/api/test_ai.py`
- `apps/api/test_nvidia.py`
- `apps/api/database.db`
- `apps/api/upsc_dev.db`

### Task 6.2 — Secure the Repo

- Ensure `.env` is in `.gitignore` (no API keys committed)
- Update `.env.example` with placeholder values
- Remove any hardcoded secrets

### Task 6.3 — Update Root README

Rewrite `README.md` for simplicity:
- What is StudyABHI (1 paragraph)
- How to set up (point to SETUP_GUIDE.md)
- How to get NVIDIA API key (link to build.nvidia.com)
- Feature list
- Remove all references to Kubernetes, Terraform, microservices, JEE, NEET

### Phase 6 Test
```
Full end-to-end test. Clean clone → setup → start → register → upload → study → quiz → roadmap.
```
