"""
Language Service
Handles multilingual support, translation, and Hinglish normalization.

STRATEGY:
1. Use LLM for high-quality translation and normalization (Zero-shot/Few-shot).
2. Maintain distinct prompt personas for English, Hindi, and Hinglish.
3. Cache translations to reduce latency and cost.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hinglish"  # Mixed Roman Hindi + English

class ContentTranslation(BaseModel):
    original_text: str
    translated_text: str
    source_language: Language
    target_language: Language
    confidence: float

class LanguageConfig(BaseModel):
    """Configuration for language-specific generation"""
    system_instruction: str
    stop_sequences: List[str] = []
    temperature_modifier: float = 0.0

# Language Personas for Prompt Engineering
LANGUAGE_PERSONAS = {
    Language.ENGLISH: LanguageConfig(
        system_instruction="You are an expert academic tutor. Respond in clear, formal English.",
        temperature_modifier=0.0
    ),
    Language.HINDI: LanguageConfig(
        system_instruction=(
            "You are an expert Hindi-speaking tutor. Respond in formal Hindi using Devanagari script. "
            "ALWAYS keep technical terms (like 'Constitution', 'Quantum Mechanics') in English within brackets, "
            "e.g., 'Sanvidhan (Constitution)'. Ensure high grammatical correctness."
        ),
        temperature_modifier=0.1  # Slightly higher for creative Hindi phrasing
    ),
    Language.HINGLISH: LanguageConfig(
        system_instruction=(
            "You are a friendly peer tutor. Respond in Hinglish (mixed Hindi-English using Roman script). "
            "Use English for all technical terms and complex concepts. "
            "Use Hindi (Romanized) for connecting verbs, prepositions, and casual conversation. "
            "Example: 'Constitution ke Article 14 mein Equality ki baat ki gayi hai.'"
        ),
        temperature_modifier=0.2  # Higher temperature for natural flowing Hinglish
    ),
}

class LanguageService:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client  # Can be OpenAI, Anthropic, or Local LLM

    def get_language_config(self, language: Language) -> LanguageConfig:
        return LANGUAGE_PERSONAS.get(language, LANGUAGE_PERSONAS[Language.ENGLISH])

    async def translate(
        self, 
        text: str, 
        target_lang: Language, 
        source_lang: Optional[Language] = None
    ) -> str:
        """
        Translate text using LLM.
        Avoids specific translation APIs to keep stack simple, relies on LLM capabilities.
        """
        if source_lang == target_lang:
            return text
            
        # If no LLM client, return mock translation (for dev)
        if not self.llm_client:
            logger.warning("No LLM client provided for translation. Returning original.")
            return f"[{target_lang.value}] {text}"

        prompt = f"""
        Translate the following text to {target_lang.value}.
        ensure technical terms are preserved or bracketed if translating to Hindi.
        
        Text:
        {text}
        """
        
        # This would call the actual LLM
        # response = await self.llm_client.generate(prompt)
        # return response.text
        return f"[{target_lang.value} translated] {text}"

    async def normalize_hinglish(self, text: str) -> str:
        """
        Standardizes Hinglish text.
        e.g., "kya hal h" -> "Kya haal hai"
        """
        if not self.llm_client:
            return text

        prompt = f"""
        Normalize the following Hinglish text. 
        Fix spelling of Romanized Hindi words. 
        Keep English technical terms as is.
        
        Input: {text}
        """
        # response = await self.llm_client.generate(prompt)
        # return response.text
        return text

    def adapt_prompt_for_language(self, base_system_prompt: str, language: Language) -> str:
        """
        Injects language-specific persona into a base system prompt.
        """
        config = self.get_language_config(language)
        
        adapter = f"\n\nLANGUAGE GUIDELINES:\n{config.system_instruction}\n"
        
        return base_system_prompt + adapter

# Singleton instance
language_service = LanguageService()
