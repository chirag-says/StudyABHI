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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📍 Environment: {settings.ENVIRONMENT}")
    
    # Initialize database tables (dev only - use Alembic in production)
    if settings.is_development:
        print("📦 Initializing database...")
        await init_db()  # Auto-create tables in development
    
    yield
    
    # Shutdown
    print("🔌 Shutting down...")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## 📚 UPSC AI Learning Platform API
    
    AI-powered learning platform for UPSC exam preparation.
    
    ### Features
    - 🔐 JWT Authentication
    - 👤 User Management
    - 📝 Quiz Generation (Coming Soon)
    - 🤖 RAG-based Q&A (Coming Soon)
    - 📄 Content Summarization (Coming Soon)
    
    ### Supported Exams
    - UPSC (Current)
    - JEE (Planned)
    - NEET (Planned)
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
    # Log the error (in production, use proper logging)
    print(f"❌ Unhandled error: {exc}")
    
    # Don't expose internal errors in production
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
