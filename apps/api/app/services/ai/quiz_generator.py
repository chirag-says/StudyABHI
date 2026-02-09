"""
AI Quiz Generator Service
Generate MCQ quizzes from study material chunks.
"""
import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import logging
import ast  # For robust parsing of Python-style dicts

from app.core.config import settings

logger = logging.getLogger(__name__)


class QuestionDifficulty(str, Enum):
    """Question difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


@dataclass
class GeneratedQuestion:
    """A generated MCQ question"""
    question_text: str
    options: List[str]  # 4 options
    correct_option: int  # 0-3 index
    explanation: str
    difficulty: str
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    source_chunk_id: Optional[str] = None
    confidence_score: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_text": self.question_text,
            "options": self.options,
            "correct_option": self.correct_option,
            "explanation": self.explanation,
            "difficulty": self.difficulty,
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "source_chunk_id": self.source_chunk_id,
            "confidence_score": self.confidence_score,
        }


@dataclass
class QuizGenerationResult:
    """Result of quiz generation"""
    questions: List[GeneratedQuestion]
    source_content: str
    difficulty: str
    success: bool
    errors: List[str] = field(default_factory=list)


# ==================== Prompt Templates ====================

QUIZ_SYSTEM_PROMPT = """You are an expert UPSC question paper setter. You create high-quality MCQs that:
- Test factual knowledge and understanding
- Have clear, unambiguous questions
- Include plausible but incorrect distractors
- Follow UPSC exam patterns
- Cover important exam-relevant concepts

Format each question strictly as valid JSON."""


GENERATE_MCQ_PROMPT = """Generate {count} multiple choice questions from the following study material.

**Study Material:**
{content}

**Requirements:**
- Difficulty Level: {difficulty}
- Topic: {topic}
- Each question must have exactly 4 options
- Only one option should be correct
- Distractors should be plausible but clearly wrong
- Include a brief explanation for the correct answer

**Output Format (JSON array):**
```json
[
  {{
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0,
    "explanation": "Brief explanation why option A is correct."
  }}
]
```

**Difficulty Guidelines:**
- easy: Basic recall, direct facts
- medium: Understanding and application
- hard: Analysis and inference
- expert: Critical evaluation, complex reasoning

Generate exactly {count} questions. Output ONLY the raw JSON array. Do not use markdown code blocks. Do not add any introductory text."""


TOPIC_SPECIFIC_PROMPT = """Generate {count} UPSC-style MCQs on the topic: {topic}

**Context from study materials:**
{content}

**Focus areas for {topic}:**
- Key concepts and definitions
- Important dates and events (if applicable)
- Constitutional/legal provisions (if applicable)
- Current developments
- Inter-linkages with other topics

**Requirements:**
- Difficulty: {difficulty}
- Mix of factual and analytical questions
- Include explanation for each

**Output as JSON array:**
```json
[
  {{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct": 0,
    "explanation": "..."
  }}
]
```

Generate exactly {count} questions:"""


PREVIOUS_YEAR_STYLE_PROMPT = """Generate {count} MCQs in UPSC Prelims previous year style.

**Reference Content:**
{content}

**UPSC Prelims Question Characteristics:**
1. Testing conceptual clarity, not just memorization
2. Using "Consider the following statements" format when appropriate
3. Including "Select the correct answer using the code below" options
4. Asking about "With reference to..." topics
5. Requiring inference from given information

**Difficulty:** {difficulty}

**Output as JSON array with standard format.**

