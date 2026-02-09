"""
Document Service
Business logic for document upload and processing
"""
import os
import uuid
import aiofiles
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import logging

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.pdf_extractor import PDFExtractor, ExtractionResult
from app.services.rag.embeddings import EmbeddingPipeline, create_embedding_pipeline

logger = logging.getLogger(__name__)

# Configuration
UPLOAD_DIR = Path("uploads/documents")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


class DocumentService:
    """Service class for document operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.upload_dir = UPLOAD_DIR
        self.extractor = PDFExtractor(
            chunk_size=1000,
            chunk_overlap=200,
            min_chunk_size=100,
        )
    
    # ==================== Document CRUD ====================
    
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        result = await self.db.execute(
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_documents(
        self, 
        user_id: str,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Document], int]:
        """Get documents for a user with pagination"""
        # Count query
        count_result = await self.db.execute(
            select(func.count(Document.id))
            .where(Document.user_id == user_id)
        )
        total = count_result.scalar() or 0
        
        # Data query
        offset = (page - 1) * limit
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        
        return items, total
    
    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Document:
        """
        Upload and save a document.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            mime_type: MIME type
            user_id: Owner's user ID
            title: Optional title
            description: Optional description
            
        Returns:
            Created Document instance
            
        Raises:
            ValueError: If file validation fails
        """
        # Validate file
        self._validate_file(filename, len(file_content), mime_type)
        
        # Generate unique filename
        file_ext = Path(filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file to disk
        file_path = self.upload_dir / unique_filename
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        # Create document record
        doc = Document(
            filename=unique_filename,
            original_filename=filename,
            file_path=str(file_path),
            file_size=len(file_content),
            file_type=file_ext.lstrip('.'),
            mime_type=mime_type,
            title=title or Path(filename).stem,
            description=description,
            status=DocumentStatus.PENDING.value,
            user_id=user_id,
        )
        
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        
        logger.info(f"Document uploaded: {doc.id} - {filename}")
        
        return doc
    
    async def process_document(self, doc_id: str) -> Document:
        """
        Process a document: extract text and create chunks.
        
        This should ideally be run as a background task.
        
        Args:
            doc_id: Document ID to process
            
        Returns:
            Updated Document with processing results
        """
        doc = await self.get_document(doc_id)
        if not doc:
            raise ValueError(f"Document not found: {doc_id}")
        
        # Update status to processing
        doc.status = DocumentStatus.PROCESSING.value
        doc.processing_started_at = datetime.now(timezone.utc)
        await self.db.flush()
        
        try:
            # Extract text based on file type
            if doc.file_type == "pdf":
                result = await self._extract_pdf(doc.file_path)
            elif doc.file_type == "txt":
                result = await self._extract_txt(doc.file_path)
            else:
                raise ValueError(f"Unsupported file type: {doc.file_type}")
            
            if not result.success:
                raise Exception("; ".join(result.errors))
            
            # Save chunks to database
            chunks_to_embed = []
            for chunk in result.chunks:
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    chunk_type=chunk.chunk_type,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    token_count=chunk.token_count,
                )
                self.db.add(db_chunk)
                chunks_to_embed.append(db_chunk) # Collect for embedding
            
            await self.db.flush() # Flush to get IDs
            
            # Update document with results
            doc.status = DocumentStatus.COMPLETED.value
            doc.processing_completed_at = datetime.now(timezone.utc)
            doc.page_count = result.page_count
            doc.chunk_count = len(result.chunks)
            doc.word_count = result.word_count
            doc.extra_metadata = result.metadata
            
            await self.db.flush()
            await self.db.refresh(doc)
            
            logger.info(f"Document processed: {doc.id} - {len(result.chunks)} chunks")
            
            # --- Auto-Index into Vector Store ---
            try:
                logger.info(f"Indexing document {doc.id} into vector store...")
                embedding_pipeline = EmbeddingPipeline(storage_path="data/vectors")
                
                # Make sure we load existing index first
                try:
                    embedding_pipeline.load()
                except Exception:
                    pass
                
                # Convert to format expected by index_chunks
                chunk_dicts = [
                    {
                        "id": str(db_chunk.id),  # Use UUID from DB
                        "content": db_chunk.content,
                        "document_id": doc.id,
                        "chunk_type": db_chunk.chunk_type,
                        "syllabus_tags": [], # Metadata not available at this stage yet
                        "source": doc.original_filename,
                    }
                    for db_chunk in chunks_to_embed 
                ]
                
                await embedding_pipeline.index_chunks(
                    chunks=chunk_dicts,
                    user_id=doc.user_id,
                )
                # Note: index_chunks now auto-saves
                logger.info(f"Successfully indexed document {doc.id}")
                
            except Exception as e:
                logger.error(f"Failed to index document {doc.id}: {e}")
                # Don't fail the whole process, just log it
                # We can retry indexing later manually if needed
            
        except Exception as e:
            logger.error(f"Document processing failed: {doc.id} - {e}")
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = str(e)
            await self.db.flush()
            raise
        
        return doc
    
    async def delete_document(self, doc_id: str, user_id: str) -> bool:
        """Delete a document and its file"""
        doc = await self.get_document(doc_id)
        
        if not doc:
            return False
        
        if doc.user_id != user_id:
            raise PermissionError("Not authorized to delete this document")
        
        # Delete file from disk
        try:
            file_path = Path(doc.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete file: {e}")
        
        # Delete from database (cascades to chunks)
        await self.db.delete(doc)
        await self.db.flush()
        
        return True
    
    async def get_document_chunks(
        self, 
        doc_id: str,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[DocumentChunk], int]:
        """Get chunks for a document with pagination"""
        count_result = await self.db.execute(
            select(func.count(DocumentChunk.id))
            .where(DocumentChunk.document_id == doc_id)
        )
        total = count_result.scalar() or 0
        
        offset = (page - 1) * limit
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc_id)
            .order_by(DocumentChunk.chunk_index)
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        
        return items, total
    
    # ==================== Private Methods ====================
    
    def _validate_file(
        self, 
        filename: str, 
        file_size: int, 
        mime_type: str
    ) -> None:
        """Validate uploaded file"""
        # Check file size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB"
            )
        
        if file_size == 0:
            raise ValueError("File is empty")
        
        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check MIME type
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Invalid file type: {mime_type}")
    
    async def _extract_pdf(self, file_path: str) -> ExtractionResult:
        """Extract text from PDF file"""
        return self.extractor.extract_from_file(file_path)
    
    async def _extract_txt(self, file_path: str) -> ExtractionResult:
        """Extract text from TXT file"""
        from app.services.pdf_extractor import TextChunk, ExtractionResult
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Split into chunks
            chunks = []
            chunk_size = 1000
            
            paragraphs = content.split('\n\n')
            current_chunk = ""
            chunk_index = 0
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                if len(current_chunk) + len(para) > chunk_size:
                    if current_chunk:
                        chunks.append(TextChunk(
                            content=current_chunk,
                            chunk_type="paragraph",
                            page_number=1,
                            chunk_index=chunk_index,
                        ))
                        chunk_index += 1
                    current_chunk = para
                else:
                    current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            
            if current_chunk:
                chunks.append(TextChunk(
                    content=current_chunk,
                    chunk_type="paragraph",
                    page_number=1,
                    chunk_index=chunk_index,
                ))
            
            return ExtractionResult(
                chunks=chunks,
                page_count=1,
                word_count=len(content.split()),
                metadata={"format": "txt"},
            )
            
        except Exception as e:
            return ExtractionResult(
                chunks=[],
                page_count=0,
                word_count=0,
                metadata={},
                errors=[str(e)],
            )
