"""
Database Schema Improvements
Improved models with proper constraints, indexes, and JSONB usage
"""

from sqlalchemy import (
    Column, String, Boolean, Integer, Text, ForeignKey, DateTime, 
    Float, Date, CheckConstraint, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone

from app.core.database import Base
from app.models.base import TimestampMixin


# ============================================================
# IMPROVEMENT 1: Enhanced Document Model
# ============================================================

class DocumentImproved(Base, TimestampMixin):
    """
    Improved Document model with better constraints
    """
    __tablename__ = "documents_v2"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # File info - all NOT NULL
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(20), nullable=False)  # Made NOT NULL
    mime_type = Column(String(100), nullable=False)  # Made NOT NULL
    
    # Metadata
    title = Column(String(300), nullable=False)  # Made NOT NULL, default to filename
    description = Column(Text, nullable=True)
    
    # Processing status with constraint
    status = Column(String(20), nullable=False, default="pending")
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Stats
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    word_count = Column(Integer, nullable=True)
    
    # JSONB for flexible metadata (PostgreSQL)
    extra_metadata = Column(JSONB, nullable=True, default={})
    # Example: {"author": "...", "creation_date": "...", "pdf_version": "1.7"}
    
    # Owner
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    user = relationship("User", backref="documents_v2")
    chunks = relationship("DocumentChunkImproved", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        # Status constraint
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_document_status"
        ),
        # File size constraint (max 100MB)
        CheckConstraint(
            "file_size > 0 AND file_size <= 104857600",
            name="ck_document_file_size"
        ),
        # Indexes
        Index("ix_documents_user_id", "user_id"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_user_created", "user_id", "created_at"),
    )


class DocumentChunkImproved(Base, TimestampMixin):
    """
    Improved chunk model with JSONB for embedding metadata
    """
    __tablename__ = "document_chunks_v2"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents_v2.id", ondelete="CASCADE"), nullable=False)
    
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    chunk_type = Column(String(50), nullable=False, default="paragraph")
    
    # Character positions
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    
    # Token count with constraint
    token_count = Column(Integer, nullable=True)
    
    # Embedding status
    is_embedded = Column(Boolean, nullable=False, default=False)
    embedded_at = Column(DateTime(timezone=True), nullable=True)
    
    # JSONB for embedding metadata
    embedding_metadata = Column(JSONB, nullable=True, default={})
    # Example: {"model": "all-MiniLM-L6-v2", "dimension": 384, "vector_id": "..."}
    
    # Relationships
    document = relationship("DocumentImproved", back_populates="chunks")
    
    __table_args__ = (
        # Chunk index constraint
        CheckConstraint("chunk_index >= 0", name="ck_chunk_index"),
        # Indexes
        Index("ix_chunks_document_id", "document_id"),
        Index("ix_chunks_embedded", "is_embedded"),
        # Unique chunk index per document
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )


# ============================================================
# IMPROVEMENT 2: Enhanced Quiz Models
# ============================================================

class QuizImproved(Base, TimestampMixin):
    """
    Improved Quiz model with JSONB for flexible settings
    """
    __tablename__ = "quizzes_v2"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic info - NOT NULL
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    
    # Configuration
    difficulty = Column(String(20), nullable=False, default="medium")
    time_limit_minutes = Column(Integer, nullable=True)
    passing_score = Column(Integer, nullable=False, default=60)
    
    # Status
    status = Column(String(20), nullable=False, default="draft")
    is_ai_generated = Column(Boolean, nullable=False, default=False)
    
    # Source (optional FK)
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    
    # JSONB for generation metadata
    generation_metadata = Column(JSONB, nullable=True, default={})
    # Example: {"model": "gpt-4", "prompt_tokens": 1000, "template": "upsc_prelims"}
    
    # JSONB for quiz settings
    settings = Column(JSONB, nullable=False, default={
        "shuffle_questions": True,
        "shuffle_options": True,
        "show_explanations": True,
        "allow_review": True
    })
    
    # Stats
    question_count = Column(Integer, nullable=False, default=0)
    total_attempts = Column(Integer, nullable=False, default=0)
    average_score = Column(Float, nullable=True)
    
    # Owner
    created_by = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    __table_args__ = (
        # Status constraint
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_quiz_status"
        ),
        # Difficulty constraint
        CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard', 'expert')",
            name="ck_quiz_difficulty"
        ),
        # Passing score constraint
        CheckConstraint(
            "passing_score >= 0 AND passing_score <= 100",
            name="ck_quiz_passing_score"
        ),
        # Indexes
        Index("ix_quizzes_created_by", "created_by"),
        Index("ix_quizzes_status", "status"),
    )


