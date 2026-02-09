"""
Document Summarization Service
Summarize long documents with UPSC-focused content extraction.
"""
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class SummaryFormat(str, Enum):
    """Format of the summary output"""
    BULLET = "bullet"          # Bullet point list
    PARAGRAPH = "paragraph"    # Flowing paragraph
    STRUCTURED = "structured"  # Headings with bullets
    NOTES = "notes"           # Study notes format
    FLASHCARD = "flashcard"   # Q&A flashcard format


class SummaryLength(str, Enum):
    """Target length of summary"""
    SHORT = "short"       # ~100-200 words
    MEDIUM = "medium"     # ~300-500 words
    LONG = "long"         # ~700-1000 words
    COMPREHENSIVE = "comprehensive"  # ~1500+ words


class SummaryLanguage(str, Enum):
    """Output language"""
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hinglish"


@dataclass
class DocumentSummary:
    """Result of document summarization"""
    summary: str
    format: str
    language: str
    word_count: int
    key_topics: List[str]
    key_terms: List[Dict[str, str]]  # Term definitions
    exam_relevance: str
    important_dates: List[str]
    important_names: List[str]
    source_chunks: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "format": self.format,
            "language": self.language,
            "word_count": self.word_count,
            "key_topics": self.key_topics,
            "key_terms": self.key_terms,
            "exam_relevance": self.exam_relevance,
            "important_dates": self.important_dates,
            "important_names": self.important_names,
            "source_chunks": self.source_chunks,
        }


@dataclass
class ChunkSummary:
    """Summary of a single chunk"""
    content: str
    key_points: List[str]
    chunk_index: int


# ==================== Prompt Templates ====================

SUMMARIZE_SYSTEM_PROMPT = """You are an expert UPSC content summarizer. Your summaries are:
- Accurate and faithful to the source
- Focused on exam-relevant information
- Well-structured and easy to revise
- Highlight important facts, dates, and names
- Include conceptual clarity"""


SUMMARY_PROMPTS = {
    SummaryFormat.BULLET: """Summarize the following content as bullet points.

Content:
{content}

Instructions:
- Create clear, concise bullet points
- Group related points together
- Highlight key facts and figures
- Include important dates and names
- Focus on exam-relevant information

Bullet Point Summary:""",

    SummaryFormat.PARAGRAPH: """Write a flowing paragraph summary of the following content.

Content:
{content}

Instructions:
- Write in clear, coherent paragraphs
- Maintain logical flow of ideas
- Include all key information
- Be concise but comprehensive
- Suitable for revision reading

Paragraph Summary:""",

    SummaryFormat.STRUCTURED: """Create a structured summary with headings and subpoints.

Content:
{content}

Instructions:
- Use clear headings for major topics
- Add bullet points under each heading
- Include key facts and figures
- Highlight exam-important points
- Make it easy to scan and revise

Structured Summary:""",

    SummaryFormat.NOTES: """Create study notes from the following content.

Content:
{content}

Instructions:
- Format as revision-friendly notes
- Include key definitions
- Add memory hooks and mnemonics if helpful
- Highlight must-remember points
- Structure for quick review

Study Notes:""",

    SummaryFormat.FLASHCARD: """Convert the following content into Q&A flashcard format.

Content:
{content}

Instructions:
- Create question-answer pairs
- Focus on key facts and concepts
- Make questions specific and clear
- Keep answers concise
- Cover all important points

Flashcards (Q: ... A: ...):""",
}


LANGUAGE_SUFFIX = {
    SummaryLanguage.ENGLISH: "",
    SummaryLanguage.HINDI: "\n\nWrite your entire response in Hindi (Devanagari script).",
    SummaryLanguage.HINGLISH: "\n\nWrite in Hinglish (Roman Hindi mixed with English technical terms).",
}


LENGTH_INSTRUCTION = {
    SummaryLength.SHORT: "\n\nKeep the summary brief (100-200 words).",
    SummaryLength.MEDIUM: "\n\nKeep the summary moderate (300-500 words).",
    SummaryLength.LONG: "\n\nProvide a detailed summary (700-1000 words).",
    SummaryLength.COMPREHENSIVE: "\n\nProvide a comprehensive summary covering all aspects (1500+ words).",
}


EXTRACT_INFO_PROMPT = """From the following text, extract:
1. Key topics covered
2. Important terms with brief definitions
3. Important dates mentioned
4. Important names/personalities mentioned
5. Exam relevance statement (1-2 sentences)

Text:
{text}

Extraction:"""


