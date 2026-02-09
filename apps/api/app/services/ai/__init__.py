"""
AI Services Package
AI-powered features for UPSC learning platform.
"""
from app.services.ai.tutor import (
    AITutor,
    TutorResponse,
    VerbosityLevel,
    OutputLanguage,
    QuestionType,
    create_ai_tutor,
)
from app.services.ai.summarizer import (
    DocumentSummarizer,
    DocumentSummary,
    SummaryFormat,
    SummaryLength,
    SummaryLanguage,
    create_summarizer,
)
from app.services.ai.quiz_generator import (
    QuizGenerator,
    GeneratedQuestion,
    QuizGenerationResult,
    QuestionDifficulty,
    create_quiz_generator,
)

__all__ = [
    # Tutor
    "AITutor",
    "TutorResponse",
    "VerbosityLevel",
    "OutputLanguage",
    "QuestionType",
    "create_ai_tutor",
    # Summarizer
    "DocumentSummarizer",
    "DocumentSummary",
    "SummaryFormat",
    "SummaryLength",
    "SummaryLanguage",
    "create_summarizer",
    # Quiz Generator
    "QuizGenerator",
    "GeneratedQuestion",
    "QuizGenerationResult",
    "QuestionDifficulty",
    "create_quiz_generator",
]

