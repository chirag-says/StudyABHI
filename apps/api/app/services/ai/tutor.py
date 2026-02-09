"""
AI Tutor Service
Intelligent tutoring using RAG with syllabus awareness,
adjustable verbosity, and multilingual output.
"""
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import logging
import re

from app.core.config import settings

logger = logging.getLogger(__name__)


class VerbosityLevel(str, Enum):
    """Level of detail in responses"""
    BRIEF = "brief"          # Quick answer, 2-3 sentences
    STANDARD = "standard"    # Normal explanation
    DETAILED = "detailed"    # Comprehensive with examples
    EXAM_READY = "exam_ready" # Full UPSC answer format


class OutputLanguage(str, Enum):
    """Supported output languages"""
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hinglish"  # Mixed Hindi-English


class QuestionType(str, Enum):
    """Types of questions for different handling"""
    FACTUAL = "factual"           # Direct facts
    CONCEPTUAL = "conceptual"     # Understanding concepts
    ANALYTICAL = "analytical"     # Analysis and evaluation
    COMPARATIVE = "comparative"   # Compare and contrast
    APPLICATION = "application"   # Apply knowledge
    OPINION = "opinion"          # Perspective-based


@dataclass
class TutorResponse:
    """Response from AI tutor"""
    answer: str
    language: str
    verbosity: str
    question_type: str
    syllabus_topics: List[str]
    citations: List[Dict[str, Any]]
    follow_up_questions: List[str]
    key_points: List[str]
    exam_tips: Optional[str] = None
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "language": self.language,
            "verbosity": self.verbosity,
            "question_type": self.question_type,
            "syllabus_topics": self.syllabus_topics,
            "citations": self.citations,
            "follow_up_questions": self.follow_up_questions,
            "key_points": self.key_points,
            "exam_tips": self.exam_tips,
            "confidence": self.confidence,
        }


# ==================== Prompt Templates ====================

TUTOR_SYSTEM_PROMPT = """You are an expert UPSC tutor with deep knowledge of the Indian Civil Services examination. 
Your role is to help students understand concepts clearly and prepare effectively for exams.

Your teaching style:
- Clear and structured explanations
- Use examples relevant to Indian context
- Connect topics to current affairs when applicable
- Provide memory aids and mnemonics
- Focus on exam-relevant aspects

Always maintain accuracy and cite sources when available."""


TUTOR_PROMPT_TEMPLATES = {
    VerbosityLevel.BRIEF: """Answer the following question briefly in 2-3 sentences.

Context from study materials:
{context}

Question: {question}

Brief Answer:""",

    VerbosityLevel.STANDARD: """Provide a clear explanation for the following question.

Context from study materials:
{context}

Question: {question}

Syllabus Topics: {syllabus_topics}

Instructions:
- Give a well-structured answer
- Include key points
- Cite sources using [1], [2] format
- Keep it concise but complete

Answer:""",

    VerbosityLevel.DETAILED: """Provide a comprehensive explanation with examples.

Context from study materials:
{context}

Question: {question}

Syllabus Topics: {syllabus_topics}

Instructions:
- Give detailed explanation with background
- Include multiple examples
- Explain interconnections
- Add relevant current affairs
- Provide memory tips
- Cite sources using [1], [2] format

Detailed Answer:""",

    VerbosityLevel.EXAM_READY: """Write a complete UPSC answer for this question.

Context from study materials:
{context}

Question: {question}

Syllabus Topics: {syllabus_topics}

Instructions:
- Write in proper answer format (Introduction, Body, Conclusion)
- Include multiple dimensions
- Add examples and case studies
- Connect to current relevance
- Mention constitutional/legal provisions if applicable
- Use proper UPSC answer writing style
- Include diagram description if helpful
- Cite sources using [1], [2] format

UPSC Model Answer:""",
}


LANGUAGE_INSTRUCTION = {
    OutputLanguage.ENGLISH: "",
    OutputLanguage.HINDI: "\n\nIMPORTANT: Write your entire response in Hindi (Devanagari script).",
    OutputLanguage.HINGLISH: "\n\nIMPORTANT: Write your response in Hinglish (Hindi words written in Roman script, mixed with English technical terms).",
}


FOLLOW_UP_PROMPT = """Based on the question "{question}" and the answer provided, suggest 3 related follow-up questions that would help deepen understanding.

Follow-up questions:
1."""


KEY_POINTS_PROMPT = """Extract 3-5 key points from this answer that are most important for exam preparation:

{answer}

Key Points:
1."""