class QuizAttemptImproved(Base, TimestampMixin):
    """
    Improved attempt model with JSONB for analytics
    """
    __tablename__ = "quiz_attempts_v2"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String(36), ForeignKey("quizzes_v2.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Attempt info
    attempt_number = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="in_progress")
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)
    
    # Results - all NOT NULL with defaults
    total_questions = Column(Integer, nullable=False)
    answered_questions = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    wrong_answers = Column(Integer, nullable=False, default=0)
    skipped_questions = Column(Integer, nullable=False, default=0)
    
    # Score
    score_percentage = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    
    # JSONB for detailed analytics
    topic_performance = Column(JSONB, nullable=True, default={})
    # Example: {"topic_id_1": {"correct": 2, "total": 5, "time_spent": 120}}
    
    difficulty_breakdown = Column(JSONB, nullable=True, default={})
    # Example: {"easy": {"correct": 3, "total": 3}, "hard": {"correct": 1, "total": 3}}
    
    time_analytics = Column(JSONB, nullable=True, default={})
    # Example: {"avg_time_per_question": 45, "fastest": 10, "slowest": 120}
    
    __table_args__ = (
        # Status constraint
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name="ck_attempt_status"
        ),
        # Score constraint
        CheckConstraint(
            "score_percentage IS NULL OR (score_percentage >= 0 AND score_percentage <= 100)",
            name="ck_attempt_score"
        ),
        # Indexes
        Index("ix_attempts_user_id", "user_id"),
        Index("ix_attempts_quiz_id", "quiz_id"),
        Index("ix_attempts_user_quiz", "user_id", "quiz_id"),
        Index("ix_attempts_completed", "user_id", "completed_at"),
    )


# ============================================================
# IMPROVEMENT 3: Enhanced Learning Models
# ============================================================

class DailyProgressImproved(Base, TimestampMixin):
    """
    Improved daily progress with JSONB for flexible tracking
    """
    __tablename__ = "daily_progress_v2"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    
    # Core metrics - NOT NULL with defaults
    total_study_minutes = Column(Integer, nullable=False, default=0)
    topics_studied = Column(Integer, nullable=False, default=0)
    quizzes_taken = Column(Integer, nullable=False, default=0)
    questions_answered = Column(Integer, nullable=False, default=0)
    questions_correct = Column(Integer, nullable=False, default=0)
    
    # Calculated
    daily_accuracy = Column(Float, nullable=True)
    goal_achieved = Column(Boolean, nullable=False, default=False)
    
    # JSONB for detailed breakdown
    study_breakdown = Column(JSONB, nullable=False, default={
        "reading_minutes": 0,
        "quiz_minutes": 0,
        "revision_minutes": 0,
        "video_minutes": 0
    })
    
    topic_breakdown = Column(JSONB, nullable=True, default={})
    # Example: {"topic_id_1": {"minutes": 30, "questions": 10}}
    
    session_details = Column(JSONB, nullable=True, default=[])
    # Example: [{"type": "reading", "start": "...", "duration": 30}]
    
    __table_args__ = (
        # Unique user-date
        UniqueConstraint("user_id", "date", name="uq_user_date"),
        # Accuracy constraint
        CheckConstraint(
            "daily_accuracy IS NULL OR (daily_accuracy >= 0 AND daily_accuracy <= 100)",
            name="ck_daily_accuracy"
        ),
        # Indexes
        Index("ix_daily_progress_user_date", "user_id", "date"),
    )


# ============================================================
# IMPROVEMENT 4: AI Conversation Model (New)
# ============================================================

