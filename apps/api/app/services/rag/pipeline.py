"""
Retrieval-Augmented Generation (RAG) Pipeline
Combines retrieval with LLM generation for grounded answers with citations.
"""
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
import logging
import json
import re

from app.services.rag.embeddings import EmbeddingPipeline, SearchResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"      # Local Ollama
    OPENAI = "openai"      # OpenAI API
    HUGGINGFACE = "huggingface"  # HuggingFace Inference


@dataclass
class Citation:
    """A citation to source material"""
    chunk_id: str
    source: str
    content_snippet: str
    relevance_score: float
    page_number: Optional[int] = None


@dataclass
class RAGResponse:
    """Response from RAG pipeline"""
    answer: str
    citations: List[Citation]
    query: str
    context_chunks: int
    model: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": [
                {
                    "chunk_id": c.chunk_id,
                    "source": c.source,
                    "snippet": c.content_snippet[:200] + "..." if len(c.content_snippet) > 200 else c.content_snippet,
                    "relevance_score": c.relevance_score,
                    "page_number": c.page_number,
                }
                for c in self.citations
            ],
            "query": self.query,
            "context_chunks": self.context_chunks,
            "model": self.model,
            "confidence": self.confidence,
        }


# ==================== Prompt Templates ====================

SYSTEM_PROMPT = """You are an expert UPSC exam tutor and study assistant. Your role is to provide accurate, comprehensive answers to questions based on the provided study materials.

Guidelines:
1. Base your answers ONLY on the provided context
2. If the context doesn't contain enough information, say so clearly
3. Use clear, structured explanations suitable for exam preparation
4. Include relevant examples and mnemonics when helpful
5. Cite sources using [1], [2], etc. format
6. For factual questions, be precise and accurate
7. For analytical questions, provide balanced perspectives

Remember: Accuracy is more important than completeness. Never fabricate information."""


RAG_PROMPT_TEMPLATE = """Based on the following study materials, answer the question comprehensively.

## Context Sources:
{context}

## Question:
{question}

## Instructions:
- Answer based ONLY on the provided context
- Use citations [1], [2] etc. to reference sources
- If information is insufficient, clearly state what's missing
- Structure your answer with clear points
- For UPSC-style questions, include multiple perspectives if relevant

## Answer:"""


CONVERSATIONAL_PROMPT_TEMPLATE = """You are having a study session with a UPSC aspirant. Continue the conversation based on the context provided.

## Previous Messages:
{history}

## Relevant Study Materials:
{context}

## Student's Question:
{question}

## Your Response (as a helpful tutor):"""


ANALYTICAL_PROMPT_TEMPLATE = """Analyze the following topic for UPSC exam preparation.

## Study Materials:
{context}

## Topic to Analyze:
{question}

## Required Analysis:
1. Key concepts and definitions
2. Historical background (if applicable)
3. Multiple perspectives/dimensions
4. Current relevance and examples
5. Potential exam questions on this topic
6. Important points to remember

Cite sources using [1], [2] format.

## Analysis:"""


# ==================== LLM Clients ====================

class BaseLLMClient:
    """Base class for LLM clients"""
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = SYSTEM_PROMPT,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        raise NotImplementedError


