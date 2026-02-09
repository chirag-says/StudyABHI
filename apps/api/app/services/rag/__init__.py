"""
RAG Service Package
Retrieval-Augmented Generation for study materials.
"""
from app.services.rag.chunker import (
    SyllabusAwareChunker,
    SemanticChunk,
    SyllabusTag,
    ChunkType,
    chunk_study_material,
)
from app.services.rag.embeddings import (
    EmbeddingModel,
    EmbeddingPipeline,
    FAISSVectorStore,
    EmbeddingMetadata,
    SearchResult,
    create_embedding_pipeline,
)
from app.services.rag.pipeline import (
    RAGPipeline,
    RAGResponse,
    Citation,
    LLMProvider,
    OllamaClient,
    HuggingFaceClient,
    create_rag_pipeline,
    create_complete_rag_system,
    SYSTEM_PROMPT,
    RAG_PROMPT_TEMPLATE,
    ANALYTICAL_PROMPT_TEMPLATE,
    CONVERSATIONAL_PROMPT_TEMPLATE,
)

__all__ = [
    # Chunker
    "SyllabusAwareChunker",
    "SemanticChunk",
    "SyllabusTag",
    "ChunkType",
    "chunk_study_material",
    # Embeddings
    "EmbeddingModel",
    "EmbeddingPipeline",
    "FAISSVectorStore",
    "EmbeddingMetadata",
    "SearchResult",
    "create_embedding_pipeline",
    # Pipeline
    "RAGPipeline",
    "RAGResponse",
    "Citation",
    "LLMProvider",
    "OllamaClient",
    "HuggingFaceClient",
    "create_rag_pipeline",
    "create_complete_rag_system",
    # Prompts
    "SYSTEM_PROMPT",
    "RAG_PROMPT_TEMPLATE",
    "ANALYTICAL_PROMPT_TEMPLATE",
    "CONVERSATIONAL_PROMPT_TEMPLATE",
]
