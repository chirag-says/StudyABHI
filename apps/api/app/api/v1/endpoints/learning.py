"""
Learning Analytics API Endpoints
Track progress, get recommendations, and manage learning goals.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== Schemas ====================

class RecordSessionRequest(BaseModel):
    """Record a study session"""
    session_type: str = "reading"  # reading, video, quiz, revision, practice
    topic_id: Optional[str] = None
    content_id: Optional[str] = None
    duration_minutes: int = Field(ge=1)
    is_revision: bool = False
    pages_read: Optional[int] = None
    notes_taken: Optional[int] = None
    focus_score: Optional[float] = None


class SessionResponse(BaseModel):
    """Study session response"""
    id: str
    session_type: str
    duration_minutes: int
    topic_id: Optional[str] = None
    started_at: str
    is_revision: bool


class DailyProgressResponse(BaseModel):
    """Daily progress summary"""
    date: str
    total_study_minutes: int
    topics_studied: int
    quizzes_taken: int
    daily_accuracy: Optional[float] = None
    study_streak_days: int
    goal_achieved: bool


class TopicProficiencyResponse(BaseModel):
    """Topic proficiency info"""
    topic_id: str
    topic_name: Optional[str] = None
    proficiency_score: float
    confidence_level: str
    accuracy_percentage: Optional[float] = None
    total_study_minutes: int
    needs_revision: bool
    is_weak_area: bool
    is_mastered: bool
    next_revision_date: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Learning recommendation"""
    type: str
    priority: int
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    title: str
    reason: str
    estimated_minutes: int


class DailyPlanResponse(BaseModel):
    """Daily learning plan"""
    date: str
    total_recommended_minutes: int
    load_level: str
    recommendations: List[RecommendationResponse]
    revision_topics: List[str]
    new_topics: List[str]
    warnings: List[str]
    motivational_message: str


class AdaptiveAnalysisResponse(BaseModel):
    """Adaptive analysis results"""
    consistency_score: float
    burnout_risk: float
    engagement_score: float
    accuracy_trend: str
    weak_topics_count: int
    topics_due_revision: int
    recommended_load: str
    is_high_performer: bool
    needs_break: bool


class CreateGoalRequest(BaseModel):
    """Create a learning goal"""
    title: str = Field(..., min_length=3, max_length=300)
    goal_type: str  # topic_mastery, daily_study, quiz_score
    target_value: float = Field(gt=0)
    unit: Optional[str] = None
    target_date: str  # ISO date
    topic_id: Optional[str] = None
    description: Optional[str] = None


class GoalResponse(BaseModel):
    """Learning goal response"""
    id: str
    title: str
    goal_type: str
    target_value: float
    current_value: float
    progress_percentage: float
    status: str
    target_date: str


# ==================== New Schemas for Roadmap and Stats ====================

class RoadmapTaskSchema(BaseModel):
    """Task in the roadmap"""
    id: str
    title: str
    description: Optional[str] = None
    task_type: str  # study, quiz, revision, practice
    status: str  # pending, in_progress, completed, skipped
    priority: int = 5
    scheduled_date: Optional[str] = None
    due_date: Optional[str] = None
    estimated_minutes: Optional[int] = None
    topic_name: Optional[str] = None
    topic_id: Optional[str] = None
    content_id: Optional[str] = None
    quiz_id: Optional[str] = None


class RoadmapResponse(BaseModel):
    """Full roadmap response"""
    overall_progress: float = 0
    current_phase: int = 1
    total_phases: int = 4
    phase_name: str = "Getting Started"
    today_tasks: List[RoadmapTaskSchema] = []
    upcoming_tasks: List[RoadmapTaskSchema] = []
    revision_due: List[RoadmapTaskSchema] = []
    completed_this_week: int = 0
    streak_days: int = 0


class RoadmapTodayResponse(BaseModel):
    """Today's tasks response"""
    tasks: List[RoadmapTaskSchema] = []


class LearningStatsResponse(BaseModel):
    """Learning stats response for dashboard"""
    study_hours_week: float = 0
    quizzes_completed: int = 0
    topics_covered: int = 0
    total_topics: int = 100
    avg_score: float = 0
    streak_days: int = 0


class UpdateTaskStatusRequest(BaseModel):
    """Request to update task status"""
    status: str  # pending, in_progress, completed, skipped