Generate {count} questions:"""


class QuizGenerator:
    """
    AI-powered Quiz Generator.
    
    Generates MCQs from study material with:
    - Configurable difficulty
    - Topic-specific questions
    - UPSC exam pattern adherence
    - Syllabus mapping
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def generate_quiz(
        self,
        content: str,
        question_count: int = 10,
        difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM,
        topic_name: Optional[str] = None,
        topic_id: Optional[str] = None,
        style: str = "standard",  # standard, topic_specific, previous_year
    ) -> QuizGenerationResult:
        """
        Generate quiz questions from content.
        
        Args:
            content: Study material text
            question_count: Number of questions to generate
            difficulty: Difficulty level
            topic_name: Topic name for context
            topic_id: Topic ID for syllabus mapping
            style: Question style
            
        Returns:
            QuizGenerationResult with generated questions
        """
        if not content or len(content.strip()) < 100:
            return QuizGenerationResult(
                questions=[],
                source_content=content,
                difficulty=difficulty.value,
                success=False,
                errors=["Content too short for quiz generation"]
            )
        
        # Select prompt template
        if style == "topic_specific" and topic_name:
            prompt_template = TOPIC_SPECIFIC_PROMPT
        elif style == "previous_year":
            prompt_template = PREVIOUS_YEAR_STYLE_PROMPT
        else:
            prompt_template = GENERATE_MCQ_PROMPT
        
        # Build prompt
        prompt = prompt_template.format(
            count=question_count,
            content=content[:8000],  # Limit content length
            difficulty=difficulty.value,
            topic=topic_name or "General",
        )
        
        try:
            # Generate questions
            response = await self._generate(prompt)
            
            # Parse response
            questions = self._parse_questions(
                response, 
                difficulty, 
                topic_id, 
                topic_name
            )
            
            if not questions:
                return QuizGenerationResult(
                    questions=[],
                    source_content=content,
                    difficulty=difficulty.value,
                    success=False,
                    errors=["Failed to parse generated questions"]
                )
            
            return QuizGenerationResult(
                questions=questions,
                source_content=content[:2000],  # Store truncated
                difficulty=difficulty.value,
                success=True,
            )
            
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            return QuizGenerationResult(
                questions=[],
                source_content=content,
                difficulty=difficulty.value,
                success=False,
                errors=[str(e)]
            )
    
    async def generate_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        questions_per_chunk: int = 2,
        difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM,
    ) -> QuizGenerationResult:
        """
        Generate questions from multiple content chunks.
        
        Args:
            chunks: List of chunk dicts with 'content', 'id', 'topic_id', etc.
            questions_per_chunk: Questions to generate per chunk
            difficulty: Difficulty level
            
        Returns:
            Combined QuizGenerationResult
        """
        all_questions = []
        all_errors = []
        combined_content = ""
        
        for chunk in chunks:
            content = chunk.get("content", "")
            topic_id = chunk.get("topic_id")
            topic_name = chunk.get("topic_name")
            chunk_id = chunk.get("id")
            
            result = await self.generate_quiz(
                content=content,
                question_count=questions_per_chunk,
                difficulty=difficulty,
                topic_name=topic_name,
                topic_id=topic_id,
            )
            
            # Add source chunk ID to questions
            for q in result.questions:
                q.source_chunk_id = chunk_id
            
            all_questions.extend(result.questions)
            all_errors.extend(result.errors)
            combined_content += content[:500] + "\n\n"
        
        return QuizGenerationResult(
            questions=all_questions,
            source_content=combined_content[:5000],
            difficulty=difficulty.value,
            success=len(all_questions) > 0,
            errors=all_errors,
        )
    
    async def generate_topic_quiz(
        self,
        topic_id: str,
        topic_name: str,
        context: str,
        question_count: int = 10,
        difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM,
    ) -> QuizGenerationResult:
        """Generate a quiz focused on a specific syllabus topic"""
        return await self.generate_quiz(
            content=context,
            question_count=question_count,
            difficulty=difficulty,
            topic_name=topic_name,
            topic_id=topic_id,
            style="topic_specific",
        )
    
    def _parse_questions(
        self,
        response: str,
        difficulty: QuestionDifficulty,
        topic_id: Optional[str],
        topic_name: Optional[str],
    ) -> List[GeneratedQuestion]:
        """Parse LLM response into GeneratedQuestion objects"""
        questions = []
        
        try:
            # Clean up response (remove markdown if present)
            clean_response = response.replace("```json", "").replace("```", "").strip()
            
            # Find the JSON array
            start_idx = clean_response.find('[')
            end_idx = clean_response.rfind(']')
            
            if start_idx != -1 and end_idx != -1:
                json_str = clean_response[start_idx:end_idx+1]
                parsed = json.loads(json_str)
                
                for item in parsed:
                    if self._validate_question(item):
                        questions.append(GeneratedQuestion(
                            question_text=item.get("question", item.get("question_text", "")),
                            options=item.get("options", []),
                            correct_option=item.get("correct", item.get("correct_option", 0)),
                            explanation=item.get("explanation", ""),
                            difficulty=difficulty.value,
                            topic_id=topic_id,
                            topic_name=topic_name,
                            confidence_score=0.8,
                        ))
            else:
                 # If no JSON brackets found, force backup parsing
                 logger.warning("No JSON brackets found in response")
                 questions = self._parse_json_objects_individually(clean_response, difficulty, topic_id, topic_name)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            # Try to parse objects individually (handles missing commas between args)
            questions = self._parse_json_objects_individually(
                clean_response if 'clean_response' in locals() else response, 
                difficulty, topic_id, topic_name
            )
        
        # If valid JSON parsed but empty, try backup (sometimes JSON is partial)
        if not questions:
             # Try evaluating as Python literal (handles single quotes, trailing commas)
             try:
                 # Find list brackets
                 start = response.find('[')
                 end = response.rfind(']')
                 if start != -1 and end != -1:
                     potential_list = response[start:end+1]
                     parsed = ast.literal_eval(potential_list)
                     if isinstance(parsed, list):
                        for item in parsed:
                            if self._validate_question(item):
                                questions.append(GeneratedQuestion(
                                    question_text=item.get("question", item.get("question_text", "")),
                                    options=item.get("options", []),
                                    correct_option=item.get("correct", item.get("correct_option", 0)),
                                    explanation=item.get("explanation", ""),
                                    difficulty=difficulty.value,
                                    topic_id=topic_id,
                                    topic_name=topic_name,
                                    confidence_score=0.8,
                                ))
             except Exception as e:
                 logger.warning(f"AST parse failed: {e}")

        # Final backup
        if not questions:
             questions = self._parse_backup(response, difficulty, topic_id, topic_name)

        return questions

    def _parse_json_objects_individually(
        self,
        text: str,
        difficulty: QuestionDifficulty,
        topic_id: Optional[str],
        topic_name: Optional[str],
    ) -> List[GeneratedQuestion]:
        """
        Robustly extract individual JSON objects like {...} from text.
        Useful when the main array is malformed (e.g. missing commas).
        """
        questions = []
        depth = 0
        start_index = -1
        
        # Simple stack-based extractor
        for i, char in enumerate(text):
            if char == '{':
                if depth == 0:
                    start_index = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start_index != -1:
                    # Found a potential object
                    json_str = text[start_index:i+1]
                    try:
                        item = json.loads(json_str)
                        if self._validate_question(item):
                            questions.append(GeneratedQuestion(
                                question_text=item.get("question", item.get("question_text", "")),
                                options=item.get("options", []),
                                correct_option=item.get("correct", item.get("correct_option", 0)),
                                explanation=item.get("explanation", ""),
                                difficulty=difficulty.value,
                                topic_id=topic_id,
                                topic_name=topic_name,
                                confidence_score=0.8,
                            ))
                    except json.JSONDecodeError:
                        # Try AST eval for single quotes
                        try:
                            item = ast.literal_eval(json_str)
                            if self._validate_question(item):
                                questions.append(GeneratedQuestion(
                                    question_text=item.get("question", item.get("question_text", "")),
                                    options=item.get("options", []),
                                    correct_option=item.get("correct", item.get("correct_option", 0)),
                                    explanation=item.get("explanation", ""),
                                    difficulty=difficulty.value,
                                    topic_id=topic_id,
                                    topic_name=topic_name,
                                    confidence_score=0.8,
                                ))
                        except Exception:
                            pass
                    start_index = -1
        
        return questions
    
    def _parse_backup(
        self,
        response: str,
        difficulty: QuestionDifficulty,
        topic_id: Optional[str],
        topic_name: Optional[str],
    ) -> List[GeneratedQuestion]:
        """Backup parsing for non-JSON responses"""
        questions = []
        
        # Try to find questions with numbered format
        # Try to find questions with numbered format using a more flexible pattern
        # Matches "1. Question?", "Q1: Question?", "**1.** Question?" etc.
        q_pattern = r'(?:^|[\n\r])(?:\*\*|\s)*(?:Q|Question)?\s*\d+[.:\)]\s*(.+?)(?=(?:^|[\n\r])(?:\*\*|\s)*(?:Q|Question)?\s*\d+[.:\)]|$)'
        matches = re.findall(q_pattern, response, re.DOTALL | re.IGNORECASE)
        
        # If no strict numbering, try double newline separation
        if not matches:
             blocks = response.split('\n\n')
             matches = [(None, b) for b in blocks if '?' in b and len(b) > 20]
        else:
             # Normalize matches to just the text
             matches = [(None, m) for m in matches]

        for _, q_text in matches:
            # Extract options
            options = re.findall(r'(?:^|[\n\r])\s*([A-Da-d])[.):\s]+(.+?)(?=(?:^|[\n\r])\s*[A-Da-d][.):]|$)', q_text, re.DOTALL)
            
            if len(options) >= 4:
                questions.append(GeneratedQuestion(
                    question_text=q_text.split('\n')[0].strip(),
                    options=[opt[1].strip() for opt in options[:4]],
                    correct_option=0,  # Default, may not be accurate
                    explanation="",
                    difficulty=difficulty.value,
                    topic_id=topic_id,
                    topic_name=topic_name,
                    confidence_score=0.5,  # Lower confidence for backup parsing
                ))
        
        return questions
    
    def _validate_question(self, item: Dict) -> bool:
        """Validate a parsed question"""
        if not isinstance(item, dict):
            return False
        
        question = item.get("question", item.get("question_text", ""))
        options = item.get("options", [])
        correct = item.get("correct", item.get("correct_option"))
        
        if not question or len(question) < 10:
            return False
        
        if not isinstance(options, list) or len(options) != 4:
            return False
        
        if correct is None or not isinstance(correct, int) or correct < 0 or correct > 3:
            return False
        
        return True
    
    async def _generate(self, prompt: str) -> str:
        """Generate using LLM"""
        if self.llm_client:
            return await self.llm_client.generate(
                prompt=prompt,
                system_prompt=QUIZ_SYSTEM_PROMPT,
                temperature=0.7,
            )
        else:
            # Mock response for testing
            return self._mock_response()
    
    def _mock_response(self) -> str:
        """Generate mock questions for testing"""
        return json.dumps([
            {
                "question": "Which Article of the Indian Constitution deals with the Right to Equality?",
                "options": [
                    "Article 12-14",
                    "Article 14-18",
                    "Article 19-22",
                    "Article 23-24"
                ],
                "correct": 1,
                "explanation": "Articles 14-18 of the Constitution deal with the Right to Equality, which includes equality before law, prohibition of discrimination, and abolition of untouchability."
            },
            {
                "question": "The concept of 'Basic Structure' doctrine was established in which case?",
                "options": [
                    "Golaknath Case",
                    "Kesavananda Bharati Case",
                    "Minerva Mills Case",
                    "Maneka Gandhi Case"
                ],
                "correct": 1,
                "explanation": "The Kesavananda Bharati Case (1973) established the Basic Structure doctrine, which limits Parliament's power to amend the Constitution."
            },
            {
                "question": "Which of the following is NOT a Fundamental Right?",
                "options": [
                    "Right to Equality",
                    "Right to Property",
                    "Right against Exploitation",
                    "Right to Constitutional Remedies"
                ],
                "correct": 1,
                "explanation": "Right to Property was removed as a Fundamental Right by the 44th Amendment (1978) and is now a legal right under Article 300A."
            }
        ])


# Factory function
async def create_quiz_generator(
    llm_provider: str = settings.LLM_PROVIDER,
    llm_model: str = settings.LLM_MODEL,
) -> QuizGenerator:
    """Create and initialize Quiz Generator"""
    from app.services.rag.pipeline import OllamaClient, HuggingFaceClient, MockLLMClient
    
    if llm_provider == "ollama":
        llm_client = OllamaClient(model=llm_model)
    elif llm_provider == "huggingface":
        llm_client = HuggingFaceClient(model=llm_model)
    else:
        llm_client = MockLLMClient()
    
    return QuizGenerator(llm_client=llm_client)