class OllamaClient(BaseLLMClient):
    """Client for local Ollama LLM"""
    
    def __init__(
        self,
        model: str = "llama2",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model or settings.LLM_MODEL
        self.base_url = base_url or settings.OLLAMA_BASE_URL
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = SYSTEM_PROMPT,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "system": system_prompt,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "")
                else:
                    logger.error(f"Ollama error: {response.status_code}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise


class HuggingFaceClient(BaseLLMClient):
    """Client for HuggingFace Inference API"""
    
    def __init__(
        self,
        model: str = "mistralai/Mistral-7B-Instruct-v0.2",
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = "https://api-inference.huggingface.co/models"
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = SYSTEM_PROMPT,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        try:
            import httpx
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/{self.model}",
                    headers=headers,
                    json={
                        "inputs": full_prompt,
                        "parameters": {
                            "max_new_tokens": max_tokens,
                            "temperature": temperature,
                            "return_full_text": False,
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0].get("generated_text", "")
                    return ""
                else:
                    logger.error(f"HuggingFace error: {response.status_code}")
                    return ""
                    
        except Exception as e:
            logger.error(f"HuggingFace generation failed: {e}")
            raise


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing"""
    
    def __init__(self, model: str = "mock"):
        self.model = model
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = SYSTEM_PROMPT,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        # Extract question from prompt
        question_match = re.search(r'Question:\s*(.+?)(?:\n|$)', prompt, re.DOTALL)
        question = question_match.group(1).strip() if question_match else "the topic"
        
        return f"""Based on the provided study materials, here is a comprehensive answer to your question about {question}:

**Key Points:**
1. The context provides relevant information on this topic [1]
2. Multiple perspectives have been considered [2]
3. This is particularly important for UPSC preparation

**Analysis:**
The study materials indicate several important aspects that candidates should understand. The historical context [1] provides a foundation, while contemporary developments [2] show current relevance.

**Conclusion:**
Understanding these concepts is crucial for comprehensive exam preparation. Focus on the interconnections between different aspects mentioned in the sources.

*Note: This is a mock response for testing. Connect to a real LLM for actual answers.*"""


# ==================== RAG Pipeline ====================

class RAGPipeline:
    """
    Complete RAG Pipeline for Study Materials.
    
    Steps:
    1. Accept user query
    2. Retrieve top-k relevant chunks from vector store
    3. Construct grounded prompt with context
    4. Generate answer with citations using LLM
    """
    
    def __init__(
        self,
        embedding_pipeline: EmbeddingPipeline,
        llm_client: Optional[BaseLLMClient] = None,
        top_k: int = 5,
        min_relevance_score: float = 0.05,
    ):
        self.embedding_pipeline = embedding_pipeline
        self.llm_client = llm_client or MockLLMClient()
        self.top_k = top_k
        self.min_relevance_score = min_relevance_score
    
    async def query(
        self,
        question: str,
        user_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        syllabus_tags: Optional[List[str]] = None,
        prompt_template: str = RAG_PROMPT_TEMPLATE,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> RAGResponse:
        """
        Execute RAG query.
        
        Args:
            question: User's question
            user_id: Filter by user's documents
            document_ids: Filter by specific document IDs
            syllabus_tags: Filter by syllabus topics
            prompt_template: Template for prompt construction
            max_tokens: Max tokens for generation
            temperature: LLM temperature
            
        Returns:
            RAGResponse with answer and citations
        """
        # Step 1: Retrieve relevant chunks
        search_results = await self.embedding_pipeline.search(
            query=question,
            top_k=self.top_k * 2,  # Fetch more candidate chunks
            user_id=user_id,
            document_ids=document_ids,
            syllabus_tags=syllabus_tags,
        )
        
        # Filter by minimum relevance
        print(f"DEBUG: Search Query: {question}")
        print(f"DEBUG: Raw Results Count: {len(search_results)}")
        for i, res in enumerate(search_results):
            print(f"DEBUG: Result {i}: Score={res.score}, Source={res.metadata.source}")

        relevant_results = [
            r for r in search_results 
            if r.score >= self.min_relevance_score
        ]
        print(f"DEBUG: Relevant Results after filter ({self.min_relevance_score}): {len(relevant_results)}")
        
        if not relevant_results:
            return RAGResponse(
                answer="I couldn't find relevant information in the study materials to answer this question. Please try rephrasing or ensure relevant content has been uploaded.",
                citations=[],
                query=question,
                context_chunks=0,
                model=getattr(self.llm_client, 'model', 'unknown'),
                confidence=0.0,
            )
        
        # Step 2: Construct context with citations
        context = self._build_context(relevant_results)
        
        # Step 3: Build prompt
        prompt = prompt_template.format(
            context=context,
            question=question,
        )
        
        # Step 4: Generate answer
        answer = await self.llm_client.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        # Step 5: Create citations
        citations = [
            Citation(
                chunk_id=r.chunk_id,
                source=r.metadata.source or f"Document {r.metadata.document_id[:8]}..." if r.metadata.document_id else "Unknown",
                content_snippet=r.content[:300],
                relevance_score=r.score,
                page_number=r.metadata.extra.get("page_number"),
            )
            for r in relevant_results
        ]
        
        # Calculate confidence based on retrieval scores
        avg_score = sum(r.score for r in relevant_results) / len(relevant_results)
        
        return RAGResponse(
            answer=answer,
            citations=citations,
            query=question,
            context_chunks=len(relevant_results),
            model=getattr(self.llm_client, 'model', 'unknown'),
            confidence=min(avg_score, 1.0),
        )
    
    async def analytical_query(
        self,
        topic: str,
        user_id: Optional[str] = None,
        syllabus_tags: Optional[List[str]] = None,
    ) -> RAGResponse:
        """Generate analytical response for UPSC-style questions"""
        return await self.query(
            question=topic,
            user_id=user_id,
            syllabus_tags=syllabus_tags,
            prompt_template=ANALYTICAL_PROMPT_TEMPLATE,
            max_tokens=2048,
            temperature=0.5,
        )
    
    async def conversational_query(
        self,
        question: str,
        history: List[Dict[str, str]],  # [{"role": "user/assistant", "content": "..."}]
        user_id: Optional[str] = None,
    ) -> RAGResponse:
        """Conversational RAG for multi-turn interactions"""
        # Format history
        history_text = "\n".join([
            f"{'Student' if m['role'] == 'user' else 'Tutor'}: {m['content']}"
            for m in history[-6:]  # Last 6 messages
        ])
        
        # Retrieve based on question + recent context
        search_query = question
        if history:
            search_query = f"{history[-1].get('content', '')} {question}"
        
        search_results = await self.embedding_pipeline.search(
            query=search_query,
            top_k=self.top_k,
            user_id=user_id,
        )
        
        relevant_results = [r for r in search_results if r.score >= self.min_relevance_score]
        context = self._build_context(relevant_results) if relevant_results else "No specific study materials found."
        
        prompt = CONVERSATIONAL_PROMPT_TEMPLATE.format(
            history=history_text,
            context=context,
            question=question,
        )
        
        answer = await self.llm_client.generate(prompt=prompt)
        
        citations = [
            Citation(
                chunk_id=r.chunk_id,
                source=r.metadata.source or "Study Material",
                content_snippet=r.content[:200],
                relevance_score=r.score,
            )
            for r in relevant_results[:3]  # Top 3 for conversation
        ]
        
        return RAGResponse(
            answer=answer,
            citations=citations,
            query=question,
            context_chunks=len(relevant_results),
            model=getattr(self.llm_client, 'model', 'unknown'),
        )
    
    def _build_context(self, results: List[SearchResult]) -> str:
        """Build context string with source numbers"""
        context_parts = []
        
        for i, result in enumerate(results, 1):
            source_info = result.metadata.source or f"Document {result.metadata.document_id[:8] if result.metadata.document_id else 'Unknown'}"
            
            context_parts.append(
                f"[{i}] Source: {source_info}\n"
                f"Content: {result.content}\n"
            )
        
        return "\n---\n".join(context_parts)


# ==================== Factory Functions ====================

def create_rag_pipeline(
    embedding_pipeline: EmbeddingPipeline,
    llm_provider: LLMProvider = LLMProvider(settings.LLM_PROVIDER),
    model: str = settings.LLM_MODEL,
    api_key: Optional[str] = None,
    **kwargs,
) -> RAGPipeline:
    """
    Create a RAG pipeline with specified LLM provider.
    
    Args:
        embedding_pipeline: Initialized embedding pipeline
        llm_provider: LLM provider to use
        model: Model name
        api_key: API key (if required)
        **kwargs: Additional arguments for RAG pipeline
        
    Returns:
        Configured RAGPipeline instance
    """
    if llm_provider == LLMProvider.OLLAMA:
        llm_client = OllamaClient(model=model)
    elif llm_provider == LLMProvider.HUGGINGFACE:
        llm_client = HuggingFaceClient(model=model, api_key=api_key)
    else:
        llm_client = MockLLMClient(model=model)
    
    return RAGPipeline(
        embedding_pipeline=embedding_pipeline,
        llm_client=llm_client,
        **kwargs,
    )


async def create_complete_rag_system(
    storage_path: str = "data/vectors",
    embedding_model: str = "all-MiniLM-L6-v2",
    llm_provider: LLMProvider = LLMProvider(settings.LLM_PROVIDER),
    llm_model: str = settings.LLM_MODEL,
) -> RAGPipeline:
    """
    Create a complete RAG system with all components.
    
    Args:
        storage_path: Path for vector storage
        embedding_model: Sentence transformer model
        llm_provider: LLM provider
        llm_model: LLM model name
        
    Returns:
        Ready-to-use RAGPipeline
    """
    from app.services.rag.embeddings import EmbeddingPipeline
    
    # Create embedding pipeline
    embedding_pipeline = EmbeddingPipeline(
        model_name=embedding_model,
        storage_path=storage_path,
    )
    
    # Create RAG pipeline
    rag_pipeline = create_rag_pipeline(
        embedding_pipeline=embedding_pipeline,
        llm_provider=llm_provider,
        model=llm_model,
    )
    
    return rag_pipeline