class AIConversation(Base, TimestampMixin):
    """
    Track AI conversations for learning assistance
    """
    __tablename__ = "ai_conversations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Conversation type
    conversation_type = Column(String(50), nullable=False, default="general")
    # Types: "general", "quiz_help", "explanation", "doubt_solving"
    
    # Topic association
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # JSONB for messages
    messages = Column(JSONB, nullable=False, default=[])
    # Example: [{"role": "user", "content": "...", "timestamp": "..."}]
    
    # JSONB for context/citations
    context = Column(JSONB, nullable=True, default={})
    # Example: {"retrieved_chunks": [...], "topic_context": "..."}
    
    # Usage tracking
    total_tokens = Column(Integer, nullable=False, default=0)
    message_count = Column(Integer, nullable=False, default=0)
    
    # AI model info
    model_used = Column(String(50), nullable=True)
    
    __table_args__ = (
        # Type constraint
        CheckConstraint(
            "conversation_type IN ('general', 'quiz_help', 'explanation', 'doubt_solving', 'rag_query')",
            name="ck_conversation_type"
        ),
        # Indexes
        Index("ix_conversations_user_id", "user_id"),
        Index("ix_conversations_user_active", "user_id", "is_active"),
        Index("ix_conversations_topic", "topic_id"),
    )


# ============================================================
# IMPROVEMENT 5: Roadmap/Study Plan Model (New)
# ============================================================

class StudyRoadmap(Base, TimestampMixin):
    """
    Personalized study roadmap for users
    """
    __tablename__ = "study_roadmaps"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Target exam
    exam_type = Column(String(50), nullable=False)
    target_date = Column(Date, nullable=True)
    
    # JSONB for roadmap structure
    phases = Column(JSONB, nullable=False, default=[])
    # Example: [{"phase": 1, "name": "Foundation", "topics": [...], "start": "...", "end": "..."}]
    
    current_phase = Column(Integer, nullable=False, default=1)
    overall_progress = Column(Float, nullable=False, default=0.0)
    
    # JSONB for task tracking
    tasks = Column(JSONB, nullable=False, default=[])
    # Example: [{"id": "...", "type": "study", "topic_id": "...", "status": "pending"}]
    
    # JSONB for recommendations
    recommendations = Column(JSONB, nullable=True, default={})
    # Example: {"priority_topics": [...], "weak_areas": [...], "next_actions": [...]}
    
    # Last update
    last_updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        # Progress constraint
        CheckConstraint(
            "overall_progress >= 0 AND overall_progress <= 100",
            name="ck_roadmap_progress"
        ),
        # Indexes
        Index("ix_roadmaps_user_id", "user_id"),
    )


class RoadmapTask(Base, TimestampMixin):
    """
    Individual tasks in a study roadmap
    """
    __tablename__ = "roadmap_tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    roadmap_id = Column(String(36), ForeignKey("study_roadmaps.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Task details
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False)  # "study", "quiz", "revision", "practice"
    
    # Related entities
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    content_id = Column(String(36), ForeignKey("contents.id", ondelete="SET NULL"), nullable=True)
    quiz_id = Column(String(36), ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=5)  # 1-10
    
    # Scheduling
    scheduled_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Estimated vs actual
    estimated_minutes = Column(Integer, nullable=True)
    actual_minutes = Column(Integer, nullable=True)
    
    # JSONB for task metadata
    metadata = Column(JSONB, nullable=True, default={})
    # Example: {"generated_by": "adaptive_engine", "reason": "weak_area"}
    
    __table_args__ = (
        # Status constraint
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'skipped')",
            name="ck_task_status"
        ),
        # Priority constraint
        CheckConstraint(
            "priority >= 1 AND priority <= 10",
            name="ck_task_priority"
        ),
        # Indexes
        Index("ix_tasks_user_id", "user_id"),
        Index("ix_tasks_roadmap_id", "roadmap_id"),
        Index("ix_tasks_status", "user_id", "status"),
        Index("ix_tasks_scheduled", "user_id", "scheduled_date"),
    )
