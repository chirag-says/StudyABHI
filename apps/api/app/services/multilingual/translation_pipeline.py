"""
Translation Pipeline Module
Handles translation between English, Hindi, and Hinglish without model retraining
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import httpx

from .language_detector import Language, DetectedLanguage, get_language_detector
from .hinglish_normalizer import get_hinglish_normalizer


class TranslationProvider(str, Enum):
    """Supported translation providers"""
    GOOGLE = "google"
    AZURE = "azure"
    DEEPL = "deepl"
    INDICTRANS = "indictrans"  # AI4Bharat's model for Indian languages


@dataclass
class TranslationResult:
    """Result of translation"""
    original_text: str
    translated_text: str
    source_language: Language
    target_language: Language
    provider: TranslationProvider
    confidence: float
    metadata: Dict[str, Any]


class TranslationBackend(ABC):
    """Abstract base class for translation backends"""
    
    @abstractmethod
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> str:
        """Translate text from source to target language"""
        pass


class GoogleTranslateBackend(TranslationBackend):
    """Google Translate API backend"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                params={"key": self.api_key},
                json={
                    "q": text,
                    "source": source_lang,
                    "target": target_lang,
                    "format": "text"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return data["data"]["translations"][0]["translatedText"]


class AzureTranslateBackend(TranslationBackend):
    """Azure Translator API backend"""
    
    def __init__(self, api_key: str, region: str = "eastus"):
        self.api_key = api_key
        self.region = region
        self.base_url = "https://api.cognitive.microsofttranslator.com/translate"
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                params={
                    "api-version": "3.0",
                    "from": source_lang,
                    "to": target_lang
                },
                headers={
                    "Ocp-Apim-Subscription-Key": self.api_key,
                    "Ocp-Apim-Subscription-Region": self.region,
                    "Content-Type": "application/json"
                },
                json=[{"text": text}]
            )
            response.raise_for_status()
            data = response.json()
            
            return data[0]["translations"][0]["text"]


