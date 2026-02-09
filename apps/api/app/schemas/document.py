"""
Document Schemas
Pydantic models for document upload and management
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class DocumentStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentTypeEnum(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


# ==================== Document Schemas ====================

class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    id: str
    filename: str
    original_filename: str
    file_size: int
    status: str
    message: str


class DocumentResponse(BaseModel):
    """Document response schema"""
    id: str
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: str
    page_count: Optional[int] = None
    chunk_count: int = 0
    word_count: Optional[int] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    """Detailed document with chunks"""
    chunks: List["DocumentChunkResponse"] = []


class DocumentListResponse(BaseModel):
    """Paginated document list"""
    items: List[DocumentResponse]
    total: int
    page: int
    limit: int
    pages: int
    
    @property
    def documents(self) -> List[DocumentResponse]:
        """Alias for items for backward compatibility"""
        return self.items
    
    def model_dump(self, **kwargs):
        """Override to include documents alias"""
        d = super().model_dump(**kwargs)
        d["documents"] = d["items"]
        return d


# ==================== Chunk Schemas ====================

class DocumentChunkResponse(BaseModel):
    """Document chunk response"""
    id: str
    chunk_index: int
    content: str
    chunk_type: str
    page_number: Optional[int] = None
    token_count: Optional[int] = None
    is_embedded: bool = False
    
    class Config:
        from_attributes = True


class ChunkListResponse(BaseModel):
    """Paginated chunk list"""
    items: List[DocumentChunkResponse]
    total: int
    page: int
    limit: int
    pages: int


# ==================== Processing Schemas ====================

class ProcessingTriggerResponse(BaseModel):
    """Response when triggering document processing"""
    document_id: str
    status: str
    message: str


class ExtractionResultResponse(BaseModel):
    """PDF extraction result"""
    success: bool
    page_count: int
    chunk_count: int
    word_count: int
    errors: List[str] = []


# Update forward references
DocumentDetailResponse.model_rebuild()
