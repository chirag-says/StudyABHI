"""
UPSC AI Platform - FastAPI Backend
Main application entry point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1.router import api_router

import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # ── Startup ──────────────────────────────────────────────
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")

    # Initialize database tables
    if settings.is_development:
        logger.info("Initializing database...")
        await init_db()

    # ── Singleton RAG Pipeline ───────────────────────────────
    # Create one EmbeddingPipeline for the entire app lifetime.
    # All endpoints share this instance via app.state.embedding_pipeline.
    # document_service also uses this SAME instance via embedding_registry
    # so indexed documents are immediately queryable.
    try:
        from app.services.rag.embeddings import EmbeddingPipeline
        from app.services import embedding_registry
        from pathlib import Path

        vector_path = settings.VECTOR_STORAGE_PATH
        Path(vector_path).mkdir(parents=True, exist_ok=True)

        embedding_pipeline = EmbeddingPipeline(
            model_name=settings.NVIDIA_EMBED_MODEL,
            storage_path=vector_path,
            dimension=settings.NVIDIA_EMBED_DIM,
        )
        app.state.embedding_pipeline = embedding_pipeline

        # Register as global singleton so document_service indexes into the same instance
        embedding_registry.set_pipeline(embedding_pipeline)

        logger.info(f"RAG embedding pipeline ready ({embedding_pipeline.vector_store.size} vectors in store)")
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline (non-fatal): {e}")
        app.state.embedding_pipeline = None

    yield

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("Shutting down StudyABHI...")

    # Save vector store before exit
    try:
        if app.state.embedding_pipeline is not None:
            app.state.embedding_pipeline.save()
            logger.info("Vector store saved to disk.")
    except Exception as e:
        logger.warning(f"Could not save vector store on shutdown: {e}")

    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## 📚 StudyABHI — UPSC AI Learning Platform

    AI-powered study companion for UPSC exam preparation.

    ### Features
    - 🔐 JWT Authentication
    - 📄 PDF Upload & Auto-indexing
    - 🤖 RAG-based Q&A with Citations
    - 🧠 AI Quiz Generation
    - 📝 Document Summarization
    - 🗺️ Personalized Study Roadmap
    """,
    version=settings.APP_VERSION,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with cleaner messages"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled error on {request.method} {request.url}: {exc}", exc_info=True)

    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs" if not settings.is_production else None,
        "health": "/api/v1/health"
    }


# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development
    )
