"""
RAG API Endpoints
Query interface for the RAG pipeline using the singleton EmbeddingPipeline.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_user, get_embedding_pipeline
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== Schemas ====================

class RAGQueryRequest(BaseModel):
    """Request for RAG query"""
    question: str = Field(..., min_length=3, max_length=2000)
    document_ids: Optional[List[str]] = None
    syllabus_tags: Optional[List[str]] = None
    top_k: int = Field(5, ge=1, le=20)
    include_user_docs: bool = True
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    query_type: str = "standard"  # standard, analytical, conversational


class ConversationalQueryRequest(BaseModel):
    """Request for conversational RAG"""
    question: str = Field(..., min_length=3, max_length=2000)
    history: List[dict] = []
    syllabus_tags: Optional[List[str]] = None


class CitationResponse(BaseModel):
    """Citation in response"""
    chunk_id: str
    source: str
    snippet: str
    relevance_score: float
    page_number: Optional[int] = None


class RAGQueryResponse(BaseModel):
    """Response from RAG query"""
    answer: str
    citations: List[CitationResponse]
    query: str
    context_chunks: int
    model: str
    confidence: float


class IndexDocumentRequest(BaseModel):
    """Request to index a document for RAG"""
    document_id: str
    syllabus_tags: Optional[List[str]] = None


class IndexStatusResponse(BaseModel):
    """Status of indexing operation"""
    document_id: str
    chunks_indexed: int
    status: str
    message: str


# ==================== API Endpoints ====================

@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedding_pipeline=Depends(get_embedding_pipeline),
):
    """
    Query the RAG system with a question.

    The system will:
    1. Search for relevant chunks from indexed study materials
    2. Construct a grounded prompt with context
    3. Generate an answer using NVIDIA Kimi K2.5
    4. Return the answer with citations
    """
    try:
        from app.services.rag import create_rag_pipeline, LLMProvider
        from app.core.config import settings

        user_id = current_user.id if request.include_user_docs else None

        rag_pipeline = create_rag_pipeline(
            embedding_pipeline=embedding_pipeline,
            llm_provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            top_k=request.top_k,
        )

        # ── Try FAISS vector search first ──
        faiss_empty = embedding_pipeline.vector_store.size == 0

        if not faiss_empty:
            if request.query_type == "analytical":
                response = await rag_pipeline.analytical_query(
                    topic=request.question,
                    user_id=user_id,
                    syllabus_tags=request.syllabus_tags,
                )
            else:
                response = await rag_pipeline.query(
                    question=request.question,
                    user_id=user_id,
                    document_ids=request.document_ids,
                    syllabus_tags=request.syllabus_tags,
                    temperature=request.temperature,
                )

            # Got real results — return them
            if response.context_chunks > 0:
                return RAGQueryResponse(
                    answer=response.answer,
                    citations=[
                        CitationResponse(
                            chunk_id=c.chunk_id,
                            source=c.source,
                            snippet=c.content_snippet[:200] + "..." if len(c.content_snippet) > 200 else c.content_snippet,
                            relevance_score=c.relevance_score,
                            page_number=c.page_number,
                        )
                        for c in response.citations
                    ],
                    query=response.query,
                    context_chunks=response.context_chunks,
                    model=response.model,
                    confidence=response.confidence,
                )

        # ── DB chunk fallback ──
        # FAISS is empty or returned no results → pull chunks from DB directly.
        # This works immediately after upload, before/during vector indexing.
        if request.document_ids:
            from app.services.document_service import DocumentService
            import re

            doc_service = DocumentService(db)
            doc_id = request.document_ids[0]
            chunks, total = await doc_service.get_document_chunks(doc_id, page=1, limit=200)

            def _is_clean(text: str) -> bool:
                """Filter out garbled/binary chunks."""
                if len(text.strip()) < 30:
                    return False
                printable = sum(1 for c in text if c.isprintable() and not c.isspace())
                return printable / max(len(text), 1) > 0.80

            def _keyword_score(text: str, query: str) -> float:
                words = re.findall(r"\w+", query.lower())
                text_lower = text.lower()
                return sum(1 for w in words if w in text_lower) / max(len(words), 1)

            clean_chunks = [c for c in chunks if _is_clean(c.content)]
            logger.info(f"DB fallback: {len(clean_chunks)}/{len(chunks)} clean chunks for doc {doc_id}")

            if clean_chunks:
                # Score by keyword relevance and pick top 12
                scored = sorted(
                    clean_chunks,
                    key=lambda c: _keyword_score(c.content, request.question),
                    reverse=True
                )
                top_chunks = scored[:12]

                context = "\n---\n".join(
                    f"[Page {c.page_number or '?'}] {c.content}" for c in top_chunks
                )

                prompt = f"""You are Sakha, an expert UPSC Civil Services tutor with 15 years of experience coaching IAS toppers.
A student is studying from their uploaded document and asked you a question.
Your job is NOT to just quote the document — your job is to TEACH the concept deeply so the student can answer any UPSC question on this topic.

## Student Question:
{request.question}

## Relevant Document Excerpts (use as your source material):
{context}

## Your Response Must Follow This Structure:

### 🎯 Direct Answer
Give a clear, concise answer to the question in 2-3 sentences first.

### 📚 Deep Explanation
Explain the concept thoroughly. Use simple language. Connect facts to their historical/political/geographical significance.
Explain the "WHY" — why does this matter? What caused it? What were the effects?

### 🗺️ UPSC Exam Angle
- How is this topic relevant to UPSC Prelims / Mains?
- Which paper/GS paper does this fall under?
- What type of question is commonly asked (MCQ pattern, analytical question)?