class IndicTransBackend(TranslationBackend):
    """
    AI4Bharat IndicTrans backend for high-quality Indian language translation
    This is a local/self-hosted option for better Hindi<->English translation
    """
    
    def __init__(self, endpoint: str = "http://localhost:8000"):
        self.endpoint = endpoint
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/translate",
                json={
                    "text": text,
                    "source_language": source_lang,
                    "target_language": target_lang
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return data["translation"]


class FallbackTranslateBackend(TranslationBackend):
    """
    Fallback using free libraries (googletrans/deep-translator)
    For development/testing when API keys are not available
    """
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> str:
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            return translator.translate(text)
        except ImportError:
            # If deep_translator not available, try googletrans
            try:
                from googletrans import Translator
                translator = Translator()
                result = await asyncio.to_thread(
                    translator.translate, text, dest=target_lang, src=source_lang
                )
                return result.text
            except Exception:
                # Last resort: return original text
                return text


class TranslationPipeline:
    """
    Main translation pipeline that handles:
    1. Language detection
    2. Hinglish normalization
    3. Translation with fallback providers
    4. Response translation back to original language
    """
    
    # Language code mapping
    LANG_CODE_MAP = {
        Language.ENGLISH: "en",
        Language.HINDI: "hi",
        Language.HINGLISH: "hi",  # Treat as Hindi for translation purposes
    }
    
    def __init__(
        self,
        primary_provider: TranslationProvider = TranslationProvider.GOOGLE,
        google_api_key: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        azure_region: str = "eastus",
        indictrans_endpoint: Optional[str] = None,
    ):
        self.detector = get_language_detector()
        self.normalizer = get_hinglish_normalizer()
        
        # Initialize backends based on available credentials
        self.backends: Dict[TranslationProvider, TranslationBackend] = {}
        
        if google_api_key:
            self.backends[TranslationProvider.GOOGLE] = GoogleTranslateBackend(google_api_key)
        
        if azure_api_key:
            self.backends[TranslationProvider.AZURE] = AzureTranslateBackend(azure_api_key, azure_region)
        
        if indictrans_endpoint:
            self.backends[TranslationProvider.INDICTRANS] = IndicTransBackend(indictrans_endpoint)
        
        # Always add fallback
        self.fallback_backend = FallbackTranslateBackend()
        
        self.primary_provider = primary_provider
    
    async def translate_to_english(self, text: str) -> TranslationResult:
        """
        Translate any input (Hindi/Hinglish) to English
        
        Args:
            text: Input text in any supported language
            
        Returns:
            TranslationResult with English translation
        """
        # Step 1: Detect language
        detected = self.detector.detect(text)
        
        # If already English, return as-is
        if detected.language == Language.ENGLISH:
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=Language.ENGLISH,
                target_language=Language.ENGLISH,
                provider=TranslationProvider.GOOGLE,
                confidence=1.0,
                metadata={"no_translation_needed": True}
            )
        
        # Step 2: Normalize if Hinglish
        if detected.language == Language.HINGLISH:
            normalized = self.normalizer.normalize(text)
            text_to_translate = normalized.normalized
            metadata = {
                "was_hinglish": True,
                "standardized_words": normalized.standardized_words
            }
        else:
            text_to_translate = text
            metadata = {"was_hinglish": False}
        
        # Step 3: Translate
        source_lang_code = self.LANG_CODE_MAP.get(detected.language, "hi")
        translated = await self._translate_with_fallback(
            text_to_translate, 
            source_lang_code, 
            "en"
        )
        
        return TranslationResult(
            original_text=text,
            translated_text=translated["text"],
            source_language=detected.language,
            target_language=Language.ENGLISH,
            provider=translated["provider"],
            confidence=detected.confidence,
            metadata=metadata
        )
    
    async def translate_from_english(
        self, 
        text: str, 
        target_language: Language
    ) -> TranslationResult:
        """
        Translate English text to target language (Hindi or Hinglish-style)
        
        Args:
            text: English input text
            target_language: Target language
            
        Returns:
            TranslationResult with translated text
        """
        if target_language == Language.ENGLISH:
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=Language.ENGLISH,
                target_language=Language.ENGLISH,
                provider=TranslationProvider.GOOGLE,
                confidence=1.0,
                metadata={"no_translation_needed": True}
            )
        
        target_code = self.LANG_CODE_MAP.get(target_language, "hi")
        translated = await self._translate_with_fallback(text, "en", target_code)
        
        # For Hinglish, we might want to keep some English words
        if target_language == Language.HINGLISH:
            translated_text = self._hinglish_post_process(text, translated["text"])
        else:
            translated_text = translated["text"]
        
        return TranslationResult(
            original_text=text,
            translated_text=translated_text,
            source_language=Language.ENGLISH,
            target_language=target_language,
            provider=translated["provider"],
            confidence=0.9,
            metadata={}
        )
    
    async def _translate_with_fallback(
        self, 
        text: str, 
        source: str, 
        target: str
    ) -> Dict[str, Any]:
        """Attempt translation with fallback providers"""
        
        # Try primary provider first
        if self.primary_provider in self.backends:
            try:
                result = await self.backends[self.primary_provider].translate(
                    text, source, target
                )
                return {"text": result, "provider": self.primary_provider}
            except Exception:
                pass
        
        # Try other providers
        for provider, backend in self.backends.items():
            if provider != self.primary_provider:
                try:
                    result = await backend.translate(text, source, target)
                    return {"text": result, "provider": provider}
                except Exception:
                    continue
        
        # Use fallback
        result = await self.fallback_backend.translate(text, source, target)
        return {"text": result, "provider": TranslationProvider.GOOGLE}
    
    def _hinglish_post_process(self, original_english: str, translated_hindi: str) -> str:
        """
        Post-process Hindi translation to create natural Hinglish
        by keeping certain English terms
        """
        # Words to keep in English (technical terms, proper nouns, etc.)
        keep_english = {
            # Technical terms
            "UPSC", "IAS", "IPS", "IFS", "CSAT", "prelims", "mains",
            "constitution", "parliament", "democracy",
            # Common English words used in Hinglish
            "please", "thank you", "sorry", "okay", "yes", "no",
            "question", "answer", "option", "correct", "wrong",
            # Study-related
            "syllabus", "exam", "paper", "topic", "chapter",
        }
        
        # This is a simplified implementation
        # A more sophisticated version would use NER and glossary matching
        return translated_hindi
    
    async def round_trip_translate(
        self, 
        text: str, 
        preserve_original_language: bool = True
    ) -> Dict[str, str]:
        """
        Translate to English for processing, then back to original language
        
        Useful for LLM processing where we want to:
        1. Process in English for best results
        2. Respond in user's original language
        
        Args:
            text: Original input text
            preserve_original_language: If True, translate response back to original
            
        Returns:
            Dict with 'english', 'original_language', and optionally 'response' translations
        """
        detected = self.detector.detect(text)
        
        # Get English version
        to_english = await self.translate_to_english(text)
        
        result = {
            "original": text,
            "original_language": detected.language.value,
            "english": to_english.translated_text,
            "confidence": detected.confidence
        }
        
        return result


# Factory function
def create_translation_pipeline(
    google_api_key: Optional[str] = None,
    azure_api_key: Optional[str] = None,
    **kwargs
) -> TranslationPipeline:
    """Create a configured translation pipeline"""
    return TranslationPipeline(
        google_api_key=google_api_key,
        azure_api_key=azure_api_key,
        **kwargs
    )
