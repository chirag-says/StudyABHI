"""
Syllabus-Aware Text Chunking Algorithm
Chunks text by semantic meaning while preserving context and attaching syllabus tags.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ChunkType(str, Enum):
    """Types of text chunks"""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    DEFINITION = "definition"
    EXAMPLE = "example"
    SUMMARY = "summary"
    QUESTION = "question"


@dataclass
class SyllabusTag:
    """Syllabus tag attached to a chunk"""
    topic_id: str
    topic_name: str
    subject: Optional[str] = None
    paper: Optional[str] = None
    importance: str = "medium"  # low, medium, high, critical
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "subject": self.subject,
            "paper": self.paper,
            "importance": self.importance,
        }


@dataclass
class SemanticChunk:
    """A semantically meaningful text chunk"""
    id: str
    content: str
    chunk_type: ChunkType
    
    # Position
    chunk_index: int
    source_document_id: Optional[str] = None
    page_number: Optional[int] = None
    
    # Tokens
    token_count: int = 0
    
    # Context preservation
    context_before: str = ""  # Summary of preceding content
    context_after: str = ""   # Preview of following content
    
    # Syllabus tags
    syllabus_tags: List[SyllabusTag] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "chunk_type": self.chunk_type.value,
            "chunk_index": self.chunk_index,
            "source_document_id": self.source_document_id,
            "page_number": self.page_number,
            "token_count": self.token_count,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "syllabus_tags": [tag.to_dict() for tag in self.syllabus_tags],
            "metadata": self.metadata,
        }


class SyllabusAwareChunker:
    """
    Advanced text chunker that:
    1. Chunks by semantic meaning (not just character count)
    2. Preserves context between chunks
    3. Attaches relevant syllabus tags
    4. Respects configurable token limits
    """
    
    def __init__(
        self,
        max_tokens: int = 512,
        min_tokens: int = 50,
        overlap_tokens: int = 50,
        context_window: int = 100,  # chars for context
    ):
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens
        self.context_window = context_window
        
        # Semantic boundary patterns
        self.heading_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headings
            r'^([A-Z][A-Z\s]+)$',  # ALL CAPS headings
            r'^\d+\.\s+([A-Z].+)$',  # Numbered headings
            r'^(?:Chapter|Section|Unit|Part)\s+\d+',  # Explicit sections
        ]
        
        self.list_patterns = [
            r'^[\u2022\u2023\u25E6\u2043\u2219•]\s',  # Bullets
            r'^[-*]\s',  # Dashes
            r'^\d+[.)]\s',  # Numbered
            r'^[a-z][.)]\s',  # Lettered
            r'^[ivxIVX]+[.)]\s',  # Roman numerals
        ]
        
        self.definition_patterns = [
            r'^(.+?):\s*(.+)$',  # Term: Definition
            r'^(.+?)\s*[-–]\s*(.+)$',  # Term - Definition
            r'(?:means|refers to|is defined as|is called)',
        ]
    
    def chunk_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        syllabus_tags: Optional[List[SyllabusTag]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SemanticChunk]:
        """
        Chunk text into semantic units with syllabus awareness.
        
        Args:
            text: Raw text to chunk
            document_id: Source document ID
            syllabus_tags: Tags to attach to all chunks
            metadata: Additional metadata
            
        Returns:
            List of SemanticChunk objects
        """
        if not text or not text.strip():
            return []
        
        syllabus_tags = syllabus_tags or []
        metadata = metadata or {}
        
        # Step 1: Split into semantic blocks
        blocks = self._split_into_blocks(text)
        
        # Step 2: Merge small blocks, split large ones
        normalized_blocks = self._normalize_block_sizes(blocks)
        
        # Step 3: Create chunks with context
        chunks = self._create_chunks_with_context(
            normalized_blocks, 
            document_id, 
            syllabus_tags,
            metadata
        )
        
        return chunks
    
    def chunk_with_topics(
        self,
        text: str,
        topic_keywords: Dict[str, SyllabusTag],  # keyword -> tag
        document_id: Optional[str] = None,
    ) -> List[SemanticChunk]:
        """
        Chunk text and auto-tag based on topic keywords.
        
        Args:
            text: Text to chunk
            topic_keywords: Mapping of keywords to syllabus tags
            document_id: Source document ID
            
        Returns:
            Chunks with auto-detected syllabus tags
        """
        chunks = self.chunk_text(text, document_id)
        
        for chunk in chunks:
            # Find matching topics based on keywords
            chunk_lower = chunk.content.lower()
            matched_tags = []
            
            for keyword, tag in topic_keywords.items():
                if keyword.lower() in chunk_lower:
                    if tag not in matched_tags:
                        matched_tags.append(tag)
            
            chunk.syllabus_tags.extend(matched_tags)
        
        return chunks
    
    def _split_into_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Split text into semantic blocks"""
        blocks = []
        
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Classify block type
            block_type = self._classify_block(para)
            
            blocks.append({
                "content": para,
                "type": block_type,
                "tokens": self._estimate_tokens(para),
            })
        
        return blocks
    
    def _classify_block(self, text: str) -> ChunkType:
        """Classify a text block by its type"""
        text_stripped = text.strip()
        first_line = text_stripped.split('\n')[0]
        
        # Check for headings
        for pattern in self.heading_patterns:
            if re.match(pattern, first_line, re.MULTILINE):
                return ChunkType.HEADING
        
        # Check for lists
        lines = text_stripped.split('\n')
        list_line_count = sum(
            1 for line in lines 
            if any(re.match(p, line.strip()) for p in self.list_patterns)
        )
        if list_line_count > len(lines) * 0.5:
            return ChunkType.LIST
        
        # Check for definitions
        for pattern in self.definition_patterns:
            if re.search(pattern, text_stripped, re.IGNORECASE):
                return ChunkType.DEFINITION
        
        # Check for examples
        if any(marker in text_stripped.lower() for marker in 
               ['for example', 'e.g.', 'such as', 'instance', 'consider']):
            return ChunkType.EXAMPLE
        
        # Check for questions
        if text_stripped.endswith('?') or text_stripped.lower().startswith(
            ('what', 'why', 'how', 'when', 'where', 'who', 'which')
        ):
            return ChunkType.QUESTION
        
        return ChunkType.PARAGRAPH
    
    def _normalize_block_sizes(
        self, 
        blocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge small blocks and split large ones"""
        normalized = []
        buffer = {"content": "", "type": ChunkType.PARAGRAPH, "tokens": 0}
        
        for block in blocks:
            # If block is too large, split it
            if block["tokens"] > self.max_tokens:
                # Flush buffer first
                if buffer["content"]:
                    normalized.append(buffer)
                    buffer = {"content": "", "type": ChunkType.PARAGRAPH, "tokens": 0}
                
                # Split large block
                split_blocks = self._split_large_block(block)
                normalized.extend(split_blocks)
                continue
            
            # If adding this block exceeds max, flush buffer
            if buffer["tokens"] + block["tokens"] > self.max_tokens:
                if buffer["content"]:
                    normalized.append(buffer)
                buffer = block.copy()
            else:
                # Merge into buffer
                if buffer["content"]:
                    buffer["content"] += "\n\n" + block["content"]
                    buffer["tokens"] += block["tokens"]
                    # Keep the more specific type
                    if block["type"] != ChunkType.PARAGRAPH:
                        buffer["type"] = block["type"]
                else:
                    buffer = block.copy()
        
        # Don't forget the last buffer
        if buffer["content"]:
            normalized.append(buffer)
        
        return normalized
    
    def _split_large_block(self, block: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split a large block into smaller chunks"""
        content = block["content"]
        block_type = block["type"]
        
        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "type": block_type,
                        "tokens": current_tokens,
                    })
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                current_chunk += " " + sentence
                current_tokens += sentence_tokens
        
        if current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "type": block_type,
                "tokens": current_tokens,
            })
        
        return chunks
    
    def _create_chunks_with_context(
        self,
        blocks: List[Dict[str, Any]],
        document_id: Optional[str],
        syllabus_tags: List[SyllabusTag],
        metadata: Dict[str, Any],
    ) -> List[SemanticChunk]:
        """Create final chunks with context preservation"""
        import uuid
        
        chunks = []
        
        for i, block in enumerate(blocks):
            # Get context from surrounding blocks
            context_before = ""
            context_after = ""
            
            if i > 0:
                prev_content = blocks[i - 1]["content"]
                context_before = prev_content[-self.context_window:].strip()
                if len(prev_content) > self.context_window:
                    context_before = "..." + context_before
            
            if i < len(blocks) - 1:
                next_content = blocks[i + 1]["content"]
                context_after = next_content[:self.context_window].strip()
                if len(next_content) > self.context_window:
                    context_after = context_after + "..."
            
            chunk = SemanticChunk(
                id=str(uuid.uuid4()),
                content=block["content"],
                chunk_type=block["type"],
                chunk_index=i,
                source_document_id=document_id,
                token_count=block["tokens"],
                context_before=context_before,
                context_after=context_after,
                syllabus_tags=syllabus_tags.copy(),
                metadata=metadata.copy(),
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: 1 token ≈ 4 chars for English)"""
        return len(text) // 4


# Convenience function
def chunk_study_material(
    text: str,
    max_tokens: int = 512,
    syllabus_tags: Optional[List[SyllabusTag]] = None,
    document_id: Optional[str] = None,
) -> List[SemanticChunk]:
    """
    Convenience function to chunk study material.
    
    Args:
        text: Study material text
        max_tokens: Maximum tokens per chunk
        syllabus_tags: Tags to attach
        document_id: Source document ID
        
    Returns:
        List of semantic chunks
    """
    chunker = SyllabusAwareChunker(max_tokens=max_tokens)
    return chunker.chunk_text(text, document_id, syllabus_tags)