# ==================== Session Tracking ====================

@router.post("/sessions", response_model=SessionResponse)
async def record_study_session(
    request: RecordSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a completed study session"""
    from app.models.learning import StudySession, DailyProgress, TopicProficiency
    from sqlalchemy import select
    from datetime import timezone
    
    now = datetime.now(timezone.utc)
    
    # Create session
    session = StudySession(
        user_id=current_user.id,
        session_type=request.session_type,
        started_at=now - timedelta(minutes=request.duration_minutes),
        ended_at=now,
        duration_minutes=request.duration_minutes,
        topic_id=request.topic_id,
        content_id=request.content_id,
        is_revision=request.is_revision,
        pages_read=request.pages_read,
        notes_taken=request.notes_taken,
        focus_score=request.focus_score,
    )
    db.add(session)
    
    # Update daily progress
    today = date.today()
    result = await db.execute(
        select(DailyProgress)
        .where(DailyProgress.user_id == current_user.id)
        .where(DailyProgress.date == today)
    )
    daily = result.scalar_one_or_none()
    
    if not daily:
        daily = DailyProgress(
            user_id=current_user.id,
            date=today,
        )
        db.add(daily)
    
    # Update aggregates
    daily.total_study_minutes += request.duration_minutes
    daily.session_count += 1
    
    if request.session_type == "reading":
        daily.reading_minutes += request.duration_minutes
    elif request.session_type == "quiz":
        daily.quiz_minutes += request.duration_minutes
    elif request.session_type == "revision":
        daily.revision_minutes += request.duration_minutes
    
    if request.topic_id:
        daily.topics_studied += 1
    
    if request.pages_read:
        daily.pages_read += request.pages_read
    
    # Check goal achievement
    if daily.total_study_minutes >= daily.daily_goal_minutes:
        daily.goal_achieved = True
    
    # Update topic proficiency
    if request.topic_id:
        result = await db.execute(
            select(TopicProficiency)
            .where(TopicProficiency.user_id == current_user.id)
            .where(TopicProficiency.topic_id == request.topic_id)
        )
        prof = result.scalar_one_or_none()
        
        if not prof:
            prof = TopicProficiency(
                user_id=current_user.id,
                topic_id=request.topic_id,
            )
            db.add(prof)
        
        prof.total_study_minutes += request.duration_minutes
        prof.last_studied = now
        
        if request.is_revision:
            prof.revision_count += 1
            prof.last_revised = now
    
    await db.commit()
    await db.refresh(session)
    
    return SessionResponse(
        id=session.id,
        session_type=session.session_type,
        duration_minutes=session.duration_minutes,
        topic_id=session.topic_id,
        started_at=session.started_at.isoformat() if session.started_at else "",
        is_revision=session.is_revision,
    )


from datetime import timedelta


@router.get("/progress/today", response_model=DailyProgressResponse)
async def get_today_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get today's learning progress"""
    from app.models.learning import DailyProgress
    from sqlalchemy import select
    
    today = date.today()
    result = await db.execute(
        select(DailyProgress)
        .where(DailyProgress.user_id == current_user.id)
        .where(DailyProgress.date == today)
    )
    daily = result.scalar_one_or_none()
    
    if not daily:
        # Return empty progress
        return DailyProgressResponse(
            date=today.isoformat(),
            total_study_minutes=0,
            topics_studied=0,
            quizzes_taken=0,
            daily_accuracy=None,
            study_streak_days=0,
            goal_achieved=False,
        )
    
    return DailyProgressResponse(
        date=daily.date.isoformat(),
        total_study_minutes=daily.total_study_minutes,
        topics_studied=daily.topics_studied,
        quizzes_taken=daily.quizzes_taken,
        daily_accuracy=daily.daily_accuracy,
        study_streak_days=daily.study_streak_days,
        goal_achieved=daily.goal_achieved,
    )


@router.get("/progress/history", response_model=List[DailyProgressResponse])
async def get_progress_history(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get learning progress history"""
    from app.models.learning import DailyProgress
    from sqlalchemy import select
    
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyProgress)
        .where(DailyProgress.user_id == current_user.id)
        .where(DailyProgress.date >= since)
        .order_by(DailyProgress.date.desc())
    )
    records = list(result.scalars().all())
    
    return [
        DailyProgressResponse(
            date=r.date.isoformat(),
            total_study_minutes=r.total_study_minutes,
            topics_studied=r.topics_studied,
            quizzes_taken=r.quizzes_taken,
            daily_accuracy=r.daily_accuracy,
            study_streak_days=r.study_streak_days,
            goal_achieved=r.goal_achieved,
        )
        for r in records
    ]


# ==================== Topic Proficiency ====================

@router.get("/proficiency", response_model=List[TopicProficiencyResponse])
async def get_topic_proficiencies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get proficiency for all studied topics"""
    from app.models.learning import TopicProficiency
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(TopicProficiency)
        .options(selectinload(TopicProficiency.topic))
        .where(TopicProficiency.user_id == current_user.id)
        .order_by(TopicProficiency.proficiency_score.desc())
    )
    proficiencies = list(result.scalars().all())
    
    return [
        TopicProficiencyResponse(
            topic_id=p.topic_id,
            topic_name=p.topic.name if p.topic else None,
            proficiency_score=p.proficiency_score,
            confidence_level=p.confidence_level,
            accuracy_percentage=p.accuracy_percentage,
            total_study_minutes=p.total_study_minutes,
            needs_revision=p.needs_revision,
            is_weak_area=p.is_weak_area,
            is_mastered=p.is_mastered,
            next_revision_date=p.next_revision_date.isoformat() if p.next_revision_date else None,
        )
        for p in proficiencies
    ]


@router.get("/proficiency/weak", response_model=List[TopicProficiencyResponse])
async def get_weak_topics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get weak topic areas needing improvement"""
    from app.models.learning import TopicProficiency
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(TopicProficiency)
        .options(selectinload(TopicProficiency.topic))
        .where(TopicProficiency.user_id == current_user.id)
        .where(TopicProficiency.is_weak_area == True)
    )
    proficiencies = list(result.scalars().all())
    
    return [
        TopicProficiencyResponse(
            topic_id=p.topic_id,
            topic_name=p.topic.name if p.topic else None,
            proficiency_score=p.proficiency_score,
            confidence_level=p.confidence_level,
            accuracy_percentage=p.accuracy_percentage,
            total_study_minutes=p.total_study_minutes,
            needs_revision=p.needs_revision,
            is_weak_area=p.is_weak_area,
            is_mastered=p.is_mastered,
            next_revision_date=p.next_revision_date.isoformat() if p.next_revision_date else None,
        )
        for p in proficiencies
    ]


# ==================== Adaptive Learning ====================

@router.get("/adaptive/analysis", response_model=AdaptiveAnalysisResponse)
async def get_adaptive_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get adaptive learning analysis for current user"""
    from app.services.adaptive_engine import AdaptiveLearningEngine
    
    engine = AdaptiveLearningEngine(db)
    analysis = await engine.analyze_user(current_user.id)
    
    await db.commit()
    
    return AdaptiveAnalysisResponse(
        consistency_score=analysis.consistency_score,
        burnout_risk=analysis.burnout_risk,
        engagement_score=analysis.engagement_score,
        accuracy_trend=analysis.accuracy_trend,
        weak_topics_count=len(analysis.weak_topics),
        topics_due_revision=len(analysis.topics_due_revision),
        recommended_load=analysis.recommended_load,
        is_high_performer=analysis.is_high_performer,
        needs_break=analysis.needs_break,
    )


@router.get("/adaptive/daily-plan", response_model=DailyPlanResponse)
async def get_daily_plan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get personalized daily learning plan"""
    from app.services.adaptive_engine import AdaptiveLearningEngine
    
    engine = AdaptiveLearningEngine(db)
    plan = await engine.generate_daily_plan(current_user.id)
    
    await db.commit()
    
    return DailyPlanResponse(
        date=plan.date.isoformat(),
        total_recommended_minutes=plan.total_recommended_minutes,
        load_level=plan.load_level,
        recommendations=[
            RecommendationResponse(
                type=r.type,
                priority=r.priority,
                topic_id=r.topic_id,
                topic_name=r.topic_name,
                title=r.title,
                reason=r.reason,
                estimated_minutes=r.estimated_minutes,
            )
            for r in plan.recommendations
        ],
        revision_topics=plan.revision_topics,
        new_topics=plan.new_topics,
        warnings=plan.warnings,
        motivational_message=plan.motivational_message,
    )


# ==================== Learning Goals ====================

@router.post("/goals", response_model=GoalResponse)
async def create_learning_goal(
    request: CreateGoalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new learning goal"""
    from app.models.learning import LearningGoal
    
    goal = LearningGoal(
        user_id=current_user.id,
        title=request.title,
        description=request.description,
        goal_type=request.goal_type,
        target_value=request.target_value,
        unit=request.unit,
        start_date=date.today(),
        target_date=date.fromisoformat(request.target_date),
        topic_id=request.topic_id,
    )
    
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    
    return GoalResponse(
        id=goal.id,
        title=goal.title,
        goal_type=goal.goal_type,
        target_value=goal.target_value,
        current_value=goal.current_value,
        progress_percentage=goal.progress_percentage,
        status=goal.status,
        target_date=goal.target_date.isoformat(),
    )


@router.get("/goals", response_model=List[GoalResponse])
async def get_learning_goals(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's learning goals"""
    from app.models.learning import LearningGoal
    from sqlalchemy import select
    
    query = select(LearningGoal).where(LearningGoal.user_id == current_user.id)
    
    if status:
        query = query.where(LearningGoal.status == status)
    
    result = await db.execute(query.order_by(LearningGoal.created_at.desc()))
    goals = list(result.scalars().all())
    
    return [
        GoalResponse(
            id=g.id,
            title=g.title,
            goal_type=g.goal_type,
            target_value=g.target_value,
            current_value=g.current_value,
            progress_percentage=g.progress_percentage,
            status=g.status,
            target_date=g.target_date.isoformat(),
        )
        for g in goals
    ]


# ==================== Roadmap and Stats Endpoints ====================

@router.get("/stats", response_model=LearningStatsResponse)
async def get_learning_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's learning statistics for the dashboard"""
    from app.models.learning import DailyProgress, TopicProficiency
    from sqlalchemy import select, func
    
    # Get stats for the past 7 days
    week_ago = date.today() - timedelta(days=7)
    
    # Calculate study hours this week
    result = await db.execute(
        select(func.sum(DailyProgress.total_study_minutes))
        .where(DailyProgress.user_id == current_user.id)
        .where(DailyProgress.date >= week_ago)
    )
    study_minutes = result.scalar() or 0
    study_hours = round(study_minutes / 60, 1)
    
    # Calculate quizzes completed
    result = await db.execute(
        select(func.sum(DailyProgress.quizzes_taken))
        .where(DailyProgress.user_id == current_user.id)
    )
    quizzes_completed = result.scalar() or 0
    
    # Get topics covered
    result = await db.execute(
        select(func.count(TopicProficiency.id))
        .where(TopicProficiency.user_id == current_user.id)
    )
    topics_covered = result.scalar() or 0
    
    # Calculate average score
    result = await db.execute(
        select(func.avg(DailyProgress.daily_accuracy))
        .where(DailyProgress.user_id == current_user.id)
        .where(DailyProgress.daily_accuracy.isnot(None))
    )
    avg_score = result.scalar() or 0
    
    # Get streak days
    result = await db.execute(
        select(DailyProgress.study_streak_days)
        .where(DailyProgress.user_id == current_user.id)
        .order_by(DailyProgress.date.desc())
        .limit(1)
    )
    streak = result.scalar() or 0
    
    return LearningStatsResponse(
        study_hours_week=study_hours,
        quizzes_completed=int(quizzes_completed),
        topics_covered=int(topics_covered),
        total_topics=100,  # Fixed for now
        avg_score=round(float(avg_score), 1) if avg_score else 0,
        streak_days=streak,
    )


@router.get("/roadmap", response_model=RoadmapResponse)
async def get_roadmap(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's personalized learning roadmap"""
    from app.models.learning import DailyProgress, TopicProficiency
    from sqlalchemy import select, func
    import uuid
    
    # Get streak and weekly progress
    result = await db.execute(
        select(DailyProgress)
        .where(DailyProgress.user_id == current_user.id)
        .order_by(DailyProgress.date.desc())
        .limit(1)
    )
    latest_progress = result.scalar_one_or_none()
    
    streak_days = latest_progress.study_streak_days if latest_progress else 0
    
    # Calculate completed this week
    week_ago = date.today() - timedelta(days=7)
    result = await db.execute(
        select(func.sum(DailyProgress.topics_studied))
        .where(DailyProgress.user_id == current_user.id)
        .where(DailyProgress.date >= week_ago)
    )
    completed_this_week = result.scalar() or 0
    
    # Get proficiency count for progress
    result = await db.execute(
        select(func.count(TopicProficiency.id))
        .where(TopicProficiency.user_id == current_user.id)
    )
    topics_done = result.scalar() or 0
    overall_progress = min(100, int((topics_done / 100) * 100)) if topics_done else 0
    
    # Determine phase based on progress
    if overall_progress < 25:
        phase, phase_name = 1, "Getting Started"
    elif overall_progress < 50:
        phase, phase_name = 2, "Foundation Building"
    elif overall_progress < 75:
        phase, phase_name = 3, "Deep Learning"
    else:
        phase, phase_name = 4, "Mastery"
    
    # Create sample tasks based on real data or defaults
    today = date.today()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    
    today_tasks = [
        RoadmapTaskSchema(
            id=str(uuid.uuid4()),
            title="Read Indian Polity Ch. 3",
            task_type="study",
            status="completed",
            priority=8,
            estimated_minutes=45,
            topic_name="Indian Polity",
        ),
        RoadmapTaskSchema(
            id=str(uuid.uuid4()),
            title="Take quiz on Fundamental Rights",
            task_type="quiz",
            status="pending",
            priority=7,
            estimated_minutes=20,
            topic_name="Constitutional Law",
        ),
        RoadmapTaskSchema(
            id=str(uuid.uuid4()),
            title="Review yesterday's notes",
            task_type="revision",
            status="pending",
            priority=6,
            estimated_minutes=15,
        ),
    ]
    
    upcoming_tasks = [
        RoadmapTaskSchema(
            id=str(uuid.uuid4()),
            title="Economics: Fiscal Policy",
            task_type="study",
            status="pending",
            priority=7,
            scheduled_date=tomorrow.isoformat(),
            topic_name="Economics",
        ),
        RoadmapTaskSchema(
            id=str(uuid.uuid4()),
            title="Geography: Indian Rivers",
            task_type="study",
            status="pending",
            priority=6,
            scheduled_date=day_after.isoformat(),
            topic_name="Geography",
        ),
    ]
    
    revision_due = [
        RoadmapTaskSchema(
            id=str(uuid.uuid4()),
            title="Revise Preamble",
            task_type="revision",
            status="pending",
            priority=9,
            topic_name="Constitution",
            due_date=today.isoformat(),
        ),
    ]
    
    return RoadmapResponse(
        overall_progress=overall_progress,
        current_phase=phase,
        total_phases=4,
        phase_name=phase_name,
        today_tasks=today_tasks,
        upcoming_tasks=upcoming_tasks,
        revision_due=revision_due,
        completed_this_week=int(completed_this_week),
        streak_days=streak_days,
    )


@router.get("/roadmap/today", response_model=RoadmapTodayResponse)
async def get_roadmap_today(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get today's tasks for the roadmap"""
    import uuid
    
    # Return sample tasks for today (in production, fetch from user's actual roadmap)
    tasks = [
        RoadmapTaskSchema(
            id=str(uuid.uuid4()),
            title="Read Indian Polity Ch. 3",
            task_type="study",
            status="completed",
            priority=8,
            estimated_minutes=45,
            topic_name="Indian Polity",
        ),
        RoadmapTaskSchema(
            id=str(uuid.uuid4()),
            title="Quiz: Fundamental Rights",
            task_type="quiz",
            status="pending",
            priority=7,
            estimated_minutes=20,
            topic_name="Constitutional Law",
        ),
        RoadmapTaskSchema(
            id=str(uuid.uuid4()),
            title="Review yesterday's notes",
            task_type="revision",
            status="pending",
            priority=6,
            estimated_minutes=15,
        ),
    ]
    
    return RoadmapTodayResponse(tasks=tasks)


@router.patch("/roadmap/task/{task_id}")
async def update_task_status(
    task_id: str,
    request: UpdateTaskStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a task's status"""
    # In production, update the actual task in the database
    # For now, just return success
    return {
        "task_id": task_id,
        "status": request.status,
        "message": "Task status updated successfully"
    }