class DocumentSummarizer:
    """
    Document Summarization Service for UPSC study materials.
    
    Features:
    - Long document handling via chunking
    - Multiple output formats (bullet, paragraph, structured, notes, flashcard)
    - UPSC-focused content extraction
    - Multilingual output (English, Hindi, Hinglish)
    - Key information extraction (dates, names, terms)
    """
    
    def __init__(
        self,
        llm_client=None,
        max_chunk_tokens: int = 2000,
        default_format: SummaryFormat = SummaryFormat.STRUCTURED,
        default_language: SummaryLanguage = SummaryLanguage.ENGLISH,
    ):
        self.llm_client = llm_client
        self.max_chunk_tokens = max_chunk_tokens
        self.default_format = default_format
        self.default_language = default_language
    
    async def summarize(
        self,
        content: str,
        format: Optional[SummaryFormat] = None,
        length: SummaryLength = SummaryLength.MEDIUM,
        language: Optional[SummaryLanguage] = None,
        extract_info: bool = True,
    ) -> DocumentSummary:
        """
        Summarize a document.
        
        Args:
            content: Document text content
            format: Output format (bullet, paragraph, etc.)
            length: Target summary length
            language: Output language
            extract_info: Whether to extract key info
            
        Returns:
            DocumentSummary with summary and extracted information
        """
        format = format or self.default_format
        language = language or self.default_language
        
        # Handle long documents by chunking
        if self._estimate_tokens(content) > self.max_chunk_tokens:
            summary = await self._summarize_long_document(
                content, format, length, language
            )
        else:
            summary = await self._summarize_chunk(
                content, format, length, language
            )
        
        # Extract key information
        key_topics = []
        key_terms = []
        important_dates = []
        important_names = []
        exam_relevance = ""
        
        if extract_info:
            info = await self._extract_key_info(content[:5000])  # First part
            key_topics = info.get("topics", [])
            key_terms = info.get("terms", [])
            important_dates = info.get("dates", [])
            important_names = info.get("names", [])
            exam_relevance = info.get("exam_relevance", "")
        
        return DocumentSummary(
            summary=summary,
            format=format.value,
            language=language.value,
            word_count=len(summary.split()),
            key_topics=key_topics,
            key_terms=key_terms,
            exam_relevance=exam_relevance,
            important_dates=important_dates,
            important_names=important_names,
            source_chunks=self._count_chunks(content),
        )
    
    async def summarize_for_revision(
        self,
        content: str,
        topic: str,
        language: SummaryLanguage = SummaryLanguage.ENGLISH,
    ) -> Dict[str, Any]:
        """
        Create a revision-ready summary with multiple formats.
        
        Returns both quick revision points and detailed notes.
        """
        # Quick bullet points
        quick_summary = await self.summarize(
            content=content,
            format=SummaryFormat.BULLET,
            length=SummaryLength.SHORT,
            language=language,
            extract_info=False,
        )
        
        # Detailed notes
        detailed_notes = await self.summarize(
            content=content,
            format=SummaryFormat.NOTES,
            length=SummaryLength.LONG,
            language=language,
            extract_info=True,
        )
        
        # Flashcards for testing
        flashcards = await self.summarize(
            content=content,
            format=SummaryFormat.FLASHCARD,
            length=SummaryLength.MEDIUM,
            language=language,
            extract_info=False,
        )
        
        return {
            "topic": topic,
            "quick_revision": quick_summary.summary,
            "detailed_notes": detailed_notes.summary,
            "flashcards": flashcards.summary,
            "key_topics": detailed_notes.key_topics,
            "key_terms": detailed_notes.key_terms,
            "important_dates": detailed_notes.important_dates,
            "important_names": detailed_notes.important_names,
            "exam_relevance": detailed_notes.exam_relevance,
        }
    
    async def _summarize_long_document(
        self,
        content: str,
        format: SummaryFormat,
        length: SummaryLength,
        language: SummaryLanguage,
    ) -> str:
        """Summarize a long document using hierarchical summarization"""
        # Split into chunks
        chunks = self._split_into_chunks(content)
        
        # Summarize each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            summary = await self._summarize_chunk(
                chunk, 
                SummaryFormat.BULLET,  # Use bullets for intermediate
                SummaryLength.SHORT,
                SummaryLanguage.ENGLISH,  # English for intermediate
            )
            chunk_summaries.append(ChunkSummary(
                content=summary,
                key_points=self._extract_bullet_points(summary),
                chunk_index=i,
            ))
        
        # Combine chunk summaries
        combined = "\n\n".join([cs.content for cs in chunk_summaries])
        
        # Final summary in requested format
        final_summary = await self._summarize_chunk(
            combined,
            format,
            length,
            language,
        )
        
        return final_summary
    
    async def _summarize_chunk(
        self,
        content: str,
        format: SummaryFormat,
        length: SummaryLength,
        language: SummaryLanguage,
    ) -> str:
        """Summarize a single chunk"""
        # Build prompt
        template = SUMMARY_PROMPTS.get(format, SUMMARY_PROMPTS[SummaryFormat.STRUCTURED])
        prompt = template.format(content=content)
        
        # Add length instruction
        prompt += LENGTH_INSTRUCTION.get(length, "")
        
        # Add language instruction
        prompt += LANGUAGE_SUFFIX.get(language, "")
        
        # Generate summary
        return await self._generate(prompt)
    
    async def _extract_key_info(self, content: str) -> Dict[str, Any]:
        """Extract key information from content"""
        prompt = EXTRACT_INFO_PROMPT.format(text=content[:3000])
        
        response = await self._generate(prompt)
        
        # Parse response (simple extraction)
        info = {
            "topics": [],
            "terms": [],
            "dates": [],
            "names": [],
            "exam_relevance": "",
        }
        
        # Extract topics
        topics_match = re.findall(r'(?:topic|subject)[:\s]*([^\n]+)', response, re.I)
        info["topics"] = [t.strip() for t in topics_match[:5]]
        
        # Extract dates
        dates = re.findall(r'\b\d{1,4}(?:\s*[-–]\s*\d{1,4})?\s*(?:AD|BC|CE|BCE)?\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b', response)
        info["dates"] = list(set(dates[:10]))
        
        # Extract names (capitalized words that might be names)
        names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', content)
        info["names"] = list(set(names[:10]))
        
        # Extract exam relevance
        relevance_match = re.search(r'exam[:\s]*relevance[:\s]*([^\n]+)', response, re.I)
        if relevance_match:
            info["exam_relevance"] = relevance_match.group(1).strip()
        
        return info
    
    def _split_into_chunks(self, content: str) -> List[str]:
        """Split content into manageable chunks"""
        chunks = []
        paragraphs = content.split('\n\n')
        
        current_chunk = ""
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)
            
            if current_tokens + para_tokens > self.max_chunk_tokens:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
                current_tokens = para_tokens
            else:
                current_chunk += "\n\n" + para
                current_tokens += para_tokens
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points from text"""
        bullets = re.findall(r'[•\-\*]\s*([^\n]+)', text)
        numbered = re.findall(r'\d+\.\s*([^\n]+)', text)
        return bullets + numbered
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        return len(text) // 4
    
    def _count_chunks(self, content: str) -> int:
        """Count number of chunks in content"""
        tokens = self._estimate_tokens(content)
        return max(1, tokens // self.max_chunk_tokens + 1)
    
    async def _generate(self, prompt: str) -> str:
        """Generate using LLM"""
        if self.llm_client:
            return await self.llm_client.generate(
                prompt=prompt,
                system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            )
        else:
            # Mock response
            word_count = len(prompt.split()) // 4
            format_type = "structured" if "heading" in prompt.lower() else "bullet"
            return f"""[Mock Summary - {format_type} format]

**Key Points:**
• This is a placeholder summary for testing
• The actual summary would be generated by an LLM
• Content would be properly summarized based on format

**Important Information:**
• Mock dates: 1947, 1950
• Mock names: Example Person
• Exam relevance: This topic is important for UPSC preparation

Word count: ~{word_count}"""


# Factory function
async def create_summarizer(
    llm_provider: str = "ollama",
    llm_model: str = "llama2",
) -> DocumentSummarizer:
    """Create and initialize Document Summarizer"""
    from app.services.rag.pipeline import OllamaClient, HuggingFaceClient, MockLLMClient
    
    if llm_provider == "ollama":
        llm_client = OllamaClient(model=llm_model)
    elif llm_provider == "huggingface":
        llm_client = HuggingFaceClient(model=llm_model)
    else:
        llm_client = MockLLMClient()
    
    return DocumentSummarizer(llm_client=llm_client)
