"""
PDF Extraction Service
Extract clean, structured text from PDFs for RAG ingestion.

Uses PyMuPDF (fitz) for robust PDF parsing.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents an extracted text chunk"""
    content: str
    chunk_type: str  # heading, paragraph, list, table, code
    page_number: int
    chunk_index: int
    start_char: int = 0
    end_char: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def token_count(self) -> int:
        """Estimate token count (rough approximation: 1 token ≈ 4 chars)"""
        return len(self.content) // 4


@dataclass 
class ExtractionResult:
    """Result of PDF extraction"""
    chunks: List[TextChunk]
    page_count: int
    word_count: int
    metadata: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        return len(self.chunks) > 0


class PDFExtractor:
    """
    Extract structured text from PDF files.
    
    Features:
    - Heading detection based on font size
    - Paragraph grouping
    - Configurable chunk size for RAG
    - Metadata extraction
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,      # Target chars per chunk
        chunk_overlap: int = 200,     # Overlap between chunks
        min_chunk_size: int = 100,    # Minimum chunk size
        detect_headings: bool = True,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.detect_headings = detect_headings
    
    def extract_from_file(self, file_path: str) -> ExtractionResult:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ExtractionResult with chunks and metadata
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install pymupdf")
            return ExtractionResult(
                chunks=[],
                page_count=0,
                word_count=0,
                metadata={},
                errors=["PyMuPDF not installed"]
            )
        
        errors = []
        all_blocks = []
        metadata = {}
        
        try:
            doc = fitz.open(file_path)
            
            # Extract metadata
            metadata = self._extract_metadata(doc)
            page_count = len(doc)
            
            # Extract text blocks from each page
            for page_num in range(page_count):
                try:
                    page = doc[page_num]
                    blocks = self._extract_page_blocks(page, page_num + 1)
                    all_blocks.extend(blocks)
                except Exception as e:
                    errors.append(f"Error on page {page_num + 1}: {str(e)}")
                    logger.warning(f"Error extracting page {page_num + 1}: {e}")
            
            doc.close()
            
            # Process blocks into chunks
            chunks = self._create_chunks(all_blocks)
            
            # Calculate word count
            word_count = sum(len(chunk.content.split()) for chunk in chunks)
            
            return ExtractionResult(
                chunks=chunks,
                page_count=page_count,
                word_count=word_count,
                metadata=metadata,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Failed to extract PDF: {e}")
            return ExtractionResult(
                chunks=[],
                page_count=0,
                word_count=0,
                metadata={},
                errors=[f"Extraction failed: {str(e)}"]
            )
    
    def extract_from_bytes(self, pdf_bytes: bytes) -> ExtractionResult:
        """Extract text from PDF bytes (for in-memory processing)"""
        try:
            import fitz
        except ImportError:
            return ExtractionResult(
                chunks=[],
                page_count=0,
                word_count=0,
                metadata={},
                errors=["PyMuPDF not installed"]
            )
        
        errors = []
        all_blocks = []
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            metadata = self._extract_metadata(doc)
            page_count = len(doc)
            
            for page_num in range(page_count):
                try:
                    page = doc[page_num]
                    blocks = self._extract_page_blocks(page, page_num + 1)
                    all_blocks.extend(blocks)
                except Exception as e:
                    errors.append(f"Error on page {page_num + 1}: {str(e)}")
            
            doc.close()
            
            chunks = self._create_chunks(all_blocks)
            word_count = sum(len(chunk.content.split()) for chunk in chunks)
            
            return ExtractionResult(
                chunks=chunks,
                page_count=page_count,
                word_count=word_count,
                metadata=metadata,
                errors=errors
            )
            
        except Exception as e:
            return ExtractionResult(
                chunks=[],
                page_count=0,
                word_count=0,
                metadata={},
                errors=[f"Extraction failed: {str(e)}"]
            )
    
    def _extract_metadata(self, doc) -> Dict[str, Any]:
        """Extract PDF metadata"""
        try:
            meta = doc.metadata
            return {
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "subject": meta.get("subject", ""),
                "keywords": meta.get("keywords", ""),
                "creator": meta.get("creator", ""),
                "producer": meta.get("producer", ""),
                "creation_date": meta.get("creationDate", ""),
                "modification_date": meta.get("modDate", ""),
            }
        except Exception:
            return {}
    
    def _extract_page_blocks(self, page, page_num: int) -> List[Dict]:
        """
        Extract text blocks from a page with formatting info.
        
        Uses PyMuPDF's text extraction with detailed block info.
        """
        blocks = []
        
        # Get text blocks with detailed info
        # flags: TEXT_PRESERVE_WHITESPACE | TEXT_PRESERVE_LIGATURES
        text_dict = page.get_text("dict", flags=11)
        
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                block_text = ""
                max_font_size = 0
                font_flags = set()
                
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        text = span.get("text", "")
                        line_text += text
                        
                        # Track font properties for heading detection
                        font_size = span.get("size", 12)
                        if font_size > max_font_size:
                            max_font_size = font_size
                        
                        flags = span.get("flags", 0)
                        if flags & 2**0:  # Superscript
                            font_flags.add("superscript")
                        if flags & 2**1:  # Italic
                            font_flags.add("italic")
                        if flags & 2**4:  # Bold
                            font_flags.add("bold")
                    
                    block_text += line_text.strip() + " "
                
                block_text = block_text.strip()
                
                if block_text:
                    # Determine block type
                    block_type = self._classify_block(
                        block_text, 
                        max_font_size, 
                        font_flags
                    )
                    
                    blocks.append({
                        "text": block_text,
                        "type": block_type,
                        "page": page_num,
                        "font_size": max_font_size,
                        "bbox": block.get("bbox", []),
                    })
        
        return blocks
    
    def _classify_block(
        self, 
        text: str, 
        font_size: float, 
        font_flags: set
    ) -> str:
        """Classify a text block as heading, paragraph, list, etc."""
        text_stripped = text.strip()
        
        # Very short text with large font is likely a heading
        if font_size > 14 and len(text_stripped) < 200:
            if font_size > 18:
                return "heading_1"
            elif font_size > 15:
                return "heading_2"
            else:
                return "heading_3"
        
        # Bold short text might be a heading
        if "bold" in font_flags and len(text_stripped) < 100:
            return "heading_3"
        
        # List detection
        list_patterns = [
            r"^[\u2022\u2023\u25E6\u2043\u2219]\s",  # Bullet points
            r"^[a-z]\)\s",                           # a) b) c)
            r"^[ivxIVX]+\.\s",                       # Roman numerals
            r"^\d+\.\s",                             # 1. 2. 3.
            r"^[-•]\s",                              # Dashes and bullets
        ]
        for pattern in list_patterns:
            if re.match(pattern, text_stripped):
                return "list_item"
        
        return "paragraph"
    
    def _create_chunks(self, blocks: List[Dict]) -> List[TextChunk]:
        """
        Create optimally-sized chunks from text blocks.
        
        Strategy:
        1. Keep headings as separate chunks (for context)
        2. Group paragraphs up to chunk_size
        3. Add overlap for context continuity
        """
        if not blocks:
            return []
        
        chunks = []
        current_text = ""
        current_page = blocks[0].get("page", 1)
        chunk_index = 0
        char_offset = 0
        
        for block in blocks:
            text = block["text"]
            block_type = block["type"]
            page = block.get("page", current_page)
            
            # Headings get their own chunk or start a new one
            if block_type.startswith("heading"):
                # Save current chunk if exists
                if current_text.strip() and len(current_text) >= self.min_chunk_size:
                    chunks.append(TextChunk(
                        content=self._clean_text(current_text),
                        chunk_type="paragraph",
                        page_number=current_page,
                        chunk_index=chunk_index,
                        start_char=char_offset - len(current_text),
                        end_char=char_offset,
                    ))
                    chunk_index += 1
                    current_text = ""
                
                # Add heading
                chunks.append(TextChunk(
                    content=self._clean_text(text),
                    chunk_type=block_type,
                    page_number=page,
                    chunk_index=chunk_index,
                    start_char=char_offset,
                    end_char=char_offset + len(text),
                ))
                chunk_index += 1
                char_offset += len(text) + 1
                current_page = page
                continue
            
            # Check if adding this block exceeds chunk size
            potential_text = current_text + " " + text if current_text else text
            
            if len(potential_text) > self.chunk_size:
                # Save current chunk
                if current_text.strip() and len(current_text) >= self.min_chunk_size:
                    chunks.append(TextChunk(
                        content=self._clean_text(current_text),
                        chunk_type="paragraph",
                        page_number=current_page,
                        chunk_index=chunk_index,
                        start_char=char_offset - len(current_text),
                        end_char=char_offset,
                    ))
                    chunk_index += 1
                    
                    # Keep overlap for context
                    if self.chunk_overlap > 0:
                        overlap_text = current_text[-self.chunk_overlap:]
                        current_text = overlap_text + " " + text
                    else:
                        current_text = text
                else:
                    current_text = text
            else:
                current_text = potential_text
            
            char_offset += len(text) + 1
            current_page = page
        
        # Add final chunk
        if current_text.strip() and len(current_text) >= self.min_chunk_size:
            chunks.append(TextChunk(
                content=self._clean_text(current_text),
                chunk_type="paragraph",
                page_number=current_page,
                chunk_index=chunk_index,
                start_char=char_offset - len(current_text),
                end_char=char_offset,
            ))
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that break things
        text = text.replace('\x00', '')
        
        # Fix common OCR/extraction issues
        text = re.sub(r'(?<=[a-z])-\s+(?=[a-z])', '', text)  # Fix hyphenation
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text.strip()


# Convenience function
def extract_pdf_text(
    file_path: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> ExtractionResult:
    """
    Convenience function to extract text from a PDF.
    
    Args:
        file_path: Path to PDF file
        chunk_size: Target size for text chunks
        chunk_overlap: Overlap between chunks for context
        
    Returns:
        ExtractionResult with chunks ready for RAG
    """
    extractor = PDFExtractor(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return extractor.extract_from_file(file_path)
