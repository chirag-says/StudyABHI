"""
Language Detection Module
Detects English, Hindi, and Hinglish (code-mixed) text
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from langdetect import detect, detect_langs, LangDetectException


class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hinglish"
    UNKNOWN = "unknown"


@dataclass
class DetectedLanguage:
    """Result of language detection"""
    language: Language
    confidence: float
    script: str  # "latin", "devanagari", "mixed"
    english_ratio: float
    hindi_ratio: float
    has_code_mixing: bool


class LanguageDetector:
    """
    Detects language with special handling for Hinglish (Hindi-English code-mixing)
    
    Hinglish detection is tricky because:
    1. It can be written in Latin script (Romanized Hindi)
    2. It can mix Devanagari and Latin scripts
    3. It can have English words in Hindi sentences
    """
    
    # Common Hindi words written in Roman script
    HINGLISH_MARKERS = {
        # Common verbs
        "kya", "hai", "hain", "ho", "tha", "thi", "the", "hoga", "hogi",
        "kar", "karo", "karna", "karenge", "kiya", "kiye",
        "de", "do", "dena", "denge", "diya", "diye",
        "le", "lo", "lena", "lenge", "liya", "liye",
        "ja", "jao", "jana", "jayenge", "gaya", "gaye", "gayi",
        "aa", "aao", "aana", "aayenge", "aaya", "aaye", "aayi",
        "bol", "bolo", "bolna", "bolenge", "bola", "bole", "boli",
        "dekh", "dekho", "dekhna", "dekhenge", "dekha", "dekhe", "dekhi",
        "sun", "suno", "sunna", "sunenge", "suna", "sune", "suni",
        
        # Common pronouns
        "main", "mein", "mai", "hum", "tum", "aap", "tu",
        "mera", "meri", "mere", "hamara", "hamari", "hamare",
        "tera", "teri", "tere", "tumhara", "tumhari", "tumhare",
        "uska", "uski", "uske", "unka", "unki", "unke",
        "yeh", "ye", "woh", "wo", "isko", "usko",
        
        # Common conjunctions/particles
        "aur", "ya", "lekin", "magar", "par", "phir", "tab",
        "toh", "to", "bhi", "sirf", "bas", "abhi", "kabhi",
        "kab", "kahan", "kaise", "kyun", "kyunki", "isliye",
        
        # Common nouns
        "log", "aadmi", "ladka", "ladki", "ghar", "kaam", "din", "raat",
        "paisa", "samay", "jagah", "baat", "cheez", "tarah",
        
        # Common adjectives
        "accha", "achha", "bura", "bada", "chota", "naya", "purana",
        "sahi", "galat", "theek", "thik", "bahut", "zyada", "kam",
        
        # Question words
        "kya", "kaun", "kitna", "kitne", "kitni",
        
        # Negative markers
        "nahi", "nahin", "nhi", "mat", "na",
        
        # Time-related
        "kal", "aaj", "parso", "abhi", "baad",
    }
    
    # Devanagari Unicode range
    DEVANAGARI_PATTERN = re.compile(r'[\u0900-\u097F]')
    
    # Extended Latin (includes accented characters common in transliteration)
    LATIN_PATTERN = re.compile(r'[a-zA-Z]')
    
    def __init__(self, hinglish_threshold: float = 0.15):
        """
        Args:
            hinglish_threshold: Minimum ratio of Hinglish markers to consider text as Hinglish
        """
        self.hinglish_threshold = hinglish_threshold
    
    def detect(self, text: str) -> DetectedLanguage:
        """
        Detect the language of the given text
        
        Args:
            text: Input text to analyze
            
        Returns:
            DetectedLanguage with language, confidence, and metadata
        """
        if not text or not text.strip():
            return DetectedLanguage(
                language=Language.UNKNOWN,
                confidence=0.0,
                script="unknown",
                english_ratio=0.0,
                hindi_ratio=0.0,
                has_code_mixing=False
            )
        
        # Analyze script composition
        script_info = self._analyze_script(text)
        
        # Check for Hinglish (code-mixing)
        hinglish_score = self._calculate_hinglish_score(text)
        
        # Use langdetect for base detection
        try:
            detected_langs = detect_langs(text)
            primary_lang = detected_langs[0] if detected_langs else None
        except LangDetectException:
            primary_lang = None
        
        # Decision logic
        if script_info["mixed"] or script_info["devanagari_ratio"] > 0 and script_info["latin_ratio"] > 0:
            # Mixed script - likely Hinglish with some Devanagari
            return DetectedLanguage(
                language=Language.HINGLISH,
                confidence=0.85,
                script="mixed",
                english_ratio=script_info["latin_ratio"],
                hindi_ratio=script_info["devanagari_ratio"],
                has_code_mixing=True
            )
        
        if script_info["devanagari_ratio"] > 0.5:
            # Primarily Devanagari - Hindi
            return DetectedLanguage(
                language=Language.HINDI,
                confidence=0.9,
                script="devanagari",
                english_ratio=script_info["latin_ratio"],
                hindi_ratio=script_info["devanagari_ratio"],
                has_code_mixing=script_info["latin_ratio"] > 0.1
            )
        
        if hinglish_score > self.hinglish_threshold:
            # Roman script but with Hindi words - Hinglish
            return DetectedLanguage(
                language=Language.HINGLISH,
                confidence=min(0.9, 0.5 + hinglish_score),
                script="latin",
                english_ratio=1.0 - hinglish_score,
                hindi_ratio=hinglish_score,
                has_code_mixing=True
            )
        
        if primary_lang:
            if primary_lang.lang == "hi":
                return DetectedLanguage(
                    language=Language.HINDI,
                    confidence=primary_lang.prob,
                    script="devanagari" if script_info["devanagari_ratio"] > 0.5 else "latin",
                    english_ratio=script_info["latin_ratio"],
                    hindi_ratio=script_info["devanagari_ratio"],
                    has_code_mixing=False
                )
            elif primary_lang.lang == "en":
                return DetectedLanguage(
                    language=Language.ENGLISH,
                    confidence=primary_lang.prob,
                    script="latin",
                    english_ratio=1.0,
                    hindi_ratio=0.0,
                    has_code_mixing=False
                )
        
        # Default to English for Latin script
        return DetectedLanguage(
            language=Language.ENGLISH,
            confidence=0.7,
            script="latin",
            english_ratio=1.0,
            hindi_ratio=0.0,
            has_code_mixing=False
        )
    
    def _analyze_script(self, text: str) -> Dict[str, float]:
        """Analyze the script composition of the text"""
        total_chars = len(text.replace(" ", ""))
        if total_chars == 0:
            return {"devanagari_ratio": 0.0, "latin_ratio": 0.0, "mixed": False}
        
        devanagari_chars = len(self.DEVANAGARI_PATTERN.findall(text))
        latin_chars = len(self.LATIN_PATTERN.findall(text))
        
        devanagari_ratio = devanagari_chars / total_chars
        latin_ratio = latin_chars / total_chars
        
        # Mixed if both scripts are significantly present
        mixed = devanagari_ratio > 0.1 and latin_ratio > 0.1
        
        return {
            "devanagari_ratio": devanagari_ratio,
            "latin_ratio": latin_ratio,
            "mixed": mixed
        }
    
    def _calculate_hinglish_score(self, text: str) -> float:
        """
        Calculate how likely the text is Hinglish based on marker words
        
        Returns a score between 0 and 1
        """
        # Tokenize (simple word-based)
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        if not words:
            return 0.0
        
        hinglish_word_count = sum(1 for word in words if word in self.HINGLISH_MARKERS)
        
        return hinglish_word_count / len(words)
    
    def is_hinglish(self, text: str) -> bool:
        """Quick check if text is Hinglish"""
        result = self.detect(text)
        return result.language == Language.HINGLISH
    
    def get_dominant_language(self, text: str) -> Language:
        """Get the dominant language without full analysis"""
        return self.detect(text).language


# Singleton instance for easy access
_detector_instance: Optional[LanguageDetector] = None


def get_language_detector() -> LanguageDetector:
    """Get or create the language detector singleton"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = LanguageDetector()
    return _detector_instance
