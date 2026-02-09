"""
Learning Behavior Models
Track study patterns, consistency, and learning progress.
"""
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import (
    Column, String, Boolean, Integer, Text, ForeignKey, 
    DateTime, JSON, Float, Date, UniqueConstraint
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.base import TimestampMixin


class LearningGoalStatus(str, enum.Enum):
    """Status of a learning goal"""
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class SessionType(str, enum.Enum):
    """Type of study session"""
    READING = "reading"
    VIDEO = "video"
    QUIZ = "quiz"
    REVISION = "revision"
    PRACTICE = "practice"
    NOTE_TAKING = "note_taking"


class MilestoneType(str, enum.Enum):
    """Types of learning milestones"""
    TOPIC_COMPLETE = "topic_complete"
    SUBJECT_COMPLETE = "subject_complete"
    QUIZ_STREAK = "quiz_streak"
    STUDY_STREAK = "study_streak"
    ACCURACY_MILESTONE = "accuracy_milestone"
    TIME_MILESTONE = "time_milestone"


# ==================== Study Session Tracking ====================

class StudySession(Base, TimestampMixin):
    """
    Individual study session record.
    Tracks what, when, and how long a user studied.
    """
    __tablename__ = "study_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Session details
    session_type = Column(String(30), default=SessionType.READING.value)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=0)
    
    # What was studied
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    content_id = Column(String(36), ForeignKey("contents.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    
    # Session metadata
    is_revision = Column(Boolean, default=False)
    pages_read = Column(Integer, nullable=True)
    notes_taken = Column(Integer, nullable=True)  # Count of notes
    
    # Engagement metrics
    focus_score = Column(Float, nullable=True)  # 0-100, based on activity
    completion_percentage = Column(Float, nullable=True)
    
    # Device/context
    device_type = Column(String(50), nullable=True)  # mobile, desktop, tablet
    
    # Relationships
    user = relationship("User", backref="study_sessions")
    topic = relationship("Topic", backref="study_sessions")
    
    def __repr__(self):
        return f"<StudySession {self.id} - {self.duration_minutes}min>"


# ==================== Daily Progress Tracking ====================

class DailyProgress(Base, TimestampMixin):
    """
    Aggregated daily learning metrics.
    One record per user per day for quick analytics.
    """
    __tablename__ = "daily_progress"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    
    # Study time
    total_study_minutes = Column(Integer, default=0)
    reading_minutes = Column(Integer, default=0)
    quiz_minutes = Column(Integer, default=0)
    revision_minutes = Column(Integer, default=0)
    
    # Content progress
    topics_studied = Column(Integer, default=0)
    topics_completed = Column(Integer, default=0)
    content_items_read = Column(Integer, default=0)
    pages_read = Column(Integer, default=0)
    
    # Quiz performance (for the day)
    quizzes_taken = Column(Integer, default=0)
    questions_answered = Column(Integer, default=0)
    questions_correct = Column(Integer, default=0)
    daily_accuracy = Column(Float, nullable=True)
    
    # Streaks (calculated)
    study_streak_days = Column(Integer, default=0)
    quiz_streak_days = Column(Integer, default=0)
    
    # Goal tracking
    daily_goal_minutes = Column(Integer, default=60)  # Target
    goal_achieved = Column(Boolean, default=False)
    
    # Session counts
    session_count = Column(Integer, default=0)
    avg_session_duration = Column(Float, nullable=True)
    
    # Relationships
    user = relationship("User", backref="daily_progress")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='unique_user_date'),
    )
    
    def __repr__(self):
        return f"<DailyProgress {self.date} - {self.total_study_minutes}min>"


# ==================== Topic Proficiency ====================

