"""
Dynamic Roadmap Models
User study plans, daily tasks, and preparation phases.
"""
import uuid
from datetime import datetime, timezone, date, timedelta
from sqlalchemy import (
    Column, String, Boolean, Integer, Text, ForeignKey, 
    DateTime, JSON, Float, Date, UniqueConstraint, Enum
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.base import TimestampMixin


class PreparationLevel(str, enum.Enum):
    """User's UPSC preparation level"""
    BEGINNER = "beginner"          # Just starting, no prior knowledge
    FOUNDATION = "foundation"       # Has basic understanding
    INTERMEDIATE = "intermediate"   # Covered 30-50% syllabus
    ADVANCED = "advanced"          # Covered 50-80% syllabus
    REVISION = "revision"          # Final revision mode


class StudyPreference(str, enum.Enum):
    """User's preferred study style"""
    INTENSIVE = "intensive"         # 8-10 hours/day
    MODERATE = "moderate"           # 5-7 hours/day
    RELAXED = "relaxed"            # 3-4 hours/day
    PART_TIME = "part_time"        # Working professional, 2-3 hours/day


class TaskStatus(str, enum.Enum):
    """Status of a study task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    RESCHEDULED = "rescheduled"


class TaskType(str, enum.Enum):
    """Type of study task"""
    STUDY = "study"
    QUIZ = "quiz"
    REVISION = "revision"
    PRACTICE = "practice"
    CURRENT_AFFAIRS = "current_affairs"
    ANSWER_WRITING = "answer_writing"
    MOCK_TEST = "mock_test"


class UserStudyPlan(Base, TimestampMixin):
    """
    Master study plan for a user.
    Contains overall preparation settings and target.
    """
    __tablename__ = "user_study_plans"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Target exam details
    target_exam_year = Column(Integer, nullable=False)  # e.g., 2026
    target_exam_type = Column(String(50), default="upsc_cse")  # upsc_cse, upsc_prelims_only
    optional_subject = Column(String(100), nullable=True)  # e.g., "Geography", "History"
    
    # User details for personalization
    preparation_level = Column(String(30), default=PreparationLevel.BEGINNER.value)
    study_preference = Column(String(30), default=StudyPreference.MODERATE.value)
    daily_study_hours = Column(Float, default=6.0)
    preferred_study_time = Column(String(20), default="morning")  # morning, afternoon, evening, night
    
    # Work/Background
    is_working = Column(Boolean, default=False)
    has_coaching = Column(Boolean, default=False)
    educational_background = Column(String(100), nullable=True)
    
    # Languages
    medium = Column(String(20), default="english")  # english, hindi
    
    # Plan dates
    plan_start_date = Column(Date, nullable=False)
    target_prelims_date = Column(Date, nullable=True)
    target_mains_date = Column(Date, nullable=True)
    
    # Current progress
    current_phase_id = Column(String(36), ForeignKey("study_phases.id", ondelete="SET NULL"), nullable=True)
    overall_progress = Column(Float, default=0.0)  # 0-100
    
    # Preferences
    include_current_affairs = Column(Boolean, default=True)
    include_answer_writing = Column(Boolean, default=True)
    weekly_mock_tests = Column(Integer, default=1)
    revision_frequency_days = Column(Integer, default=7)  # Revise every X days
    
    # Stats
    total_study_hours = Column(Float, default=0.0)
    topics_completed = Column(Integer, default=0)
    quizzes_taken = Column(Integer, default=0)
    
    # Flags
    is_active = Column(Boolean, default=True)
    onboarding_completed = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", backref="study_plan", uselist=False)
    current_phase = relationship("StudyPhase", foreign_keys=[current_phase_id])
    phases = relationship("StudyPhase", back_populates="study_plan", foreign_keys="StudyPhase.study_plan_id")
    daily_tasks = relationship("DailyStudyTask", back_populates="study_plan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UserStudyPlan {self.user_id}>"


class StudyPhase(Base, TimestampMixin):
    """
    A phase in the user's study plan.
    Example phases: Foundation, Prelims Focus, Mains Preparation, Revision
    """
    __tablename__ = "study_phases"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    study_plan_id = Column(String(36), ForeignKey("user_study_plans.id", ondelete="CASCADE"), nullable=False)
    
    # Phase details
    name = Column(String(100), nullable=False)  # e.g., "Foundation Building"
    description = Column(Text, nullable=True)
    order = Column(Integer, default=1)  # Phase sequence
    
    # Duration
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    
    # Focus areas (JSON list of subject codes)
    focus_subjects = Column(JSON, nullable=True)  # ["polity", "history", "geography"]
    
    # Goals for this phase
    target_topics = Column(Integer, default=0)
    target_study_hours = Column(Float, default=0)
    target_quizzes = Column(Integer, default=0)
    
    # Current progress
    topics_completed = Column(Integer, default=0)
    study_hours = Column(Float, default=0)
    quizzes_completed = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)
    
    # Status
    is_active = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    study_plan = relationship("UserStudyPlan", back_populates="phases", foreign_keys=[study_plan_id])
    
    def __repr__(self):
        return f"<StudyPhase {self.name}>"
    
    def update_progress(self):
        """Calculate phase progress"""
        if self.target_topics > 0:
            topic_progress = (self.topics_completed / self.target_topics) * 100
        else:
            topic_progress = 0
        
        if self.target_study_hours > 0:
            hours_progress = (self.study_hours / self.target_study_hours) * 100
        else:
            hours_progress = 0
        
        # Weighted average
        self.progress_percentage = min(100, (topic_progress * 0.6 + hours_progress * 0.4))


class DailyStudyTask(Base, TimestampMixin):
    """
    Individual study task for a specific day.
    Generated dynamically based on the study plan.
    """
    __tablename__ = "daily_study_tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    study_plan_id = Column(String(36), ForeignKey("user_study_plans.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Task details
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(30), default=TaskType.STUDY.value)
    
    # Scheduling
    scheduled_date = Column(Date, nullable=False, index=True)
    scheduled_time_slot = Column(String(30), nullable=True)  # morning, afternoon, evening
    due_date = Column(Date, nullable=True)
    
    # Duration
    estimated_minutes = Column(Integer, default=30)
    actual_minutes = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(30), default=TaskStatus.PENDING.value)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Priority (1-10, higher = more important)
    priority = Column(Integer, default=5)
    is_mandatory = Column(Boolean, default=False)
    
    # Related content
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    topic_name = Column(String(200), nullable=True)  # Cached for quick access
    subject_id = Column(String(36), nullable=True)
    subject_name = Column(String(100), nullable=True)  # Cached
    content_id = Column(String(36), ForeignKey("contents.id", ondelete="SET NULL"), nullable=True)
    quiz_id = Column(String(36), nullable=True)
    
    # For spaced repetition
    is_revision = Column(Boolean, default=False)
    revision_number = Column(Integer, nullable=True)  # 1st, 2nd, 3rd revision
    original_task_id = Column(String(36), nullable=True)  # Link to original study task
    
    # Resources (JSON list)
    resources = Column(JSON, nullable=True)  # [{"type": "book", "name": "Laxmikanth", "chapter": 3}]
    
    # Feedback
    difficulty_rating = Column(Integer, nullable=True)  # 1-5, user feedback
    notes = Column(Text, nullable=True)
    
    # Relationships
    study_plan = relationship("UserStudyPlan", back_populates="daily_tasks")
    user = relationship("User", backref="daily_tasks")
    topic = relationship("Topic", backref="assigned_tasks")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'scheduled_date', 'topic_id', 'task_type', 
                        name='unique_user_date_topic_type'),
    )
    
    def __repr__(self):
        return f"<DailyStudyTask {self.title}>"
    
    def mark_completed(self, actual_minutes: int = None):
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED.value
        self.completed_at = datetime.now(timezone.utc)
        if actual_minutes:
            self.actual_minutes = actual_minutes
        elif not self.actual_minutes:
            self.actual_minutes = self.estimated_minutes


class WeeklyPlan(Base, TimestampMixin):
    """
    Weekly plan summary for user.
    Generated at the start of each week.
    """
    __tablename__ = "weekly_plans"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    study_plan_id = Column(String(36), ForeignKey("user_study_plans.id", ondelete="CASCADE"), nullable=False)
    
    # Week details
    week_number = Column(Integer, nullable=False)  # Week of the year
    year = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Targets
    target_study_hours = Column(Float, default=0)
    target_topics = Column(Integer, default=0)
    target_quizzes = Column(Integer, default=0)
    
    # Actual progress
    actual_study_hours = Column(Float, default=0)
    topics_completed = Column(Integer, default=0)
    quizzes_completed = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    tasks_total = Column(Integer, default=0)
    
    # Focus for the week (JSON)
    focus_subjects = Column(JSON, nullable=True)  # ["polity", "history"]
    weekly_goals = Column(JSON, nullable=True)  # [{"goal": "Complete Constitution basics", "done": false}]
    
    # Analysis
    productivity_score = Column(Float, nullable=True)  # 0-100
    consistency_score = Column(Float, nullable=True)  # 0-100
    
    # Status
    is_current = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'year', 'week_number', name='unique_user_week'),
    )
    
    def __repr__(self):
        return f"<WeeklyPlan Week {self.week_number}/{self.year}>"
