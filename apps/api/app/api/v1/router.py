"""
API v1 Router
Main router that aggregates all v1 endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, users, health, syllabus, content, 
    documents, rag, tutor, quiz, learning, attention, privacy, feedback, roadmap
)


# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    syllabus.router,
    prefix="/syllabus",
    tags=["Syllabus"]
)

api_router.include_router(
    content.router,
    prefix="/content",
    tags=["Content"]
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"]
)

api_router.include_router(
    rag.router,
    prefix="/rag",
    tags=["RAG"]
)

api_router.include_router(
    tutor.router,
    prefix="/tutor",
    tags=["AI Tutor"]
)

api_router.include_router(
    quiz.router,
    prefix="/quiz",
    tags=["Quiz"]
)

api_router.include_router(
    learning.router,
    prefix="/learning",
    tags=["Learning Analytics"]
)

api_router.include_router(
    attention.router,
    prefix="/attention",
    tags=["Attention Tracking"]
)

api_router.include_router(
    privacy.router,
    tags=["Privacy"]
)

api_router.include_router(
    feedback.router,
    prefix="/feedback",
    tags=["Feedback"]
)

api_router.include_router(
    roadmap.router,
    prefix="/roadmap",
    tags=["Roadmap"]
)