class TopicProficiency(Base, TimestampMixin):
    """
    User's proficiency level for each topic.
    Updated based on quiz performance and revision.
    """
    __tablename__ = "topic_proficiency"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    
    # Proficiency metrics
    proficiency_score = Column(Float, default=0.0)  # 0-100
    confidence_level = Column(String(20), default="beginner")  # beginner, familiar, proficient, expert
    
    # Quiz performance
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    accuracy_percentage = Column(Float, nullable=True)
    
    # Time investment
    total_study_minutes = Column(Integer, default=0)
    revision_count = Column(Integer, default=0)
    last_studied = Column(DateTime, nullable=True)
    last_revised = Column(DateTime, nullable=True)
    
    # Spaced repetition
    next_revision_date = Column(Date, nullable=True)
    revision_interval_days = Column(Integer, default=1)  # Days until next revision
    ease_factor = Column(Float, default=2.5)  # SM-2 algorithm ease factor
    
    # Flags
    needs_revision = Column(Boolean, default=False)
    is_weak_area = Column(Boolean, default=False)
    is_mastered = Column(Boolean, default=False)
    
    # Performance trend
    recent_accuracy = Column(Float, nullable=True)  # Last 5 attempts
    accuracy_trend = Column(String(20), nullable=True)  # improving, stable, declining
    
    # Relationships
    user = relationship("User", backref="topic_proficiencies")
    topic = relationship("Topic", backref="proficiencies")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'topic_id', name='unique_user_topic'),
    )
    
    def update_proficiency(self, correct: bool, questions: int = 1):
        """Update proficiency based on quiz answer"""
        self.total_questions += questions
        if correct:
            self.correct_answers += 1
        
        self.accuracy_percentage = (self.correct_answers / self.total_questions) * 100
        
        # Update confidence level
        if self.accuracy_percentage >= 90 and self.total_questions >= 20:
            self.confidence_level = "expert"
            self.is_mastered = True
        elif self.accuracy_percentage >= 75 and self.total_questions >= 10:
            self.confidence_level = "proficient"
        elif self.accuracy_percentage >= 50 and self.total_questions >= 5:
            self.confidence_level = "familiar"
        else:
            self.confidence_level = "beginner"
        
        # Mark weak areas
        self.is_weak_area = self.accuracy_percentage < 50 and self.total_questions >= 5
        
        # Update proficiency score (weighted)
        base_score = self.accuracy_percentage
        revision_bonus = min(self.revision_count * 2, 10)
        time_bonus = min(self.total_study_minutes / 60 * 5, 10)
        self.proficiency_score = min(base_score + revision_bonus + time_bonus, 100)
    
    def update_revision_schedule(self, quality: int):
        """
        Update spaced repetition schedule using SM-2 algorithm.
        quality: 0-5 (0=complete blackout, 5=perfect response)
        """
        if quality < 3:
            # Reset interval
            self.revision_interval_days = 1
        else:
            if self.revision_count == 0:
                self.revision_interval_days = 1
            elif self.revision_count == 1:
                self.revision_interval_days = 6
            else:
                self.revision_interval_days = int(
                    self.revision_interval_days * self.ease_factor
                )
        
        # Update ease factor
        self.ease_factor = max(1.3, self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        
        # Set next revision date
        self.next_revision_date = date.today() + timedelta(days=self.revision_interval_days)
        self.revision_count += 1
        self.last_revised = datetime.now(timezone.utc)
    
    def __repr__(self):
        return f"<TopicProficiency {self.topic_id} - {self.proficiency_score}>"


from datetime import timedelta


# ==================== Learning Goals ====================

class LearningGoal(Base, TimestampMixin):
    """
    User-defined or system-recommended learning goals.
    """
    __tablename__ = "learning_goals"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Goal details
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    goal_type = Column(String(50), nullable=False)  # topic_mastery, daily_study, quiz_score, etc.
    
    # Target
    target_value = Column(Float, nullable=False)  # Target to achieve
    current_value = Column(Float, default=0)
    unit = Column(String(50), nullable=True)  # minutes, percentage, count
    
    # Timeline
    start_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False)
    completed_date = Column(Date, nullable=True)
    
    # Status
    status = Column(String(20), default=LearningGoalStatus.ACTIVE.value)
    progress_percentage = Column(Float, default=0)
    
    # Related entities
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    
    # System flags
    is_system_generated = Column(Boolean, default=False)
    priority = Column(Integer, default=5)  # 1-10
    
    # Relationships
    user = relationship("User", backref="learning_goals")
    topic = relationship("Topic", backref="goals")
    
    def update_progress(self, new_value: float):
        """Update goal progress"""
        self.current_value = new_value
        self.progress_percentage = min((new_value / self.target_value) * 100, 100)
        
        if self.progress_percentage >= 100:
            self.status = LearningGoalStatus.COMPLETED.value
            self.completed_date = date.today()
    
    def __repr__(self):
        return f"<LearningGoal {self.title}>"


# ==================== Learning Milestones ====================

class LearningMilestone(Base, TimestampMixin):
    """
    Achievements and milestones reached by user.
    """
    __tablename__ = "learning_milestones"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Milestone info
    milestone_type = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    
    # Achievement details
    achieved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    value_achieved = Column(Float, nullable=True)  # e.g., 7 for 7-day streak
    
    # Related entities
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    
    # Display
    badge_icon = Column(String(100), nullable=True)
    points_earned = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", backref="milestones")
    
    def __repr__(self):
        return f"<LearningMilestone {self.title}>"


# ==================== Adaptive Learning State ====================

class AdaptiveLearningState(Base, TimestampMixin):
    """
    Stores the current adaptive learning state for a user.
    Used by the adaptive engine to make decisions.
    """
    __tablename__ = "adaptive_learning_states"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Current state
    current_load_level = Column(String(20), default="normal")  # light, normal, intensive
    burnout_risk = Column(Float, default=0.0)  # 0-100
    engagement_score = Column(Float, default=50.0)  # 0-100
    
    # Consistency metrics
    consistency_score = Column(Float, default=50.0)  # 0-100
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    missed_days_last_week = Column(Integer, default=0)
    
    # Performance metrics
    overall_accuracy = Column(Float, nullable=True)
    accuracy_trend = Column(String(20), default="stable")  # improving, stable, declining
    weak_topics_count = Column(Integer, default=0)
    
    # Recommendations state
    recommended_daily_minutes = Column(Integer, default=60)
    recommended_topics = Column(JSON, nullable=True)  # List of topic IDs
    topics_needing_revision = Column(JSON, nullable=True)  # List of topic IDs
    unlocked_content_ids = Column(JSON, nullable=True)  # Bonus content for performers
    
    # Flags
    needs_break = Column(Boolean, default=False)
    force_revision_mode = Column(Boolean, default=False)
    is_high_performer = Column(Boolean, default=False)
    
    # Last update
    last_evaluated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", backref="adaptive_state", uselist=False)
    
    def __repr__(self):
        return f"<AdaptiveLearningState {self.user_id}>"
