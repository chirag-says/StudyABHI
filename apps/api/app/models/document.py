"""
Document Model
For storing uploaded documents (PDFs, etc.)
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, Text, ForeignKey, DateTime, JSON
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.base import TimestampMixin


class DocumentStatus(str, enum.Enum):
    """Document processing status"""
    PENDING = "pending"          # Uploaded, awaiting processing
    PROCESSING = "processing"    # Currently being processed
    COMPLETED = "completed"      # Successfully processed
    FAILED = "failed"           # Processing failed
    

class DocumentType(str, enum.Enum):
    """Document types"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class Document(Base, TimestampMixin):
    """
    Uploaded document model for PDFs and other files.
    
    Stores metadata and processing status.
    Extracted content is stored as chunks for RAG.
    """
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # File info
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Storage path
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String(20), default=DocumentType.PDF.value)
    mime_type = Column(String(100), nullable=True)
    
    # Metadata
    title = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    
    # Processing status
    status = Column(String(20), default=DocumentStatus.PENDING.value)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Extracted data stats
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, default=0)
    word_count = Column(Integer, nullable=True)
    
    # Additional metadata (JSON)
    extra_metadata = Column(JSON, nullable=True)  # For PDF metadata like author, creation date
    
    # Owner
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    user = relationship("User", backref="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document {self.filename}>"


class DocumentChunk(Base, TimestampMixin):
    """
    Extracted text chunks from documents.
    Ready for embedding and RAG ingestion.
    """
    __tablename__ = "document_chunks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Chunk content
    content = Column(Text, nullable=False)
    
    # Position info
    chunk_index = Column(Integer, nullable=False)  # Order within document
    page_number = Column(Integer, nullable=True)   # Source page (if applicable)
    
    # Chunk type (heading, paragraph, list, etc.)
    chunk_type = Column(String(50), default="paragraph")
    
    # Character positions (for highlighting in original)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    
    # Token count (for LLM context management)
    token_count = Column(Integer, nullable=True)
    
    # Embedding stored flag
    is_embedded = Column(Boolean, default=False)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<DocumentChunk {self.document_id}:{self.chunk_index}>"
