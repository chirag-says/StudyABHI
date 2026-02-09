# Backend Codebase Analysis & Flow Review

## Executive Summary

This document analyzes the UPSC AI Platform backend, identifying issues in the end-to-end learning flow, database schema, and provides actionable improvements.

---

## 1. End-to-End Learning Flow Analysis

### Current Flow

```
User Upload PDF → Text Extraction → Chunking → [GAP: Embedding] → RAG Query → Quiz Gen → Evaluation → [GAP: Roadmap Update]
```

### Detailed Flow with Issues

| Step | Component | Status | Issues Found |
|------|-----------|--------|--------------|
| 1. PDF Upload | `document_service.py` | ✅ Working | Minor: Background task DB session issue |
| 2. Text Extraction | `pdf_extractor.py` | ✅ Working | - |
| 3. Chunking | `pdf_extractor.py` | ✅ Working | - |
| 4. **Embedding Storage** | `rag/embeddings.py` | ⚠️ Disconnected | Manual trigger required, no auto-flow |
| 5. RAG Query | `rag/pipeline.py` | ✅ Working | Pipeline recreated on each request |
| 6. Quiz Generation | `quiz_service.py` | ✅ Working | Uses MockLLMClient in production |
| 7. Quiz Evaluation | `quiz_service.py` | ✅ Working | - |
| 8. **Roadmap Update** | N/A | ❌ Missing | No link between quiz results and learning goals |

---

## 2. Critical Issues Identified

### Issue 1: Background Task Database Session (CRITICAL)

**Location:** `documents.py:284-297`

```python
# BROKEN: Background task receives committed session
async def _process_document_background(doc_id: str, db: AsyncSession):
    # This db session may be closed/invalid after the request completes
```

**Fix Required:** Create new session in background task

### Issue 2: Embedding Not Auto-Triggered (HIGH)

After document processing completes, embeddings must be manually triggered via `/rag/index`.

**Missing Link:** `DocumentService.process_document()` should trigger embedding pipeline.

### Issue 3: Quiz Results Don't Update Learning State (HIGH)

**Location:** `quiz_service.py` - `QuizEvaluator.complete_attempt()`

Quiz completion doesn't update:
- `TopicProficiency` table
- `AdaptiveLearningState` table
- `LearningGoal` progress

### Issue 4: RAG Pipeline Recreation (MEDIUM)

**Location:** `rag.py:91-115`

```python
# Created fresh on every request - inefficient
embedding_pipeline = EmbeddingPipeline(...)
rag_pipeline = create_rag_pipeline(...)
```

### Issue 5: User Data Isolation (SECURITY)

Vector store queries don't properly filter by user_id in all cases:
- FAISS doesn't support native filtering
- Must use post-retrieval filtering

---

## 3. Missing Service Connections

```
┌─────────────────────────────────────────────────────────────────┐
│                    MISSING CONNECTIONS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DocumentService ──X──> EmbeddingPipeline                       │
│  (Should auto-embed after processing)                          │
│                                                                 │
│  QuizEvaluator ──X──> TopicProficiency                         │
│  (Should update proficiency after quiz)                        │
│                                                                 │
│  QuizEvaluator ──X──> AdaptiveEngine                           │
│  (Should recalculate recommendations)                          │
│                                                                 │
│  LearningService ──X──> AdaptiveEngine                         │
│  (Should update state after study session)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. User Isolation Audit

### ✅ Properly Isolated

| Table | Isolation Method |
|-------|------------------|
| `documents` | `user_id` filter in queries |
| `quizzes` | `created_by` filter |
| `quiz_attempts` | `user_id` filter |
| `study_sessions` | `user_id` filter |
| `privacy_settings` | `user_id` FK |

### ⚠️ Needs Verification

| Component | Risk |
|-----------|------|
| Vector Store (FAISS) | No native user filtering - relies on metadata |
| Shared content | Public syllabus content accessible to all (intended) |

---

## 5. Async Flow Issues

### Issue: Background Task Session Management

```python
# Current (Broken)
@router.post("/{doc_id}/process")
async def trigger_processing(..., db: AsyncSession = Depends(get_db)):
    background_tasks.add_task(_process_document_background, doc_id, db)
    # db session closes when request ends, background task fails
```

### Issue: Missing Await in Sync Context

```python
# In pdf_extractor.py - _extract_pdf is sync but called with await
async def _extract_pdf(self, file_path: str) -> ExtractionResult:
    return self.extractor.extract_from_file(file_path)  # Sync call
```

---

## 6. Recommendations Summary

| Priority | Issue | Fix |
|----------|-------|-----|
| 🔴 Critical | Background task session | Create new session in task |
| 🔴 Critical | User isolation in vectors | Add user_id to all vector metadata |
| 🟠 High | Auto-embed after processing | Call embedding service in process_document |
| 🟠 High | Quiz → Proficiency link | Update TopicProficiency in complete_attempt |
| 🟡 Medium | Singleton RAG pipeline | Create app-level singleton |
| 🟡 Medium | MockLLMClient in prod | Use real LLM client |
| 🟢 Low | Sync/async mismatch | Wrap sync calls properly |

---

## Next Steps

1. Review `code_fixes.py` for specific code changes
2. Apply database migrations for schema fixes
3. Add indexes per `indexes.sql`
4. Integrate structured logging per `logging_config.py`
