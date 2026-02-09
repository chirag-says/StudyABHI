"""
Quiz Models
Database models for quizzes, questions, and attempts.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, Text, ForeignKey, 
    DateTime, JSON, Float, Table
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.base import TimestampMixin


class DifficultyLevel(str, enum.Enum):
    """Question difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class QuizStatus(str, enum.Enum):
    """Quiz status"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AttemptStatus(str, enum.Enum):
    """Quiz attempt status"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# Association table for quiz-topic relationship
quiz_topics = Table(
    "quiz_topics",
    Base.metadata,
    Column("quiz_id", String(36), ForeignKey("quizzes.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", String(36), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
)


class Quiz(Base, TimestampMixin):
    """
    Quiz model containing multiple questions.
    Can be auto-generated or manually created.
    """
    __tablename__ = "quizzes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic info
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    
    # Configuration
    difficulty = Column(String(20), default=DifficultyLevel.MEDIUM.value)
    time_limit_minutes = Column(Integer, nullable=True)  # Optional time limit
    passing_score = Column(Integer, default=60)  # Percentage
    
    # Status
    status = Column(String(20), default=QuizStatus.DRAFT.value)
    is_ai_generated = Column(Boolean, default=False)
    
    # Source material
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_content = Column(Text, nullable=True)  # Original text used
    
    # Metadata
    question_count = Column(Integer, default=0)
    total_attempts = Column(Integer, default=0)
    average_score = Column(Float, nullable=True)
    
    # Owner
    created_by = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")
    topics = relationship("Topic", secondary=quiz_topics, backref="quizzes")
    creator = relationship("User", backref="created_quizzes")
    
    def __repr__(self):
        return f"<Quiz {self.title}>"


class QuizQuestion(Base, TimestampMixin):
    """
    Individual quiz question (MCQ format).
    """
    __tablename__ = "quiz_questions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String(36), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    
    # Question content
    question_text = Column(Text, nullable=False)
    question_number = Column(Integer, nullable=False)
    
    # Options (JSON array of 4 options)
    options = Column(JSON, nullable=False)  # ["Option A", "Option B", "Option C", "Option D"]
    correct_option = Column(Integer, nullable=False)  # 0-3 index
    
    # Explanation
    explanation = Column(Text, nullable=True)
    
    # Difficulty
    difficulty = Column(String(20), default=DifficultyLevel.MEDIUM.value)
    
    # Syllabus mapping
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    topic_name = Column(String(200), nullable=True)  # Denormalized for quick access
    
    # AI generation metadata
    source_chunk_id = Column(String(36), nullable=True)
    confidence_score = Column(Float, nullable=True)  # AI confidence in question quality
    
    # Statistics
    times_answered = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    topic = relationship("Topic", backref="questions")
    answers = relationship("QuestionAnswer", back_populates="question", cascade="all, delete-orphan")
    
    @property
    def accuracy_rate(self) -> float:
        """Calculate accuracy rate for this question"""
        if self.times_answered == 0:
            return 0.0
        return self.times_correct / self.times_answered * 100
    
    def __repr__(self):
        return f"<QuizQuestion {self.question_number}>"


class QuizAttempt(Base, TimestampMixin):
    """
    Record of a user's quiz attempt.
    """
    __tablename__ = "quiz_attempts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String(36), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Attempt info
    attempt_number = Column(Integer, default=1)  # Which attempt for this user
    status = Column(String(20), default=AttemptStatus.IN_PROGRESS.value)
    
    # Timing
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)
    
    # Results
    total_questions = Column(Integer, nullable=False)
    answered_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    wrong_answers = Column(Integer, default=0)
    skipped_questions = Column(Integer, default=0)
    
    # Score
    score_percentage = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    
    # Topic-wise performance (JSON)
    topic_performance = Column(JSON, nullable=True)  # {"topic_id": {"correct": 2, "total": 5}}
    
    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    user = relationship("User", backref="quiz_attempts")
    answers = relationship("QuestionAnswer", back_populates="attempt", cascade="all, delete-orphan")
    
    def calculate_score(self):
        """Calculate and update score"""
        if self.total_questions > 0:
            self.score_percentage = (self.correct_answers / self.total_questions) * 100
            self.passed = self.score_percentage >= self.quiz.passing_score if self.quiz else False
    
    def __repr__(self):
        return f"<QuizAttempt {self.id}>"


class QuestionAnswer(Base, TimestampMixin):
    """
    Individual answer within a quiz attempt.
    """
    __tablename__ = "question_answers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id = Column(String(36), ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(36), ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False)
    
    # Answer
    selected_option = Column(Integer, nullable=True)  # 0-3 index, null if skipped
    is_correct = Column(Boolean, nullable=True)
    
    # Timing
    time_spent_seconds = Column(Integer, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    
    # Flag for review
    marked_for_review = Column(Boolean, default=False)
    
    # Relationships
    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("QuizQuestion", back_populates="answers")
    
    def __repr__(self):
        return f"<QuestionAnswer {self.question_id}>"
