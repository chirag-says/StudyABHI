"""
PDF Extraction Service
Extract clean, structured text from PDFs for RAG ingestion.

Uses PyMuPDF (fitz) for robust PDF parsing.
For image-based (scanned) PDFs, falls back to NVIDIA vision model OCR.
"""
import re
import base64
import asyncio
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


# ---------------------------------------------------------------------------
# Vision OCR helper — sends a page image to NVIDIA vision model
# ---------------------------------------------------------------------------

async def _ocr_page_via_nvidia(page_png_bytes: bytes, page_num: int) -> str:
    """
    Send a page image to NVIDIA llama-3.2-11b-vision-instruct for OCR.
    Returns the extracted text, or empty string on failure.
    """
    try:
        import httpx
        from app.core.config import settings

        api_key = settings.NVIDIA_API_KEY
        if not api_key:
            return ""

        b64 = base64.b64encode(page_png_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        payload = {
            "model": "meta/llama-3.2-11b-vision-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {
                            "type": "text",
                            "text": (
                                "You are an OCR engine. Extract ALL text from this page image exactly as it appears. "
                                "Preserve headings, paragraphs, lists, and tables. "
                                "Output ONLY the extracted text — no commentary, no markdown code fences."
                            ),
                        },
                    ],
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.0,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.NVIDIA_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                logger.info(f"OCR page {page_num}: extracted {len(text)} chars via vision model")
                return text
            else:
                logger.warning(f"OCR page {page_num} failed: {resp.status_code} {resp.text[:200]}")
                return ""
    except Exception as e:
        logger.warning(f"OCR page {page_num} exception: {e}")
        return ""


def _is_image_page(text: str) -> bool:
    """Return True if the extracted text is too short / garbled to be useful."""
    # Strip whitespace and control characters
    clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text).strip()
    # Less than 50 printable chars → treat as image page
    printable = sum(1 for c in clean if c.isprintable() and not c.isspace())
    return printable < 50


class PDFExtractor:
    """
    Extract structured text from PDF files.
    
    Features:
    - Heading detection based on font size
    - Paragraph grouping
    - Configurable chunk size for RAG
    - Metadata extraction
    - Auto OCR for image-based (scanned) PDFs via NVIDIA vision model
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,      # Target chars per chunk
        chunk_overlap: int = 200,     # Overlap between chunks
        min_chunk_size: int = 100,    # Minimum chunk size
        detect_headings: bool = True,
        enable_ocr: bool = True,      # OCR fallback for image pages
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.detect_headings = detect_headings
        self.enable_ocr = enable_ocr
    
    def extract_from_file(self, file_path: str) -> ExtractionResult:
        """
        Extract text from a PDF file.
        Runs the async extraction in an executor so it can be called from sync code.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._extract_async(file_path=file_path))
                    return future.result()
            else:
                return loop.run_until_complete(self._extract_async(file_path=file_path))
        except RuntimeError:
            return asyncio.run(self._extract_async(file_path=file_path))

    def extract_from_bytes(self, pdf_bytes: bytes) -> ExtractionResult:
        """Extract text from PDF bytes (for in-memory processing)"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._extract_async(pdf_bytes=pdf_bytes))
                    return future.result()
            else:
                return loop.run_until_complete(self._extract_async(pdf_bytes=pdf_bytes))
        except RuntimeError:
            return asyncio.run(self._extract_async(pdf_bytes=pdf_bytes))

    async def _extract_async(
        self,
        file_path: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
    ) -> ExtractionResult:
        """Async extraction with OCR fallback for image pages."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install pymupdf")
            return ExtractionResult(chunks=[], page_count=0, word_count=0, metadata={},
                                    errors=["PyMuPDF not installed"])

        errors = []
        all_blocks = []

        try:
            if file_path:
                doc = fitz.open(file_path)
            else:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            metadata = self._extract_metadata(doc)
            page_count = len(doc)

            for page_num in range(page_count):
                try:
                    page = doc[page_num]
                    # Try normal text extraction first
                    raw_text = page.get_text("text")

                    if self.enable_ocr and _is_image_page(raw_text):
                        # Image-based page → OCR via NVIDIA vision model
                        logger.info(f"Page {page_num + 1} appears image-based, running OCR...")
                        # Render at 150 DPI for good OCR quality without huge payloads
                        mat = fitz.Matrix(150 / 72, 150 / 72)
                        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
                        png_bytes = pix.tobytes("png")
                        ocr_text = await _ocr_page_via_nvidia(png_bytes, page_num + 1)

                        if ocr_text.strip():
                            all_blocks.append({
                                "text": ocr_text,
                                "type": "paragraph",
                                "page": page_num + 1,
                                "font_size": 12,
                                "bbox": [],
                            })
                        else:
                            logger.warning(f"OCR returned empty for page {page_num + 1}, skipping.")
                    else:
                        # Normal text PDF
                        blocks = self._extract_page_blocks(page, page_num + 1)
                        all_blocks.extend(blocks)

                except Exception as e:
                    errors.append(f"Error on page {page_num + 1}: {str(e)}")
                    logger.warning(f"Error extracting page {page_num + 1}: {e}")

            doc.close()

            chunks = self._create_chunks(all_blocks)
            word_count = sum(len(chunk.content.split()) for chunk in chunks)

            return ExtractionResult(
                chunks=chunks,
                page_count=page_count,
                word_count=word_count,
                metadata=metadata,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"Failed to extract PDF: {e}")
            return ExtractionResult(chunks=[], page_count=0, word_count=0, metadata={},
                                    errors=[f"Extraction failed: {str(e)}"])

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
        text = text.replace('\u2018', "'").replace('\u2019', "'")
        
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
