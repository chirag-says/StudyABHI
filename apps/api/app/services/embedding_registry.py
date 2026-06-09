"""
Embedding Registry
Global singleton holder for the EmbeddingPipeline.

Why this exists:
  document_service.py needs to index chunks into the SAME EmbeddingPipeline instance
  that the RAG query endpoints use (stored in app.state.embedding_pipeline).
  Since FastAPI's app.state is not easily accessible from a service layer, we keep
  a module-level reference here that main.py sets at startup.
"""
from typing import Optional

_pipeline = None


def set_pipeline(pipeline) -> None:
    """Called once at app startup with the singleton EmbeddingPipeline."""
    global _pipeline
    _pipeline = pipeline


def get_pipeline():
    """
    Returns the singleton EmbeddingPipeline, or None if not yet initialized.
    document_service uses this to index into the live in-memory store.
    """
    return _pipeline
