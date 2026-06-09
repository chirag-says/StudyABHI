# 🔥 StudyABHI — Revival Plan

> **Mission:** Transform a broken prototype into a polished, production-ready UPSC study companion that one person will genuinely love using.
> **Philosophy:** FireRed Mode — every line earns its place, build the smallest engine that produces the largest world.

---

## 1. Full Codebase Audit

### What Actually Works ✅

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI app shell | ✅ Boots | Lifespan, CORS, error handlers are solid |
| SQLite database | ✅ Working | SQLite for dev, schema auto-creates |
| Auth (JWT) | ✅ Working | Login/register, token refresh, password hashing |
| User model | ✅ Working | Full CRUD |
| PDF upload + extraction | ✅ Working | PyMuPDF-based, chunking works |
| Document CRUD | ✅ Working | Upload, list, delete |
| NVIDIA Kimi K2.5 client | ✅ Working | Streaming + non-streaming, retry logic |
| Chat endpoint (`/chat/general`) | ✅ Working | Connects to NVIDIA, has streaming SSE variant |
| Next.js frontend shell | ✅ Boots | Auth, sidebar, routing, dashboard |
| Study page (chat UI) | ✅ Renders | Markdown rendering, citation display, feedback |

### What's Broken 🔴

| Component | Problem | Severity |
|-----------|---------|----------|
| **Background task DB session** | `_process_document_background` receives a session that dies when the request ends | 🔴 Critical |
| **Embedding not auto-triggered** | After PDF processing → chunks exist in DB but are never vectorized automatically | 🔴 Critical |
| **RAG pipeline recreated per request** | `EmbeddingPipeline` + FAISS index re-initialized on every `/rag/query` call — loses all vectors | 🔴 Critical |
| **sentence-transformers heavy load** | The `all-MiniLM-L6-v2` model is loaded locally — 400MB+ download, slow on CPU, blocks the event loop | 🟠 High |
| **FAISS vector store is in-memory** | Vectors are lost on every server restart unless manually saved | 🟠 High |
| **Quiz service uses MockLLMClient** | Quiz generation returns placeholder text, not real questions | 🟠 High |
| **Summarizer uses MockLLMClient** | Same problem — no real summaries | 🟠 High |
| **Quiz results don't update learning state** | `TopicProficiency`, `AdaptiveLearningState` never updated after quiz | 🟠 High |
| **Roadmap service disconnected** | Generates plans but has no feedback loop from actual study activity | 🟡 Medium |
| **Debug print statements in pipeline** | `print(f"DEBUG: ...")` scattered in `pipeline.py` | 🟡 Medium |
| **NVIDIA API key hardcoded in `.env`** | Exposed in repo (though it's a dev key) | 🟡 Medium |

### What's Scaffolded But Empty 🟡

| Component | Reality |
|-----------|---------|
| `services/rag-service/` | Just a `README.md` — no code |
| `services/quiz-generator/` | Just a `README.md` — no code |
| `services/summarizer/` | Just a `README.md` — no code |
| `packages/shared-utils/` | Doesn't exist |
| `packages/ui-components/` | Doesn't exist |
| `infrastructure/` | Doesn't exist |
| `study-materials/` | 12 empty subject folders — no actual PDFs inside |

### Frontend Issues

| Component | Problem |
|-----------|---------|
| **Study page posts to `/rag/query`** | But RAG pipeline has no persistent vectors → always returns "I couldn't find relevant information" |
| **Dashboard shows mock data on failure** | Catches API errors and silently shows fake stats |
| **Quiz pages** | UI exists but backend returns mock questions |
| **Roadmap pages** | UI exists but roadmap generation has no real AI backing |
| **Study Room** | Page exists but functionality is unclear/broken |
| **Materials page** | Exists but disconnected from actual content |

---

## 2. Architecture Decisions

### The Big Simplification

This is for **one person**. That changes everything.

> [!IMPORTANT]
> We do NOT need: Kubernetes, Terraform, microservices, Qdrant, Redis, PostgreSQL connection pooling, rate limiting at scale, multi-tenant isolation, or separate AI service containers.

**What we actually need:**

```
┌────────────────────────────────────────────────────────┐
│                    StudyABHI                            │
│                                                        │
│  ┌──────────┐     ┌──────────────┐    ┌─────────────┐  │
│  │ Next.js  │────▶│  FastAPI     │───▶│  SQLite DB  │  │
│  │ Frontend │◀────│  Backend     │    │  (Local)    │  │
│  └──────────┘     │              │    └─────────────┘  │
│                   │  + FAISS     │                      │
│                   │  (Persisted  │    ┌─────────────┐  │
│                   │   to Disk)   │───▶│  NVIDIA     │  │
│                   │              │    │  build APIs  │  │
│                   └──────────────┘    └─────────────┘  │
│                                                        │
│  Local Machine (i7, 14GB RAM, Windows)                 │
└────────────────────────────────────────────────────────┘
```

### NVIDIA API Strategy

From [build.nvidia.com](https://build.nvidia.com), we'll use:

| Need | NVIDIA API | Why |
|------|-----------|-----|
| **Chat/Tutor/Quiz/Summary** | `moonshotai/kimi-k2.5` (already configured) | Free tier, thinking model, great for structured UPSC answers |
| **Embeddings** | `nvidia/nv-embedqa-e5-v5` or `nvidia/llama-3.2-nv-embedqa-1b-v2` | NVIDIA provides embedding APIs — **eliminates the need to run sentence-transformers locally** |
| **Reranking (optional)** | `nvidia/nv-rerankqa-mistral-4b-v3` | Can improve RAG quality for free |

> [!TIP]
> **Key insight:** By using NVIDIA's embedding API instead of local `sentence-transformers`, we:
> 1. Remove ~400MB model download
> 2. Eliminate CPU-blocking embedding operations
> 3. Get better quality embeddings (1024-dim vs 384-dim)
> 4. Make the app start instantly (no model loading)
> 5. Reduce RAM usage significantly on her machine

### What We're Cutting (Dead Weight)

| Remove | Reason |
|--------|--------|
| `services/rag-service/`, `services/quiz-generator/`, `services/summarizer/` | Empty shells. All AI logic lives in `apps/api/app/services/ai/` already |
| `packages/shared-utils/`, `packages/ui-components/` | Don't exist. Not needed for single-user app |
| `infrastructure/` | No cloud deployment planned |
| Docker references in docker-compose for Qdrant | Using FAISS locally instead |
| `sentence-transformers` + `faiss-cpu` from requirements | Replacing with NVIDIA embedding API |
| `attention_service.py` | 28KB of complex attention tracking — overkill for one user |
| `privacy_service.py` | GDPR compliance for single-user app is unnecessary |
| `adaptive_engine.py` | 26KB of adaptive learning — can be simplified drastically |

---

## 3. Core Features That Matter (For Her)

Thinking from her perspective — what does a UPSC aspirant actually need?

### Must-Have (Phase 1-3) 🎯

1. **Upload PDFs and study materials** → Auto-indexed, searchable
2. **Ask AI anything about UPSC** → General chat (no docs needed)
3. **Ask AI about uploaded materials** → RAG-powered Q&A with citations
4. **Generate quizzes from materials** → Real AI-generated MCQs & subjective Qs
5. **Get summaries of uploaded PDFs** → Concise, exam-ready notes
6. **Study roadmap** → AI-generated personalized study plan

### Nice-to-Have (Phase 4-6) ✨

7. **Quiz history & performance tracking** → See progress over time
8. **Topic-wise proficiency** → Know weak areas
9. **Streaming AI responses** → Real-time "typing" effect
10. **Hindi/Hinglish support** → Already scaffolded, just needs real LLM
11. **Pre-loaded UPSC syllabus structure** → Already exists in `upsc_syllabus_data.py`
12. **Beautiful, motivating UI** → She should feel excited opening this app

---

## 4. Phased Execution Plan

### Phase 1: Foundation Fix (Backend Core)
> **Goal:** Make the API actually work end-to-end. Boot → Upload PDF → Auto-embed → Query → Get real answers.

**Tasks:**
1. Fix background task DB session management (create new session per task)
2. Replace local `sentence-transformers` with NVIDIA Embedding API
3. Make FAISS vector store persist to disk reliably (auto-save/load on startup)
4. Create a singleton RAG pipeline (app-level, not per-request)
5. Auto-trigger embedding after document processing
6. Wire quiz generation to real NVIDIA LLM (remove MockLLMClient usage)
7. Wire summarizer to real NVIDIA LLM
8. Remove all `print(f"DEBUG: ...")` statements, use proper logging
9. Clean up `.env` — remove hardcoded API key from repo

**Test Criteria:**
- `POST /api/v1/documents/upload` → Upload a PDF → It gets chunked AND embedded automatically
- `POST /api/v1/rag/query` → Ask about uploaded content → Get a real AI answer with citations
- `POST /api/v1/chat/general` → Ask a general UPSC question → Get real answer
- `POST /api/v1/quiz/generate` → Generate a quiz on a topic → Get real questions
- Server restart → Vectors survive (persisted FAISS)

---

### Phase 2: Frontend ↔ Backend Connection
> **Goal:** Every button on the frontend actually does something real.

**Tasks:**
1. Fix Study Page → Use correct API flow (upload → auto-embed → chat works)
2. Fix Dashboard → Show real stats from DB (remove mock data fallback)
3. Fix Quiz Page → Connect to real quiz generation + evaluation
4. Fix Upload Page → Show processing status, auto-redirect to study
5. Ensure streaming chat works end-to-end (SSE from NVIDIA → backend → frontend)
6. Fix sidebar navigation — ensure all links go to working pages

**Test Criteria:**
- Upload PDF → See it in dashboard → Click → Ask questions → Get real answers
- Generate quiz → Take quiz → See score
- Dashboard shows real stats

---

### Phase 3: Study Roadmap & Syllabus
> **Goal:** AI-generated personalized study plan that actually helps.

**Tasks:**
1. Wire roadmap generation to NVIDIA LLM
2. Connect `upsc_syllabus_data.py` to roadmap service
3. Create simple onboarding flow: "Which subjects have you covered?" → generate personalized plan
4. Daily tasks → mark complete → track progress
5. Quiz results → update topic proficiency → adjust roadmap

**Test Criteria:**
- Complete onboarding → See personalized daily plan
- Complete a task → Dashboard updates
- Take quiz → Weak topics surface in next day's plan

---

### Phase 4: Polish & UX Magic
> **Goal:** Make her fall in love with the app.

**Tasks:**
1. Redesign landing page — personal, warm, motivating (not generic SaaS)
2. Add smooth transitions and micro-animations
3. Dark mode polish (it uses Tailwind dark mode, ensure consistency)
4. Loading states, empty states, error states — all beautiful
5. Add motivational quotes that rotate daily
6. Study timer integration (Pomodoro)
7. Mobile-responsive polish

**Test Criteria:**
- Visual review — does it feel premium?
- All screens have proper loading/error/empty states
- Works on her laptop's screen resolution

---

### Phase 5: Pre-Loading Content
> **Goal:** She opens the app and there's already useful content waiting.

**Tasks:**
1. Pre-process the UPSC syllabus PDF into the vector store
2. Add the complete UPSC syllabus structure (already in `upsc_syllabus_data.py`)
3. Pre-populate 2-3 important study materials from the `study-materials/` directories
4. Create a "seed database" script she can run on first setup
5. Add suggested questions for each subject

**Test Criteria:**
- Fresh install → Run setup script → App has content ready
- Can ask UPSC questions even without uploading anything

---

### Phase 6: Deployment & Handover
> **Goal:** She can run this on her machine with zero technical knowledge.

**Tasks:**
1. Create a single `setup.bat` / PowerShell script for Windows
2. Script does: install Python deps, install Node deps, create `.env`, seed DB, start servers
3. Create a simple `start.bat` — one-click to launch both backend + frontend
4. Write a simple README just for her (not developer docs)
5. Test on clean Windows machine
6. Share via USB/zip (no Docker needed)

**Test Criteria:**
- Clone repo → Run `setup.bat` → Run `start.bat` → App works at localhost:3000
- She never sees a terminal error

---

## 5. Technical Debt to Clean Up

| Item | Action |
|------|--------|
| Empty `services/` microservices | Delete the folders |
| Empty `packages/` folders | Delete |
| `infrastructure/` references | Remove from README |
| `improved_models.py` (17KB) | Audit — merge into main models or delete |
| `ai_cost_control.py` | Single user = no cost control needed |
| `resilience.py` | 12KB of circuit breakers — overkill, simplify |
| Multiple DB files (`upsc.db`, `upsc_dev.db`, `database.db`) | Consolidate to one |
| `check_users.py`, `test_ai.py`, `test_nvidia.py` | Move to tests/ or delete |
| `reindex_documents.py` | Keep as utility script |

---

## 6. File Count Summary

| Layer | Files | Total Size | Assessment |
|-------|-------|------------|------------|
| Backend endpoints | 16 files | ~190KB | Many are overbuilt |
| Backend services | 18 files | ~250KB | Core of the app, needs fixing |
| Backend models | 12 files | ~90KB | Solid, well-structured |
| Backend schemas | 7 files | ~26KB | Good |
| Frontend pages | ~15 files | ~140KB | Need real data connections |
| Frontend components | ~10 files | ~30KB | Basic but functional |
