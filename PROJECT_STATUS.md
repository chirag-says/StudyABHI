# UPSC AI Platform - Project Status & Handover

This document outlines the current state of the UPSC AI Platform, what has been successfully implemented, how the architecture works, and what the immediate next steps are for development.

## 🟢 Completed & Functional Features

### 1. Robust RAG Pipeline & Vector Storage
- **FAISS Integration:** The system uses local FAISS vector storage (`data/vectors`) for document embeddings.
- **Dimension Mismatch Fix:** We resolved a critical issue where the FAISS index expected a different embedding dimension than the NVIDIA API provided. The pipeline now dynamically reshapes the query embedding and enforces a strict dimension check.
- **Singleton Architecture:** The FastAPI app initializes a single `EmbeddingPipeline` at startup and registers it globally (`embedding_registry.py`). This ensures that documents indexed in the background are immediately queryable without restarting the server.

### 2. Advanced Document Processing (PDF OCR)
- **Image-Based PDF Support:** The standard PyMuPDF extractor was failing on scanned NCERT textbooks because they contained no selectable text.
- **Vision Model Fallback:** We implemented an automated fallback mechanism. If a page yields less than 50 printable characters, the system renders the page as an image and sends it to the `meta/llama-3.2-11b-vision-instruct` model to perform high-accuracy OCR.

### 3. Resilient RAG Query Endpoint
- **DB Chunk Fallback (The "Zero-Wait" RAG):** OCR on a 260-page PDF can take 5-10 minutes. To prevent the frontend from appearing broken during this time, the RAG query endpoint (`rag.py`) uses a two-tier approach:
  1. It tries FAISS vector search first.
  2. If FAISS is empty (still indexing), it pulls the raw extracted chunks directly from the SQLite database.
  3. It runs a keyword-relevance algorithm on the DB chunks, filters out garbled text, and passes the best matches to the LLM.
- **UPSC-Optimized Teaching Prompt:** The LLM does not just recite text. It is prompted to act as an expert UPSC tutor (Sakha), providing direct answers, deep explanations, UPSC exam angles, memory hooks, and probable exam questions.

### 4. Roadmap Task Routing
- **Frontend Integration:** The "Start Task" button on the roadmap UI successfully triggers a status update (changing the task to `in_progress`) and routes the user appropriately.
- **UI Bug Fixes:** Resolved React reference errors (`ReferenceError: onAction is not defined`) in the roadmap component.

---

## 🟡 What Needs To Be Done Next (Next Steps)

### 1. Async Task Queue (Celery/Redis)
- **Current State:** Document OCR and indexing run as FastAPI `BackgroundTasks`. This spins up a thread in the event loop, which works but is not scalable for many concurrent users uploading large 300-page textbooks.
- **Action Required:** Move the document processing pipeline (`_process_document_background`) to a dedicated worker queue like Celery or RQ backed by Redis.

### 2. Frontend UX for Processing State
- **Current State:** If a user asks a question while OCR is still running and the chunks haven't populated yet, the LLM returns a hardcoded "⏳ Your document is still being processed" message.
- **Action Required:** Add a visual "Processing... (Page X of Y)" indicator on the frontend immediately after a user uploads a PDF. Block or warn them before they try to query an unindexed document.

### 3. Connecting Study Material to Specific Roadmap Tasks
- **Current State:** The roadmap task status updates to "ongoing", but there isn't a hard link routing the user directly from a specific roadmap task to the exact study material chapter they need to read.
- **Action Required:** Map specific roadmap tasks to uploaded document IDs or tags, so clicking "Start Task" automatically opens the relevant PDF in the Study Assistant view.

### 4. Quiz Generation Verification
- **Current State:** The backend has endpoints for quiz generation, but it needs rigorous testing with the new OCR-extracted text chunks to ensure the generated questions are accurate and relevant to UPSC standards.

---

## 🚀 How to Run Locally

1. **Backend:**
   ```bash
   cd apps/api
   python -m venv venv
   source venv/Scripts/activate # (Windows)
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
2. **Frontend:**
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

*Signed: ~Sakha & Chirag*
