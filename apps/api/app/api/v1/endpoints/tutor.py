"""
AI Tutor API Endpoints
Intelligent tutoring with RAG, multilingual output, and adjustable verbosity.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== Request/Response Schemas ====================

class TutorQueryRequest(BaseModel):
    """Request for AI tutor query"""
    question: str = Field(..., min_length=3, max_length=2000)
    syllabus_tags: Optional[List[str]] = None
    language: str = Field("en", description="Output language: en, hi, hinglish")
    verbosity: str = Field("standard", description="Detail level: brief, standard, detailed, exam_ready")
    include_follow_ups: bool = True
    include_exam_tips: bool = True


class ExplainTopicRequest(BaseModel):
    """Request to explain a topic"""
    topic: str = Field(..., min_length=3, max_length=500)
    language: str = "en"
    verbosity: str = "detailed"


class PracticeQuestionRequest(BaseModel):
    """Request to generate practice question"""
    topic: str = Field(..., min_length=3, max_length=500)
    question_type: str = Field("analytical", description="factual, conceptual, analytical, comparative, application")


class TutorQueryResponse(BaseModel):
    """Response from AI tutor"""
    answer: str
    language: str
    verbosity: str
    question_type: str
    syllabus_topics: List[str]
    citations: List[dict]
    follow_up_questions: List[str]
    key_points: List[str]
    exam_tips: Optional[str] = None
    confidence: float


class PracticeQuestionResponse(BaseModel):
    """Practice question response"""
    topic: str
    question: str
    question_type: str
    model_answer: str
    key_points: List[str]


# ==================== Summarization Schemas ====================

class SummarizeRequest(BaseModel):
    """Request to summarize content"""
    content: str = Field(..., min_length=100, max_length=100000)
    format: str = Field("structured", description="bullet, paragraph, structured, notes, flashcard")
    length: str = Field("medium", description="short, medium, long, comprehensive")
    language: str = "en"
    extract_info: bool = True


class SummarizeDocumentRequest(BaseModel):
    """Request to summarize a document by ID"""
    document_id: str
    format: str = "structured"
    length: str = "medium"
    language: str = "en"


class RevisionSummaryRequest(BaseModel):
    """Request for revision-ready summary"""
    content: str = Field(..., min_length=100, max_length=100000)
    topic: str = Field(..., min_length=3, max_length=200)
    language: str = "en"


class SummaryResponse(BaseModel):
    """Summary response"""
    summary: str
    format: str
    language: str
    word_count: int
    key_topics: List[str]
    key_terms: List[dict]
    exam_relevance: str
    important_dates: List[str]
    important_names: List[str]
    source_chunks: int


class RevisionSummaryResponse(BaseModel):
    """Revision summary response with multiple formats"""
    topic: str
    quick_revision: str
    detailed_notes: str
    flashcards: str
    key_topics: List[str]
    key_terms: List[dict]
    important_dates: List[str]
    important_names: List[str]
    exam_relevance: str


# ==================== Tutor Endpoints ====================

@router.post("/ask", response_model=TutorQueryResponse)
async def ask_tutor(
    request: TutorQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask the AI tutor a question.
    
    Features:
    - RAG-based answering with syllabus awareness
    - Adjustable verbosity (brief, standard, detailed, exam_ready)
    - Multilingual output (English, Hindi, Hinglish)
    - Follow-up question suggestions
    - Exam tips based on question type
    """
    try:
        from app.services.ai import AITutor, VerbosityLevel, OutputLanguage
        from app.services.rag import EmbeddingPipeline, create_rag_pipeline, LLMProvider
        from app.services.rag.pipeline import MockLLMClient
        
        # Map string to enum
        verbosity_map = {
            "brief": VerbosityLevel.BRIEF,
            "standard": VerbosityLevel.STANDARD,
            "detailed": VerbosityLevel.DETAILED,
            "exam_ready": VerbosityLevel.EXAM_READY,
        }
        
        language_map = {
            "en": OutputLanguage.ENGLISH,
            "hi": OutputLanguage.HINDI,
            "hinglish": OutputLanguage.HINGLISH,
        }
        
        verbosity = verbosity_map.get(request.verbosity, VerbosityLevel.STANDARD)
        language = language_map.get(request.language, OutputLanguage.ENGLISH)
        
        # Initialize components
        try:
            embedding_pipeline = EmbeddingPipeline(
                model_name="all-MiniLM-L6-v2",
                storage_path="data/vectors",
            )
            embedding_pipeline.load()
            rag_pipeline = create_rag_pipeline(
                embedding_pipeline=embedding_pipeline,
                llm_provider=LLMProvider.OLLAMA,
            )
        except Exception:
            rag_pipeline = None
        
        # Create tutor
        tutor = AITutor(
            rag_pipeline=rag_pipeline,
            llm_client=MockLLMClient(),  # Replace with real LLM in production
        )
        
        # Get response
        response = await tutor.ask(
            question=request.question,
            syllabus_tags=request.syllabus_tags,
            user_id=current_user.id,
            language=language,
            verbosity=verbosity,
            include_follow_ups=request.include_follow_ups,
            include_exam_tips=request.include_exam_tips,
        )
        
        return TutorQueryResponse(
            answer=response.answer,
            language=response.language,
            verbosity=response.verbosity,
            question_type=response.question_type,
            syllabus_topics=response.syllabus_topics,
            citations=response.citations,
            follow_up_questions=response.follow_up_questions,
            key_points=response.key_points,
            exam_tips=response.exam_tips,
            confidence=response.confidence,
        )
        
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI dependencies not available: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Tutor query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tutor query failed: {str(e)}"
        )


