"""
Roadmap API Endpoints
Dynamic study plan generation and task management.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime, timedelta
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.roadmap_service import RoadmapService

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== Schemas ====================

class OnboardingRequest(BaseModel):
    """Request to create a study plan"""
    target_exam_year: int = Field(..., ge=2025, le=2035)
    preparation_level: str = Field(default="beginner")  # beginner, foundation, intermediate, advanced
    study_preference: str = Field(default="moderate")  # intensive, moderate, relaxed, part_time
    daily_study_hours: float = Field(default=6.0, ge=1.0, le=14.0)
    optional_subject: Optional[str] = None
    is_working: bool = False
    preferred_study_time: str = Field(default="morning")  # morning, afternoon, evening, night
    medium: str = Field(default="english")  # english, hindi


class StudyPlanResponse(BaseModel):
    """Study plan response"""
    id: str
    target_exam_year: int
    preparation_level: str
    study_preference: str
    daily_study_hours: float
    overall_progress: float
    current_phase_name: Optional[str] = None
    onboarding_completed: bool
    days_to_prelims: Optional[int] = None


class TaskResponse(BaseModel):
    """Task response"""
    id: str
    title: str
    description: Optional[str] = None
    task_type: str
    status: str
    priority: int
    scheduled_date: Optional[str] = None
    due_date: Optional[str] = None
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    topic_name: Optional[str] = None
    topic_id: Optional[str] = None
    subject_name: Optional[str] = None
    is_revision: bool = False
    scheduled_time_slot: Optional[str] = None


class PhaseResponse(BaseModel):
    """Phase response"""
    name: str
    start_date: str
    end_date: str
    progress: float
    is_active: bool
    is_completed: bool


class RoadmapFullResponse(BaseModel):
    """Complete roadmap response"""
    has_plan: bool
    overall_progress: float = 0
    current_phase: int = 1
    total_phases: int = 3
    phase_name: str = "Getting Started"
    phase_progress: float = 0
    today_tasks: List[TaskResponse] = []
    upcoming_tasks: List[TaskResponse] = []
    revision_due: List[TaskResponse] = []
    completed_this_week: int = 0
    streak_days: int = 0
    target_exam_year: Optional[int] = None
    days_to_prelims: Optional[int] = None
    daily_goal_hours: float = 6.0
    phases: List[PhaseResponse] = []


class UpdateTaskRequest(BaseModel):
    """Request to update task status"""
    status: str  # pending, in_progress, completed, skipped
    actual_minutes: Optional[int] = None
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class DailyStatsResponse(BaseModel):
    """Daily statistics response"""
    date: str
    tasks_total: int
    tasks_completed: int
    completion_rate: float
    study_minutes: int
    study_hours: float


class SyllabusSubjectResponse(BaseModel):
    """Syllabus subject info"""
    code: str
    name: str
    weightage: int
    topics_count: int


class SyllabusOverviewResponse(BaseModel):
    """Syllabus overview"""
    total_subjects: int
    total_topics: int
    total_hours: int
    subjects: List[SyllabusSubjectResponse]


# ==================== Onboarding Endpoints ====================

@router.get("/onboarding/status")
async def get_onboarding_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if user has completed onboarding"""
    from app.models.roadmap import UserStudyPlan
    from sqlalchemy import select
    
    result = await db.execute(
        select(UserStudyPlan)
        .where(UserStudyPlan.user_id == current_user.id)
        .where(UserStudyPlan.is_active == True)
    )
    study_plan = result.scalar_one_or_none()
    
    if not study_plan:
        return {
            "onboarding_completed": False,
            "has_plan": False
        }
    
    return {
        "onboarding_completed": study_plan.onboarding_completed,
        "has_plan": True,
        "plan_id": study_plan.id,
        "target_exam_year": study_plan.target_exam_year,
        "preparation_level": study_plan.preparation_level
    }


