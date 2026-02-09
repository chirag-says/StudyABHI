"""
Quiz API Endpoints
Generate, take, and evaluate quizzes.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from sqlalchemy import select, func
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.quiz import Quiz, QuizQuestion, QuestionAnswer, QuizAttempt

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== Request/Response Schemas ====================

class GenerateQuizRequest(BaseModel):
    """Request to generate a quiz from content"""
    title: str = Field(..., min_length=3, max_length=300)
    content: str = Field(..., min_length=100, max_length=50000)
    question_count: int = Field(10, ge=1, le=50)
    difficulty: str = Field("medium", description="easy, medium, hard, expert")
    topic_name: Optional[str] = None
    topic_id: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    passing_score: int = Field(60, ge=0, le=100)


class GenerateFromDocumentRequest(BaseModel):
    """Request to generate quiz from a document"""
    document_id: str
    title: str = Field(..., min_length=3, max_length=300)
    question_count: int = Field(10, ge=1, le=50)
    difficulty: str = "medium"
    time_limit_minutes: Optional[int] = None


class QuestionSchema(BaseModel):
    """Question in a quiz"""
    id: str
    question_text: str
    options: List[str]
    question_number: int
    difficulty: str
    topic_name: Optional[str] = None


class QuestionWithAnswerSchema(QuestionSchema):
    """Question with answer (for review)"""
    correct_option: int
    explanation: Optional[str] = None
    source_chunk_id: Optional[str] = None


class QuizSchema(BaseModel):
    """Quiz response schema"""
    id: str
    title: str
    description: Optional[str] = None
    difficulty: str
    question_count: int
    time_limit_minutes: Optional[int] = None
    passing_score: int
    status: str
    is_ai_generated: bool
    total_attempts: int
    average_score: Optional[float] = None
    created_at: str


class QuizDetailSchema(QuizSchema):
    """Quiz with questions"""
    questions: List[QuestionSchema]


class StartAttemptResponse(BaseModel):
    """Response when starting a quiz attempt"""
    attempt_id: str
    quiz_id: str
    quiz_title: str
    total_questions: int
    time_limit_minutes: Optional[int] = None
    questions: List[QuestionSchema]


class SubmitAnswerRequest(BaseModel):
    """Submit an answer"""
    question_id: str
    selected_option: Optional[int] = None  # None = skipped
    time_spent_seconds: int = Field(default=0, ge=0)  # Made optional with default 0


class SubmitAnswerResponse(BaseModel):
    """Response after submitting answer"""
    question_id: str
    recorded: bool


class CompleteAttemptResponse(BaseModel):
    """Response after completing attempt"""
    attempt_id: str
    quiz_id: str
    quiz_title: str
    score_percentage: float
    passed: bool
    total_questions: int
    correct_answers: int
    wrong_answers: int
    skipped: int
    time_spent_seconds: int
    topic_performance: List[dict]
    question_results: List[dict]
    improvement_areas: List[str]


class AttemptHistoryItem(BaseModel):
    """Quiz attempt in history"""
    attempt_id: str
    quiz_id: str
    quiz_title: str
    attempt_number: int
    score_percentage: Optional[float] = None
    passed: Optional[bool] = None
    completed_at: Optional[str] = None
    time_spent_seconds: Optional[int] = None


class UserAnalyticsResponse(BaseModel):
    """User analytics response"""
    user_id: str
    total_quizzes_attempted: int
    total_questions_answered: int
    overall_accuracy: float
    average_time_per_question: float
    quizzes_passed: int
    quizzes_failed: int
    pass_rate: float
    topic_performance: List[dict]
    difficulty_performance: dict
    recent_trend: str
    streak_days: int

class QuickQuizQuestion(BaseModel):
    id: str
    question: str
    options: List[str]
    correct_answer: int
    explanation: Optional[str] = None

class QuickQuizResponse(BaseModel):
    questions: List[QuickQuizQuestion]


# ==================== Quick Quiz Endpoint ====================

@router.get("/quick", response_model=QuickQuizResponse)
async def get_quick_quiz(
    document_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    count: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a quick quiz for flashcard-style practice.
    Returns questions with answers for immediate feedback.
    """
    # Simply fetch random questions from the database for now
    # In a real app, this would be smarter (e.g., spaced repetition)
    
    query = select(QuizQuestion).join(Quiz).where(Quiz.status == "published")
    
    # Filter by document/topic if provided
    if document_id:
        query = query.where(Quiz.source_document_id == document_id)
    if topic_id:
        query = query.where(QuizQuestion.topic_id == topic_id)
    
    query = query.order_by(func.random()).limit(count)
    result = await db.execute(query)
    questions = result.scalars().all()
    
    quick_questions = []
    
    if not questions:
        # Fallback if no questions found in DB, return empty list (frontend handles this)
        return QuickQuizResponse(questions=[])
        
    for q in questions:
        # Parse options from JSON string if stored as string, or use directly if list
        options = q.options if isinstance(q.options, list) else [] 
        
        quick_questions.append(QuickQuizQuestion(
            id=str(q.id),
            question=q.question_text,
            options=options,
            correct_answer=q.correct_option,
            explanation=q.explanation
        ))
        
    return QuickQuizResponse(questions=quick_questions)


