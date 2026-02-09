"""
Models Package
Export all SQLAlchemy models
"""
from app.models.base import TimestampMixin
from app.models.user import User, UserRole, ExamType as UserExamType
from app.models.syllabus import (
    ExamType,
    ExamStage,
    Paper,
    Subject,
    Topic,
    content_topics,
)
from app.models.content import (
    Content,
    ContentTag,
    ContentRevision,
    ContentType,
    DifficultyLevel,
    Language,
    ContentStatus,
    content_tag_associations,
)
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
)
from app.models.quiz import (
    Quiz,
    QuizQuestion,
    QuizAttempt,
    QuestionAnswer,
    QuizStatus,
    AttemptStatus,
    quiz_topics,
)
from app.models.learning import (
    StudySession,
    DailyProgress,
    TopicProficiency,
    LearningGoal,
    LearningMilestone,
    AdaptiveLearningState,
    SessionType,
    LearningGoalStatus,
    MilestoneType,
)
from app.models.attention import (
    AttentionSession,
    DailyAttentionSummary,
    AttentionInsight,
    UserAttentionPreferences,
    AttentionLevel,
)
from app.models.privacy import (
    UserPrivacySettings,
    DataExportRequest,
    AccountDeletionRequest,
)
from app.models.roadmap import (
    UserStudyPlan,
    StudyPhase,
    DailyStudyTask,
    WeeklyPlan,
    PreparationLevel,
    StudyPreference,
    TaskStatus,
    TaskType,
)

__all__ = [
    # Base
    "TimestampMixin",
    # User
    "User",
    "UserRole",
    "UserExamType",
    # Syllabus
    "ExamType",
    "ExamStage", 
    "Paper",
    "Subject",
    "Topic",
    "content_topics",
    # Content
    "Content",
    "ContentTag",
    "ContentRevision",
    "ContentType",
    "DifficultyLevel",
    "Language",
    "ContentStatus",
    "content_tag_associations",
    # Document
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "DocumentType",
    # Quiz
    "Quiz",
    "QuizQuestion",
    "QuizAttempt",
    "QuestionAnswer",
    "QuizStatus",
    "AttemptStatus",
    "quiz_topics",
    # Learning
    "StudySession",
    "DailyProgress",
    "TopicProficiency",
    "LearningGoal",
    "LearningMilestone",
    "AdaptiveLearningState",
    "SessionType",
    "LearningGoalStatus",
    "MilestoneType",
    # Attention
    "AttentionSession",
    "DailyAttentionSummary",
    "AttentionInsight",
    "UserAttentionPreferences",
    "AttentionLevel",
    # Privacy
    "UserPrivacySettings",
    "DataExportRequest",
    "AccountDeletionRequest",
    # Roadmap
    "UserStudyPlan",
    "StudyPhase",
    "DailyStudyTask",
    "WeeklyPlan",
    "PreparationLevel",
    "StudyPreference",
    "TaskStatus",
    "TaskType",
]

