"""
Multilingual Processor - Unified interface for multilingual NLP
"""
from typing import Dict, Optional, Any
from dataclasses import dataclass

from .language_detector import Language, DetectedLanguage, get_language_detector
from .hinglish_normalizer import get_hinglish_normalizer, NormalizationResult
from .translation_pipeline import TranslationPipeline, TranslationResult
from .language_aware_prompter import LanguageAwarePrompter, LanguageAwarePrompt, PromptStyle


@dataclass
class ProcessedInput:
    """Complete processed multilingual input"""
    original_text: str
    detected_language: DetectedLanguage
    normalized_text: str
    english_translation: Optional[str]
    prompt: LanguageAwarePrompt
    metadata: Dict[str, Any]


@dataclass
class ProcessedOutput:
    """Complete processed multilingual output"""
    llm_response: str
    translated_response: Optional[str]
    target_language: Language
    final_response: str


class MultilingualProcessor:
    """
    Unified processor for multilingual NLP pipeline
    
    Usage:
        processor = MultilingualProcessor()
        
        # Process user input
        processed = await processor.process_input("UPSC ki taiyari kaise karein?")
        
        # Use processed.prompt for LLM
        llm_response = await call_llm(processed.prompt)
        
        # Process output
        output = await processor.process_output(llm_response, processed.detected_language.language)
    """
    
    def __init__(
        self,
        google_api_key: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        prompt_style: PromptStyle = PromptStyle.DIRECT_MULTILINGUAL
    ):
        self.detector = get_language_detector()
        self.normalizer = get_hinglish_normalizer()
        self.translator = TranslationPipeline(
            google_api_key=google_api_key,
            azure_api_key=azure_api_key
        )
        self.prompter = LanguageAwarePrompter(default_style=prompt_style)
    
    async def process_input(
        self,
        text: str,
        context: Optional[str] = None,
        translate_to_english: bool = False
    ) -> ProcessedInput:
        """
        Process multilingual input through the full pipeline
        
        Args:
            text: User input text
            context: Optional conversation context
            translate_to_english: Force translation to English for LLM
        """
        # Step 1: Detect language
        detected = self.detector.detect(text)
        
        # Step 2: Normalize if Hinglish
        if detected.language == Language.HINGLISH:
            normalized = self.normalizer.normalize(text)
            normalized_text = normalized.normalized
        else:
            normalized_text = text
        
        # Step 3: Translate if needed
        english_translation = None
        if translate_to_english and detected.language != Language.ENGLISH:
            translation = await self.translator.translate_to_english(normalized_text)
            english_translation = translation.translated_text
        
        # Step 4: Create language-aware prompt
        prompt = self.prompter.create_prompt(
            user_message=english_translation or normalized_text,
            context=context,
            force_language=detected.language if not translate_to_english else Language.ENGLISH
        )
        
        return ProcessedInput(
            original_text=text,
            detected_language=detected,
            normalized_text=normalized_text,
            english_translation=english_translation,
            prompt=prompt,
            metadata={
                "was_translated": english_translation is not None,
                "was_normalized": detected.language == Language.HINGLISH
            }
        )
    
    async def process_output(
        self,
        llm_response: str,
        target_language: Language,
        was_translated_to_english: bool = False
    ) -> ProcessedOutput:
        """
        Process LLM output for multilingual response
        
        Args:
            llm_response: Raw response from LLM
            target_language: User's original language
            was_translated_to_english: If input was translated
        """
        translated_response = None
        
        if was_translated_to_english and target_language != Language.ENGLISH:
            translation = await self.translator.translate_from_english(
                llm_response, target_language
            )
            translated_response = translation.translated_text
            final = translated_response
        else:
            final = llm_response
        
        return ProcessedOutput(
            llm_response=llm_response,
            translated_response=translated_response,
            target_language=target_language,
            final_response=final
        )
    
    def detect_language(self, text: str) -> DetectedLanguage:
        """Quick language detection"""
        return self.detector.detect(text)
    
    def normalize_hinglish(self, text: str) -> NormalizationResult:
        """Quick Hinglish normalization"""
        return self.normalizer.normalize(text)


def create_multilingual_processor(**kwargs) -> MultilingualProcessor:
    """Factory function for MultilingualProcessor"""
    return MultilingualProcessor(**kwargs)