@router.post("/onboarding/complete", response_model=StudyPlanResponse)
async def complete_onboarding(
    request: OnboardingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete onboarding and create personalized study plan"""
    from app.models.roadmap import UserStudyPlan
    from sqlalchemy import select
    
    # Check if plan already exists
    result = await db.execute(
        select(UserStudyPlan)
        .where(UserStudyPlan.user_id == current_user.id)
    )
    existing_plan = result.scalar_one_or_none()
    
    if existing_plan:
        # Update existing plan
        existing_plan.target_exam_year = request.target_exam_year
        existing_plan.preparation_level = request.preparation_level
        existing_plan.study_preference = request.study_preference
        existing_plan.daily_study_hours = request.daily_study_hours
        existing_plan.optional_subject = request.optional_subject
        existing_plan.is_working = request.is_working
        existing_plan.preferred_study_time = request.preferred_study_time
        existing_plan.medium = request.medium
        existing_plan.onboarding_completed = True
        
        await db.commit()
        await db.refresh(existing_plan)
        
        study_plan = existing_plan
    else:
        # Create new plan
        service = RoadmapService(db)
        study_plan = await service.create_study_plan(
            user_id=current_user.id,
            target_exam_year=request.target_exam_year,
            preparation_level=request.preparation_level,
            study_preference=request.study_preference,
            daily_study_hours=request.daily_study_hours,
            optional_subject=request.optional_subject,
            is_working=request.is_working,
            preferred_study_time=request.preferred_study_time,
            medium=request.medium
        )
    
    # Calculate days to prelims
    today = date.today()
    days_to_prelims = None
    if study_plan.target_prelims_date:
        days_to_prelims = (study_plan.target_prelims_date - today).days
    
    return StudyPlanResponse(
        id=study_plan.id,
        target_exam_year=study_plan.target_exam_year,
        preparation_level=study_plan.preparation_level,
        study_preference=study_plan.study_preference,
        daily_study_hours=study_plan.daily_study_hours,
        overall_progress=study_plan.overall_progress,
        current_phase_name=study_plan.current_phase.name if study_plan.current_phase else None,
        onboarding_completed=study_plan.onboarding_completed,
        days_to_prelims=days_to_prelims
    )


# ==================== Roadmap Endpoints ====================

@router.get("/full", response_model=RoadmapFullResponse)
async def get_full_roadmap(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get complete roadmap with today's tasks and progress"""
    service = RoadmapService(db)
    data = await service.get_roadmap_data(current_user.id)
    
    if not data.get("has_plan"):
        return RoadmapFullResponse(has_plan=False)
    
    return RoadmapFullResponse(
        has_plan=True,
        overall_progress=data.get("overall_progress", 0),
        current_phase=data.get("current_phase", 1),
        total_phases=data.get("total_phases", 3),
        phase_name=data.get("phase_name", "Getting Started"),
        phase_progress=data.get("phase_progress", 0),
        today_tasks=[TaskResponse(**t) for t in data.get("today_tasks", [])],
        upcoming_tasks=[TaskResponse(**t) for t in data.get("upcoming_tasks", [])],
        revision_due=[TaskResponse(**t) for t in data.get("revision_due", [])],
        completed_this_week=data.get("completed_this_week", 0),
        streak_days=data.get("streak_days", 0),
        target_exam_year=data.get("target_exam_year"),
        days_to_prelims=data.get("days_to_prelims"),
        daily_goal_hours=data.get("daily_goal_hours", 6.0),
        phases=[PhaseResponse(**p) for p in data.get("phases", [])]
    )


@router.get("/today", response_model=List[TaskResponse])
async def get_today_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get today's study tasks"""
    service = RoadmapService(db)
    tasks = await service.generate_daily_tasks(current_user.id)
    
    return [
        TaskResponse(
            id=t.id,
            title=t.title,
            description=t.description,
            task_type=t.task_type,
            status=t.status,
            priority=t.priority,
            scheduled_date=t.scheduled_date.isoformat() if t.scheduled_date else None,
            due_date=t.due_date.isoformat() if t.due_date else None,
            estimated_minutes=t.estimated_minutes,
            actual_minutes=t.actual_minutes,
            topic_name=t.topic_name,
            topic_id=t.topic_id,
            subject_name=t.subject_name,
            is_revision=t.is_revision,
            scheduled_time_slot=t.scheduled_time_slot
        )
        for t in tasks
    ]


@router.post("/tasks/generate")
async def generate_tasks(
    target_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate tasks for a specific date"""
    service = RoadmapService(db)
    
    dt = date.fromisoformat(target_date) if target_date else date.today()
    tasks = await service.generate_daily_tasks(current_user.id, dt)
    
    return {
        "date": dt.isoformat(),
        "tasks_generated": len(tasks),
        "message": f"Generated {len(tasks)} tasks for {dt.isoformat()}"
    }


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update task status"""
    service = RoadmapService(db)
    
    task = await service.update_task_status(
        task_id=task_id,
        user_id=current_user.id,
        status=request.status,
        actual_minutes=request.actual_minutes,
        difficulty_rating=request.difficulty_rating,
        notes=request.notes
    )
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        status=task.status,
        priority=task.priority,
        scheduled_date=task.scheduled_date.isoformat() if task.scheduled_date else None,
        due_date=task.due_date.isoformat() if task.due_date else None,
        estimated_minutes=task.estimated_minutes,
        actual_minutes=task.actual_minutes,
        topic_name=task.topic_name,
        topic_id=task.topic_id,
        subject_name=task.subject_name,
        is_revision=task.is_revision,
        scheduled_time_slot=task.scheduled_time_slot
    )


# ==================== Stats Endpoints ====================

@router.get("/stats/today", response_model=DailyStatsResponse)
async def get_today_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get today's study statistics"""
    service = RoadmapService(db)
    stats = await service.get_daily_stats(current_user.id)
    
    return DailyStatsResponse(**stats)


@router.get("/stats/week")
async def get_week_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get this week's statistics"""
    service = RoadmapService(db)
    
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    stats = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        if day <= today:
            day_stats = await service.get_daily_stats(current_user.id, day)
            stats.append(day_stats)
    
    # Summary
    total_minutes = sum(s["study_minutes"] for s in stats)
    total_completed = sum(s["tasks_completed"] for s in stats)
    total_tasks = sum(s["tasks_total"] for s in stats)
    
    return {
        "week_start": week_start.isoformat(),
        "daily_stats": stats,
        "summary": {
            "total_study_hours": round(total_minutes / 60, 1),
            "total_tasks_completed": total_completed,
            "total_tasks": total_tasks,
            "avg_completion_rate": total_completed / total_tasks * 100 if total_tasks else 0
        }
    }


# ==================== Syllabus Endpoints ====================

@router.get("/syllabus/overview", response_model=SyllabusOverviewResponse)
async def get_syllabus_overview(
    current_user: User = Depends(get_current_user),
):
    """Get UPSC syllabus overview"""
    from app.services.upsc_syllabus_data import UPSC_SYLLABUS, get_total_syllabus_hours
    
    subjects = []
    total_topics = 0
    
    for stage in UPSC_SYLLABUS["stages"]:
        for paper in stage["papers"]:
            for subject in paper["subjects"]:
                topics_count = len(subject.get("topics", []))
                total_topics += topics_count
                subjects.append(SyllabusSubjectResponse(
                    code=subject["code"],
                    name=subject["name"],
                    weightage=subject.get("weightage", 0),
                    topics_count=topics_count
                ))
    
    return SyllabusOverviewResponse(
        total_subjects=len(subjects),
        total_topics=total_topics,
        total_hours=get_total_syllabus_hours(),
        subjects=subjects
    )


@router.get("/syllabus/subject/{subject_code}")
async def get_subject_topics(
    subject_code: str,
    current_user: User = Depends(get_current_user),
):
    """Get topics for a specific subject"""
    from app.services.upsc_syllabus_data import UPSC_SYLLABUS, RECOMMENDED_BOOKS
    
    for stage in UPSC_SYLLABUS["stages"]:
        for paper in stage["papers"]:
            for subject in paper["subjects"]:
                if subject["code"] == subject_code:
                    return {
                        "code": subject["code"],
                        "name": subject["name"],
                        "weightage": subject.get("weightage", 0),
                        "topics": subject.get("topics", []),
                        "recommended_books": RECOMMENDED_BOOKS.get(subject_code, [])
                    }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Subject {subject_code} not found"
    )