# ==================== Quiz Generation Endpoints ====================


# ==================== Quiz Attempt Endpoints ====================

@router.post("/attempts/{attempt_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    attempt_id: str,
    request: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit an answer to a question"""
    from app.services.quiz_service import QuizEvaluator
    
    evaluator = QuizEvaluator(db)
    
    try:
        answer = await evaluator.submit_answer(
            attempt_id=attempt_id,
            question_id=request.question_id,
            selected_option=request.selected_option,
            time_spent_seconds=request.time_spent_seconds,
        )
        return answer
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/attempts/{attempt_id}/complete", response_model=CompleteAttemptResponse)
async def complete_attempt(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete a quiz attempt and get results"""
    from app.services.quiz_service import QuizEvaluator
    
    evaluator = QuizEvaluator(db)
    
    try:
        result = await evaluator.complete_attempt(attempt_id)
        await db.commit()
        
        return CompleteAttemptResponse(**result.to_dict())
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/attempt/{attempt_id}/submit", response_model=CompleteAttemptResponse, include_in_schema=False)
async def complete_attempt_legacy(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Legacy endpoint alias"""
    return await complete_attempt(attempt_id, db, current_user)


@router.get("/attempts/{attempt_id}/result", response_model=CompleteAttemptResponse)
async def get_attempt_result(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get result of a completed attempt"""
    from app.services.quiz_service import QuizEvaluator
    
    evaluator = QuizEvaluator(db)
    
    try:
        result = await evaluator.get_attempt_result(attempt_id)
        return CompleteAttemptResponse(**result.to_dict())
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/generate", response_model=QuizDetailSchema)
async def generate_quiz(
    request: GenerateQuizRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a quiz from text content using AI.
    
    The AI will create MCQs based on the provided study material.
    """
    try:
        from app.services.ai.quiz_generator import create_quiz_generator, QuestionDifficulty
        from app.services.quiz_service import QuizService
        
        # ... (diff map) ...
        
        # Generate questions with real LLM
        generator = await create_quiz_generator()
        result = await generator.generate_quiz(
            content=request.content,
            question_count=request.question_count,
            difficulty=difficulty,
            topic_name=request.topic_name,
            topic_id=request.topic_id,
        )
        
        if not result.success or not result.questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to generate quiz: {result.errors}"
            )
        
        # Create quiz in database
        quiz_service = QuizService(db)
        quiz = await quiz_service.create_quiz(
            title=request.title,
            created_by=current_user.id,
            questions=[q.to_dict() for q in result.questions],
            difficulty=request.difficulty,
            time_limit_minutes=request.time_limit_minutes,
            passing_score=request.passing_score,
            is_ai_generated=True,
            source_content=request.content[:2000],
        )
        
        await db.commit()
        
        return QuizDetailSchema(
            id=quiz.id,
            title=quiz.title,
            description=quiz.description,
            difficulty=quiz.difficulty,
            question_count=quiz.question_count,
            time_limit_minutes=quiz.time_limit_minutes,
            passing_score=quiz.passing_score,
            status=quiz.status,
            is_ai_generated=quiz.is_ai_generated,
            total_attempts=quiz.total_attempts,
            average_score=quiz.average_score,
            created_at=quiz.created_at.isoformat() if quiz.created_at else "",
            questions=[
                QuestionSchema(
                    id=q.id,
                    question_text=q.question_text,
                    options=q.options,
                    question_number=q.question_number,
                    difficulty=q.difficulty,
                    topic_name=q.topic_name,
                )
                for q in sorted(quiz.questions, key=lambda x: x.question_number)
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quiz generation failed: {str(e)}"
        )


@router.post("/generate-from-document", response_model=QuizDetailSchema)
async def generate_quiz_from_document(
    request: GenerateFromDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a quiz from an uploaded document's content"""
    try:
        from app.services.document_service import DocumentService
        from app.services.ai.quiz_generator import create_quiz_generator, QuestionDifficulty
        from app.services.quiz_service import QuizService
        
        # Get document
        doc_service = DocumentService(db)
        doc = await doc_service.get_document(request.document_id)
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if doc.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get chunks
        chunks, _ = await doc_service.get_document_chunks(request.document_id, limit=50)
        
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no content chunks"
            )
        
        content = "\n\n".join([c.content for c in chunks])
        
        # Generate quiz
        diff_map = {
            "easy": QuestionDifficulty.EASY,
            "medium": QuestionDifficulty.MEDIUM,
            "hard": QuestionDifficulty.HARD,
            "expert": QuestionDifficulty.EXPERT,
        }
        difficulty = diff_map.get(request.difficulty, QuestionDifficulty.MEDIUM)
        
        generator = await create_quiz_generator()
        result = await generator.generate_quiz(
            content=content,
            question_count=request.question_count,
            difficulty=difficulty,
        )
        
        if not result.success or not result.questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to generate quiz: {result.errors}"
            )
        
        # Create quiz
        quiz_service = QuizService(db)
        quiz = await quiz_service.create_quiz(
            title=request.title,
            created_by=current_user.id,
            questions=[q.to_dict() for q in result.questions],
            difficulty=request.difficulty,
            time_limit_minutes=request.time_limit_minutes,
            is_ai_generated=True,
            source_content=content[:2000],
        )
        
        await db.commit()
        
        return QuizDetailSchema(
            id=quiz.id,
            title=quiz.title,
            description=quiz.description,
            difficulty=quiz.difficulty,
            question_count=quiz.question_count,
            time_limit_minutes=quiz.time_limit_minutes,
            passing_score=quiz.passing_score,
            status=quiz.status,
            is_ai_generated=quiz.is_ai_generated,
            total_attempts=quiz.total_attempts,
            average_score=quiz.average_score,
            created_at=quiz.created_at.isoformat() if quiz.created_at else "",
            questions=[
                QuestionSchema(
                    id=q.id,
                    question_text=q.question_text,
                    options=q.options,
                    question_number=q.question_number,
                    difficulty=q.difficulty,
                    topic_name=q.topic_name,
                )
                for q in sorted(quiz.questions, key=lambda x: x.question_number)
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz generation from document failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quiz generation failed: {str(e)}"
        )


# ==================== Quiz CRUD Endpoints ====================

@router.get("", response_model=List[QuizSchema])
async def list_quizzes(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available quizzes"""
    from app.services.quiz_service import QuizService
    
    quiz_service = QuizService(db)
    quizzes, _ = await quiz_service.get_user_quizzes(current_user.id, page, limit)
    
    return [
        QuizSchema(
            id=q.id,
            title=q.title,
            description=q.description,
            difficulty=q.difficulty,
            question_count=q.question_count,
            time_limit_minutes=q.time_limit_minutes,
            passing_score=q.passing_score,
            status=q.status,
            is_ai_generated=q.is_ai_generated,
            total_attempts=q.total_attempts,
            average_score=q.average_score,
            created_at=q.created_at.isoformat() if q.created_at else "",
        )
        for q in quizzes
    ]


@router.get("/{quiz_id}", response_model=QuizDetailSchema)
async def get_quiz(
    quiz_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get quiz details with questions"""
    from app.services.quiz_service import QuizService
    
    quiz_service = QuizService(db)
    quiz = await quiz_service.get_quiz(quiz_id)
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    return QuizDetailSchema(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        difficulty=quiz.difficulty,
        question_count=quiz.question_count,
        time_limit_minutes=quiz.time_limit_minutes,
        passing_score=quiz.passing_score,
        status=quiz.status,
        is_ai_generated=quiz.is_ai_generated,
        total_attempts=quiz.total_attempts,
        average_score=quiz.average_score,
        created_at=quiz.created_at.isoformat() if quiz.created_at else "",
        questions=[
            QuestionSchema(
                id=q.id,
                question_text=q.question_text,
                options=q.options,
                question_number=q.question_number,
                difficulty=q.difficulty,
                topic_name=q.topic_name,
            )
            for q in sorted(quiz.questions, key=lambda x: x.question_number)
        ]
    )


@router.post("/{quiz_id}/publish", response_model=QuizSchema)
async def publish_quiz(
    quiz_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish a quiz to make it available"""
    from app.services.quiz_service import QuizService
    
    quiz_service = QuizService(db)
    quiz = await quiz_service.get_quiz(quiz_id)
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    if quiz.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only publish your own quizzes"
        )
    
    quiz = await quiz_service.publish_quiz(quiz_id)
    await db.commit()
    
    return QuizSchema(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        difficulty=quiz.difficulty,
        question_count=quiz.question_count,
        time_limit_minutes=quiz.time_limit_minutes,
        passing_score=quiz.passing_score,
        status=quiz.status,
        is_ai_generated=quiz.is_ai_generated,
        total_attempts=quiz.total_attempts,
        average_score=quiz.average_score,
        created_at=quiz.created_at.isoformat() if quiz.created_at else "",
    )


# ==================== Quiz Attempt Endpoints ====================

@router.post("/{quiz_id}/start", response_model=StartAttemptResponse)
async def start_quiz_attempt(
    quiz_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new quiz attempt"""
    from app.services.quiz_service import QuizService, QuizEvaluator
    
    quiz_service = QuizService(db)
    quiz = await quiz_service.get_quiz(quiz_id)
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    evaluator = QuizEvaluator(db)
    attempt = await evaluator.start_attempt(quiz_id, current_user.id)
    await db.commit()
    
    return StartAttemptResponse(
        attempt_id=attempt.id,
        quiz_id=quiz.id,
        quiz_title=quiz.title,
        total_questions=quiz.question_count,
        time_limit_minutes=quiz.time_limit_minutes,
        questions=[
            QuestionSchema(
                id=q.id,
                question_text=q.question_text,
                options=q.options,
                question_number=q.question_number,
                difficulty=q.difficulty,
                topic_name=q.topic_name,
            )
            for q in sorted(quiz.questions, key=lambda x: x.question_number)
        ]
    )


@router.post("/attempts/{attempt_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    attempt_id: str,
    request: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit an answer for a question"""
    from app.services.quiz_service import QuizEvaluator
    
    evaluator = QuizEvaluator(db)
    
    try:
        await evaluator.submit_answer(
            attempt_id=attempt_id,
            question_id=request.question_id,
            selected_option=request.selected_option,
            time_spent_seconds=request.time_spent_seconds,
        )
        await db.commit()
        
        return SubmitAnswerResponse(
            question_id=request.question_id,
            recorded=True,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/attempts/{attempt_id}/complete", response_model=CompleteAttemptResponse)
async def complete_attempt(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete a quiz attempt and get results"""
    from app.services.quiz_service import QuizEvaluator
    
    evaluator = QuizEvaluator(db)
    
    try:
        result = await evaluator.complete_attempt(attempt_id)
        await db.commit()
        
        return CompleteAttemptResponse(**result.to_dict())
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/attempts/{attempt_id}/result", response_model=CompleteAttemptResponse)
async def get_attempt_result(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get result of a completed attempt"""
    from app.services.quiz_service import QuizEvaluator
    
    evaluator = QuizEvaluator(db)
    
    try:
        result = await evaluator.get_attempt_result(attempt_id)
        return CompleteAttemptResponse(**result.to_dict())
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ==================== Analytics Endpoints ====================

@router.get("/analytics/me", response_model=UserAnalyticsResponse)
async def get_my_analytics(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's quiz analytics"""
    from app.services.quiz_service import QuizEvaluator
    
    evaluator = QuizEvaluator(db)
    analytics = await evaluator.get_user_analytics(current_user.id, days)
    
    return UserAnalyticsResponse(**analytics.to_dict())


@router.get("/analytics/history", response_model=List[AttemptHistoryItem])
async def get_attempt_history(
    quiz_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's quiz attempt history"""
    from app.services.quiz_service import QuizEvaluator
    
    evaluator = QuizEvaluator(db)
    attempts, _ = await evaluator.get_attempt_history(
        current_user.id, quiz_id, page, limit
    )
    
    return [
        AttemptHistoryItem(
            attempt_id=a.id,
            quiz_id=a.quiz_id,
            quiz_title=a.quiz.title if a.quiz else "Unknown",
            attempt_number=a.attempt_number,
            score_percentage=a.score_percentage,
            passed=a.passed,
            completed_at=a.completed_at.isoformat() if a.completed_at else None,
            time_spent_seconds=a.time_spent_seconds,
        )
        for a in attempts
    ]