### 🔗 Connect to Bigger Picture
Link this topic to related concepts, events, or themes from Indian/World history that a student should know together.

### 💡 What To Remember (Memory Hook)
Give 1-2 crisp mnemonics, memorable phrases, or a simple story/analogy to remember the key facts.

### ❓ Probable UPSC Questions
List 2-3 likely exam questions on this topic (Prelims MCQ style and/or Mains descriptive style).

---
IMPORTANT RULES:
- Only use facts from the provided excerpts. Do not hallucinate.
- If the excerpts don't have enough info, clearly say "The document doesn't cover this in detail, but generally..."
- Always cite page numbers in parentheses like (Page 8) when using specific facts.
- Write in a warm, encouraging teacher's voice — not robotic.
"""
                answer = await rag_pipeline.llm_client.generate(prompt=prompt, max_tokens=2048)

                citations = [
                    CitationResponse(
                        chunk_id=str(c.id),
                        source=f"Page {c.page_number or '?'}",
                        snippet=c.content[:200] + "..." if len(c.content) > 200 else c.content,
                        relevance_score=_keyword_score(c.content, request.question),
                        page_number=c.page_number,
                    )
                    for c in top_chunks[:5]
                ]

                return RAGQueryResponse(
                    answer=answer,
                    citations=citations,
                    query=request.question,
                    context_chunks=len(top_chunks),
                    model=getattr(rag_pipeline.llm_client, "model", "unknown"),
                    confidence=0.7,
                )
            else:
                # All chunks are garbled — indexing / OCR is still running
                return RAGQueryResponse(
                    answer=(
                        "⏳ **Your document is still being processed (OCR in progress for image-based PDF).**\n\n"
                        "This NCERT textbook is image-based and each page is being read via AI vision. "
                        "For a 260-page book this takes ~5–10 minutes.\n\n"
                        "Please try again in a few minutes, or ask about a specific topic in the meantime."
                    ),
                    citations=[],
                    query=request.question,
                    context_chunks=0,
                    model="system",
                    confidence=0.0,
                )

        # No document_ids and FAISS is empty
        return RAGQueryResponse(
            answer=(
                "No study materials found. Please upload a PDF first, then ask your question."
            ),
            citations=[],
            query=request.question,
            context_chunks=0,
            model="system",
            confidence=0.0,
        )

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"RAG query failed: {e}\n{tb}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query failed: {type(e).__name__}: {str(e)}"
        )


@router.post("/chat", response_model=RAGQueryResponse)
async def conversational_query(
    request: ConversationalQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedding_pipeline=Depends(get_embedding_pipeline),
):
    """Conversational RAG for multi-turn study sessions."""
    try:
        from app.services.rag import create_rag_pipeline
        from app.core.config import settings

        rag_pipeline = create_rag_pipeline(
            embedding_pipeline=embedding_pipeline,
            llm_provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
        )

        response = await rag_pipeline.conversational_query(
            question=request.question,
            history=request.history,
            user_id=current_user.id,
        )

        return RAGQueryResponse(
            answer=response.answer,
            citations=[
                CitationResponse(
                    chunk_id=c.chunk_id,
                    source=c.source,
                    snippet=c.content_snippet[:200],
                    relevance_score=c.relevance_score,
                    page_number=c.page_number,
                )
                for c in response.citations
            ],
            query=response.query,
            context_chunks=response.context_chunks,
            model=response.model,
            confidence=response.confidence,
        )

    except Exception as e:
        logger.error(f"Conversational query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversational query failed: {str(e)}"
        )


@router.post("/index", response_model=IndexStatusResponse)
async def index_document(
    request: IndexDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedding_pipeline=Depends(get_embedding_pipeline),
):
    """
    Manually index a document's chunks into the vector store.
    The document must have been processed (chunks extracted) before indexing.
    """
    try:
        from app.services.document_service import DocumentService

        doc_service = DocumentService(db)
        doc = await doc_service.get_document(request.document_id)

        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        if doc.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if doc.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has not been processed yet"
            )

        chunks, _ = await doc_service.get_document_chunks(request.document_id, limit=1000)

        if not chunks:
            return IndexStatusResponse(
                document_id=request.document_id,
                chunks_indexed=0,
                status="no_chunks",
                message="No chunks found to index"
            )

        chunk_dicts = [
            {
                "id": chunk.id,
                "content": chunk.content,
                "document_id": chunk.document_id,
                "chunk_type": chunk.chunk_type,
                "syllabus_tags": request.syllabus_tags or [],
                "source": doc.original_filename,
            }
            for chunk in chunks
        ]

        count = await embedding_pipeline.index_chunks(
            chunks=chunk_dicts,
            user_id=current_user.id,
        )

        return IndexStatusResponse(
            document_id=request.document_id,
            chunks_indexed=count,
            status="success",
            message=f"Successfully indexed {count} chunks"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {str(e)}"
        )


@router.get("/stats")
async def get_rag_stats(
    current_user: User = Depends(get_current_user),
    embedding_pipeline=Depends(get_embedding_pipeline),
):
    """Get statistics about the RAG system."""
    return {
        "total_vectors": embedding_pipeline.vector_store.size,
        "embedding_model": embedding_pipeline.embedding_model.model_name,
        "vector_dimension": embedding_pipeline.embedding_model.dimension,
        "index_type": embedding_pipeline.vector_store.index_type,
        "status": "ready" if embedding_pipeline.vector_store.size > 0 else "empty",
    }
