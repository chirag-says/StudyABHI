"""
Document API Endpoints
Upload, process, and manage documents (PDFs, etc.)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.document_service import DocumentService, MAX_FILE_SIZE
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentChunkResponse,
    ChunkListResponse,
    ProcessingTriggerResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    auto_process: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document (PDF, TXT, DOCX).
    
    - **file**: The document file (max 50MB)
    - **title**: Optional title (defaults to filename)
    - **description**: Optional description
    - **auto_process**: If true, automatically trigger text extraction
    
    Supported formats: PDF, TXT, DOCX
    
    Returns the created document with processing status.
    """
    # Validate file size early
    content = await file.read()
    file_size = len(content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )
    
    service = DocumentService(db)
    
    try:
        doc = await service.upload_document(
            file_content=content,
            filename=file.filename or "unknown",
            mime_type=file.content_type or "application/octet-stream",
            user_id=current_user.id,
            title=title,
            description=description,
        )
        
        # Trigger async processing if requested
        if auto_process:
            background_tasks.add_task(
                _process_document_background,
                doc.id,
                db,
            )
        
        await db.commit()
        
        return DocumentUploadResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_size=doc.file_size,
            status=doc.status,
            message="Document uploaded successfully" + 
                    (" - processing started" if auto_process else ""),
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List user's uploaded documents.
    
    Returns paginated list of documents with status info.
    """
    service = DocumentService(db)
    items, total = await service.get_user_documents(
        user_id=current_user.id,
        page=page,
        limit=limit,
    )
    
    pages = (total + limit - 1) // limit
    
    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get document details with chunks"""
    service = DocumentService(db)
    doc = await service.get_document(doc_id)
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if doc.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return doc


@router.get("/{doc_id}/chunks", response_model=ChunkListResponse)
async def get_document_chunks(
    doc_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get extracted text chunks from a document.
    
    Chunks are ready for RAG embedding/ingestion.
    """
    service = DocumentService(db)
    doc = await service.get_document(doc_id)
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if doc.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    items, total = await service.get_document_chunks(doc_id, page, limit)
    pages = (total + limit - 1) // limit
    
    return ChunkListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post("/{doc_id}/process", response_model=ProcessingTriggerResponse)
async def trigger_processing(
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually trigger document processing.
    
    Use this if auto_process was disabled during upload
    or to re-process a failed document.
    """
    service = DocumentService(db)
    doc = await service.get_document(doc_id)
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if doc.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if doc.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is already being processed"
        )
    
    # Add to background tasks
    background_tasks.add_task(
        _process_document_background,
        doc_id,
        db,
    )
    
    return ProcessingTriggerResponse(
        document_id=doc_id,
        status="processing",
        message="Processing started in background"
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and all its chunks"""
    service = DocumentService(db)
    
    try:
        deleted = await service.delete_document(doc_id, current_user.id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        await db.commit()
        return None
        
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document"
        )


# ==================== Background Task ====================

async def _process_document_background(doc_id: str, db: AsyncSession):
    """
    Background task to process document.
    
    Note: In production, use a proper task queue (Celery, etc.)
    """
    try:
        service = DocumentService(db)
        await service.process_document(doc_id)
        await db.commit()
        logger.info(f"Background processing completed: {doc_id}")
    except Exception as e:
        logger.error(f"Background processing failed: {doc_id} - {e}")
        await db.rollback()