class AITutor:
    """
    AI Tutor Service with RAG integration.
    
    Features:
    - RAG-based answering with syllabus awareness
    - Adjustable verbosity levels
    - Multilingual output (English, Hindi, Hinglish)
    - Question type detection
    - Follow-up question generation
    - Exam tips and key points extraction
    """
    
    def __init__(
        self,
        rag_pipeline=None,
        llm_client=None,
        default_language: OutputLanguage = OutputLanguage.ENGLISH,
        default_verbosity: VerbosityLevel = VerbosityLevel.STANDARD,
    ):
        self.rag_pipeline = rag_pipeline
        self.llm_client = llm_client
        self.default_language = default_language
        self.default_verbosity = default_verbosity
    
    async def ask(
        self,
        question: str,
        syllabus_tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        language: Optional[OutputLanguage] = None,
        verbosity: Optional[VerbosityLevel] = None,
        include_follow_ups: bool = True,
        include_exam_tips: bool = True,
    ) -> TutorResponse:
        """
        Ask the AI tutor a question.
        
        Args:
            question: Student's question
            syllabus_tags: Limit scope to specific syllabus topics
            user_id: For personalized content access
            language: Output language
            verbosity: Detail level of response
            include_follow_ups: Generate follow-up questions
            include_exam_tips: Include exam preparation tips
            
        Returns:
            TutorResponse with comprehensive answer
        """
        language = language or self.default_language
        verbosity = verbosity or self.default_verbosity
        
        # Detect question type
        question_type = self._detect_question_type(question)
        
        # Get relevant context from RAG
        context, citations, matched_topics = await self._retrieve_context(
            question, syllabus_tags, user_id
        )
        
        # Build prompt
        prompt = self._build_prompt(
            question=question,
            context=context,
            syllabus_topics=matched_topics,
            verbosity=verbosity,
            language=language,
        )
        
        # Generate answer
        answer = await self._generate(prompt)
        
        # Extract key points
        key_points = await self._extract_key_points(answer)
        
        # Generate follow-up questions
        follow_ups = []
        if include_follow_ups:
            follow_ups = await self._generate_follow_ups(question)
        
        # Generate exam tips
        exam_tips = None
        if include_exam_tips and verbosity in [VerbosityLevel.DETAILED, VerbosityLevel.EXAM_READY]:
            exam_tips = await self._generate_exam_tips(question, question_type)
        
        # Calculate confidence
        confidence = len(citations) / 5.0 if citations else 0.3
        confidence = min(confidence, 1.0)
        
        return TutorResponse(
            answer=answer,
            language=language.value,
            verbosity=verbosity.value,
            question_type=question_type.value,
            syllabus_topics=matched_topics,
            citations=citations,
            follow_up_questions=follow_ups,
            key_points=key_points,
            exam_tips=exam_tips,
            confidence=confidence,
        )
    
    async def explain_topic(
        self,
        topic: str,
        language: OutputLanguage = OutputLanguage.ENGLISH,
        verbosity: VerbosityLevel = VerbosityLevel.DETAILED,
    ) -> TutorResponse:
        """Explain a syllabus topic in detail"""
        question = f"Explain {topic} in detail for UPSC preparation"
        return await self.ask(
            question=question,
            language=language,
            verbosity=verbosity,
            include_exam_tips=True,
        )
    
    async def practice_question(
        self,
        topic: str,
        question_type: QuestionType = QuestionType.ANALYTICAL,
    ) -> Dict[str, Any]:
        """Generate a practice question on a topic"""
        prompt = f"""Generate a {question_type.value} UPSC-style question on the topic: {topic}

The question should be:
- Suitable for UPSC Mains examination
- Clear and specific
- Testable and answerable

Question:"""
        
        question = await self._generate(prompt)
        
        # Generate model answer
        model_answer = await self.ask(
            question=question,
            verbosity=VerbosityLevel.EXAM_READY,
        )
        
        return {
            "topic": topic,
            "question": question,
            "question_type": question_type.value,
            "model_answer": model_answer.answer,
            "key_points": model_answer.key_points,
        }
    
    def _detect_question_type(self, question: str) -> QuestionType:
        """Detect the type of question asked"""
        question_lower = question.lower()
        
        # Comparative questions
        if any(word in question_lower for word in [
            'compare', 'contrast', 'difference', 'similar', 'versus', 'vs'
        ]):
            return QuestionType.COMPARATIVE
        
        # Analytical questions
        if any(word in question_lower for word in [
            'analyze', 'analyse', 'evaluate', 'assess', 'critically', 'examine'
        ]):
            return QuestionType.ANALYTICAL
        
        # Application questions
        if any(word in question_lower for word in [
            'how can', 'apply', 'implement', 'solve', 'what steps'
        ]):
            return QuestionType.APPLICATION
        
        # Opinion questions
        if any(word in question_lower for word in [
            'do you think', 'your opinion', 'should', 'agree or disagree'
        ]):
            return QuestionType.OPINION
        
        # Conceptual questions
        if any(word in question_lower for word in [
            'explain', 'what is', 'describe', 'elaborate', 'meaning'
        ]):
            return QuestionType.CONCEPTUAL
        
        # Default to factual
        return QuestionType.FACTUAL
    
    async def _retrieve_context(
        self,
        question: str,
        syllabus_tags: Optional[List[str]],
        user_id: Optional[str],
    ) -> Tuple[str, List[Dict], List[str]]:
        """Retrieve relevant context from RAG"""
        if not self.rag_pipeline:
            return "", [], []
        
        try:
            results = await self.rag_pipeline.embedding_pipeline.search(
                query=question,
                top_k=5,
                user_id=user_id,
                syllabus_tags=syllabus_tags,
            )
            
            # Build context
            context_parts = []
            citations = []
            matched_topics = set()
            
            for i, result in enumerate(results, 1):
                context_parts.append(f"[{i}] {result.content}")
                citations.append({
                    "id": result.chunk_id,
                    "source": result.metadata.source,
                    "score": result.score,
                })
                matched_topics.update(result.metadata.syllabus_tags)
            
            return "\n\n".join(context_parts), citations, list(matched_topics)
            
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return "", [], []
    
    def _build_prompt(
        self,
        question: str,
        context: str,
        syllabus_topics: List[str],
        verbosity: VerbosityLevel,
        language: OutputLanguage,
    ) -> str:
        """Build the tutor prompt"""
        template = TUTOR_PROMPT_TEMPLATES.get(
            verbosity, 
            TUTOR_PROMPT_TEMPLATES[VerbosityLevel.STANDARD]
        )
        
        prompt = template.format(
            context=context or "No specific study materials available.",
            question=question,
            syllabus_topics=", ".join(syllabus_topics) if syllabus_topics else "General",
        )
        
        # Add language instruction
        prompt += LANGUAGE_INSTRUCTION.get(language, "")
        
        return prompt
    
    async def _generate(self, prompt: str) -> str:
        """Generate response using LLM"""
        if self.llm_client:
            return await self.llm_client.generate(
                prompt=prompt,
                system_prompt=TUTOR_SYSTEM_PROMPT,
            )
        else:
            # Mock response for testing
            return f"[Mock Tutor Response]\n\nThis is a placeholder response for: {prompt[:100]}...\n\nIn production, this would be generated by an LLM like Ollama or OpenAI."
    
    async def _extract_key_points(self, answer: str) -> List[str]:
        """Extract key points from the answer"""
        # Simple extraction based on patterns
        points = []
        
        # Look for numbered points
        numbered = re.findall(r'\d+\.\s*([^\n]+)', answer)
        points.extend(numbered[:5])
        
        # Look for bullet points
        bullets = re.findall(r'[•\-\*]\s*([^\n]+)', answer)
        points.extend(bullets[:5])
        
        # If no points found, extract first sentences
        if not points:
            sentences = re.split(r'[.!?]\s+', answer)
            points = [s.strip() for s in sentences[:3] if len(s.strip()) > 20]
        
        return points[:5]
    
    async def _generate_follow_ups(self, question: str) -> List[str]:
        """Generate follow-up questions"""
        # Simple rule-based follow-ups
        base_topic = question.replace("?", "").strip()
        
        follow_ups = [
            f"What are the current developments related to {base_topic[:50]}?",
            f"How is {base_topic[:50]} relevant for UPSC exam?",
            f"What are the different perspectives on {base_topic[:50]}?",
        ]
        
        return follow_ups
    
    async def _generate_exam_tips(
        self, 
        question: str, 
        question_type: QuestionType
    ) -> str:
        """Generate exam tips based on question type"""
        tips = {
            QuestionType.FACTUAL: "For factual questions: Be precise, include dates/numbers, and structure your answer with clear headings.",
            QuestionType.CONCEPTUAL: "For conceptual questions: Define the concept clearly, explain its significance, and provide examples.",
            QuestionType.ANALYTICAL: "For analytical questions: Present multiple perspectives, use evidence, and provide a balanced conclusion.",
            QuestionType.COMPARATIVE: "For comparative questions: Use a structured format (table if possible), highlight both similarities and differences.",
            QuestionType.APPLICATION: "For application questions: Show understanding of the concept, provide practical examples, and suggest implementable solutions.",
            QuestionType.OPINION: "For opinion questions: State your position clearly, support with evidence, acknowledge counter-arguments.",
        }
        
        return tips.get(question_type, "Structure your answer with introduction, body, and conclusion.")


# Factory function
async def create_ai_tutor(
    rag_pipeline=None,
    llm_provider: str = settings.LLM_PROVIDER,
    llm_model: str = settings.LLM_MODEL,
) -> AITutor:
    """Create and initialize AI Tutor"""
    from app.services.rag.pipeline import OllamaClient, HuggingFaceClient, MockLLMClient
    
    if llm_provider == "ollama":
        llm_client = OllamaClient(model=llm_model)
    elif llm_provider == "huggingface":
        llm_client = HuggingFaceClient(model=llm_model)
    else:
        llm_client = MockLLMClient()
    
    return AITutor(
        rag_pipeline=rag_pipeline,
        llm_client=llm_client,
    )
