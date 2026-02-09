"""
RAG API Endpoints
Query interface for the RAG pipeline.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_user
from app.models.user import User

router = APIRouter()


# ==================== Schemas ====================

class RAGQueryRequest(BaseModel):
    """Request for RAG query"""
    question: str = Field(..., min_length=3, max_length=2000)
    document_ids: Optional[List[str]] = None  # Filter by specific documents
    syllabus_tags: Optional[List[str]] = None  # Topic IDs to filter
    top_k: int = Field(5, ge=1, le=20)
    include_user_docs: bool = True  # Include user's personal documents
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    query_type: str = "standard"  # standard, analytical, conversational


class ConversationalQueryRequest(BaseModel):
    """Request for conversational RAG"""
    question: str = Field(..., min_length=3, max_length=2000)
    history: List[dict] = []  # [{"role": "user/assistant", "content": "..."}]
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
):
    """
    Query the RAG system with a question.
    
    The system will:
    1. Search for relevant chunks from indexed study materials
    2. Construct a grounded prompt with context
    3. Generate an answer using the LLM
    4. Return the answer with citations
    
    Query types:
    - **standard**: Direct Q&A format
    - **analytical**: UPSC-style analysis with multiple dimensions
    """
    try:
        from app.services.rag import (
            EmbeddingPipeline,
            create_rag_pipeline,
            LLMProvider,
        )
        from app.core.config import settings
        
        # Initialize RAG pipeline
        # In production, these would be singleton/cached instances
        embedding_pipeline = EmbeddingPipeline(
            model_name="all-MiniLM-L6-v2",
            storage_path="data/vectors",
        )
        
        rag_pipeline = create_rag_pipeline(
            embedding_pipeline=embedding_pipeline,
            llm_provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            top_k=request.top_k,
        )
        
        # Determine user filter
        user_id = current_user.id if request.include_user_docs else None
        
        # Execute query
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
        
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG dependencies not installed: {str(e)}. Install with: pip install sentence-transformers faiss-cpu"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query failed: {str(e)}"
        )


@router.post("/chat", response_model=RAGQueryResponse)
async def conversational_query(
    request: ConversationalQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Conversational RAG for multi-turn study sessions.
    
    Maintains context from previous messages and retrieves
    relevant materials based on the conversation flow.
    """
    try:
        from app.services.rag import (
            EmbeddingPipeline,
            create_rag_pipeline,
            LLMProvider,
        )
        
        embedding_pipeline = EmbeddingPipeline(
            model_name="all-MiniLM-L6-v2",
            storage_path="data/vectors",
        )
        
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversational query failed: {str(e)}"
        )


@router.post("/index", response_model=IndexStatusResponse)
async def index_document(
    request: IndexDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Index a document's chunks into the vector store for RAG retrieval.
    
    The document must have been processed (chunks extracted) before indexing.
    """
    try:
        from app.services.document_service import DocumentService
        from app.services.rag import EmbeddingPipeline
        
        # Get document
        doc_service = DocumentService(db)
        doc = await doc_service.get_document(request.document_id)
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if doc.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        if doc.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has not been processed yet"
            )
        
        # Get chunks
        chunks, _ = await doc_service.get_document_chunks(request.document_id, limit=1000)
        
        if not chunks:
            return IndexStatusResponse(
                document_id=request.document_id,
                chunks_indexed=0,
                status="no_chunks",
                message="No chunks found to index"
            )
        
        # Initialize embedding pipeline
        embedding_pipeline = EmbeddingPipeline(
            model_name="all-MiniLM-L6-v2",
            storage_path="data/vectors",
        )
        
        # Try to load existing index
        try:
            embedding_pipeline.load()
        except Exception:
            pass  # No existing index
        
        # Prepare chunks for indexing
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
        
        # Index chunks
        count = await embedding_pipeline.index_chunks(
            chunks=chunk_dicts,
            user_id=current_user.id,
        )
        
        # Save index
        embedding_pipeline.save()
        
        return IndexStatusResponse(
            document_id=request.document_id,
            chunks_indexed=count,
            status="success",
            message=f"Successfully indexed {count} chunks"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {str(e)}"
        )


@router.get("/stats")
async def get_rag_stats(
    current_user: User = Depends(get_current_user),
):
    """Get statistics about the RAG system"""
    try:
        from app.services.rag import EmbeddingPipeline
        
        embedding_pipeline = EmbeddingPipeline(
            model_name="all-MiniLM-L6-v2",
            storage_path="data/vectors",
        )
        
        try:
            embedding_pipeline.load()
            vector_count = embedding_pipeline.vector_store.size
        except Exception:
            vector_count = 0
        
        return {
            "total_vectors": vector_count,
            "embedding_model": "all-MiniLM-L6-v2",
            "vector_dimension": 384,
            "index_type": "flat",
            "status": "ready" if vector_count > 0 else "empty",
        }
        
    except Exception as e:
        return {
            "total_vectors": 0,
            "status": "error",
            "error": str(e),
        }