@router.post("/explain", response_model=TutorQueryResponse)
async def explain_topic(
    request: ExplainTopicRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explain a syllabus topic in detail"""
    # Reuse ask endpoint with modified question
    ask_request = TutorQueryRequest(
        question=f"Explain {request.topic} in detail for UPSC preparation",
        language=request.language,
        verbosity=request.verbosity,
        include_follow_ups=True,
        include_exam_tips=True,
    )
    return await ask_tutor(ask_request, db, current_user)


@router.post("/practice-question", response_model=PracticeQuestionResponse)
async def generate_practice_question(
    request: PracticeQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a practice question on a topic with model answer"""
    try:
        from app.services.ai import AITutor, QuestionType
        from app.services.rag.pipeline import MockLLMClient
        
        question_type_map = {
            "factual": QuestionType.FACTUAL,
            "conceptual": QuestionType.CONCEPTUAL,
            "analytical": QuestionType.ANALYTICAL,
            "comparative": QuestionType.COMPARATIVE,
            "application": QuestionType.APPLICATION,
        }
        
        qtype = question_type_map.get(request.question_type, QuestionType.ANALYTICAL)
        
        tutor = AITutor(llm_client=MockLLMClient())
        result = await tutor.practice_question(
            topic=request.topic,
            question_type=qtype,
        )
        
        return PracticeQuestionResponse(**result)
        
    except Exception as e:
        logger.error(f"Practice question generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate practice question: {str(e)}"
        )


# ==================== Summarization Endpoints ====================

@router.post("/summarize", response_model=SummaryResponse)
async def summarize_content(
    request: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Summarize text content.
    
    Formats:
    - bullet: Bullet point list
    - paragraph: Flowing paragraphs
    - structured: Headings with bullets
    - notes: Study notes format
    - flashcard: Q&A flashcard format
    """
    try:
        from app.services.ai import (
            DocumentSummarizer, 
            SummaryFormat, 
            SummaryLength, 
            SummaryLanguage
        )
        from app.services.rag.pipeline import MockLLMClient
        
        format_map = {
            "bullet": SummaryFormat.BULLET,
            "paragraph": SummaryFormat.PARAGRAPH,
            "structured": SummaryFormat.STRUCTURED,
            "notes": SummaryFormat.NOTES,
            "flashcard": SummaryFormat.FLASHCARD,
        }
        
        length_map = {
            "short": SummaryLength.SHORT,
            "medium": SummaryLength.MEDIUM,
            "long": SummaryLength.LONG,
            "comprehensive": SummaryLength.COMPREHENSIVE,
        }
        
        language_map = {
            "en": SummaryLanguage.ENGLISH,
            "hi": SummaryLanguage.HINDI,
            "hinglish": SummaryLanguage.HINGLISH,
        }
        
        fmt = format_map.get(request.format, SummaryFormat.STRUCTURED)
        length = length_map.get(request.length, SummaryLength.MEDIUM)
        lang = language_map.get(request.language, SummaryLanguage.ENGLISH)
        
        summarizer = DocumentSummarizer(llm_client=MockLLMClient())
        
        result = await summarizer.summarize(
            content=request.content,
            format=fmt,
            length=length,
            language=lang,
            extract_info=request.extract_info,
        )
        
        return SummaryResponse(
            summary=result.summary,
            format=result.format,
            language=result.language,
            word_count=result.word_count,
            key_topics=result.key_topics,
            key_terms=result.key_terms,
            exam_relevance=result.exam_relevance,
            important_dates=result.important_dates,
            important_names=result.important_names,
            source_chunks=result.source_chunks,
        )
        
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summarization failed: {str(e)}"
        )


@router.post("/summarize-document", response_model=SummaryResponse)
async def summarize_document(
    request: SummarizeDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Summarize a processed document by its ID"""
    try:
        from app.services.document_service import DocumentService
        from app.services.ai import (
            DocumentSummarizer, 
            SummaryFormat, 
            SummaryLength, 
            SummaryLanguage
        )
        from app.services.rag.pipeline import MockLLMClient
        
        # Get document chunks
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
        chunks, _ = await doc_service.get_document_chunks(request.document_id, limit=100)
        content = "\n\n".join([c.content for c in chunks])
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No content found in document"
            )
        
        # Summarize
        format_map = {
            "bullet": SummaryFormat.BULLET,
            "paragraph": SummaryFormat.PARAGRAPH,
            "structured": SummaryFormat.STRUCTURED,
            "notes": SummaryFormat.NOTES,
            "flashcard": SummaryFormat.FLASHCARD,
        }
        length_map = {
            "short": SummaryLength.SHORT,
            "medium": SummaryLength.MEDIUM,
            "long": SummaryLength.LONG,
            "comprehensive": SummaryLength.COMPREHENSIVE,
        }
        language_map = {
            "en": SummaryLanguage.ENGLISH,
            "hi": SummaryLanguage.HINDI,
            "hinglish": SummaryLanguage.HINGLISH,
        }
        
        summarizer = DocumentSummarizer(llm_client=MockLLMClient())
        
        result = await summarizer.summarize(
            content=content,
            format=format_map.get(request.format, SummaryFormat.STRUCTURED),
            length=length_map.get(request.length, SummaryLength.MEDIUM),
            language=language_map.get(request.language, SummaryLanguage.ENGLISH),
        )
        
        return SummaryResponse(
            summary=result.summary,
            format=result.format,
            language=result.language,
            word_count=result.word_count,
            key_topics=result.key_topics,
            key_terms=result.key_terms,
            exam_relevance=result.exam_relevance,
            important_dates=result.important_dates,
            important_names=result.important_names,
            source_chunks=result.source_chunks,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document summarization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document summarization failed: {str(e)}"
        )


@router.post("/revision-summary", response_model=RevisionSummaryResponse)
async def create_revision_summary(
    request: RevisionSummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a complete revision package with multiple summary formats.
    
    Returns:
    - Quick revision bullet points
    - Detailed study notes
    - Flashcards for self-testing
    - Key information extraction
    """
    try:
        from app.services.ai import DocumentSummarizer, SummaryLanguage
        from app.services.rag.pipeline import MockLLMClient
        
        language_map = {
            "en": SummaryLanguage.ENGLISH,
            "hi": SummaryLanguage.HINDI,
            "hinglish": SummaryLanguage.HINGLISH,
        }
        
        lang = language_map.get(request.language, SummaryLanguage.ENGLISH)
        
        summarizer = DocumentSummarizer(llm_client=MockLLMClient())
        
        result = await summarizer.summarize_for_revision(
            content=request.content,
            topic=request.topic,
            language=lang,
        )
        
        return RevisionSummaryResponse(**result)
        
    except Exception as e:
        logger.error(f"Revision summary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Revision summary failed: {str(e)}"
        )
