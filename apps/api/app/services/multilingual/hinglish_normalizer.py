"""
Hinglish Normalization Module
Handles standardization of Hinglish text for consistent processing
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class NormalizationResult:
    """Result of Hinglish normalization"""
    original: str
    normalized: str
    standardized_words: Dict[str, str]  # original -> normalized mapping
    separated_hindi: str  # Hindi portions extracted
    separated_english: str  # English portions extracted


class HinglishNormalizer:
    """
    Normalizes Hinglish text by:
    1. Standardizing spelling variations (e.g., kya/kia/kiya → kya)
    2. Handling common transliteration variations
    3. Separating code-mixed segments for targeted translation
    """
    
    # Common spelling variations mapping (variant -> standard)
    SPELLING_NORMALIZATIONS: Dict[str, str] = {
        # Kya variations
        "kia": "kya", "kyaa": "kya", "kiya": "kya",
        
        # Hai variations  
        "he": "hai", "hein": "hai", "h": "hai",
        
        # Nahi variations
        "nhi": "nahi", "nahin": "nahi", "nai": "nahi", "ni": "nahi",
        
        # Main/Mein variations
        "mein": "main", "mai": "main", "me": "main",
        
        # Aur variations
        "or": "aur", "aor": "aur",
        
        # Tha/Thi variations
        "thaa": "tha", "thee": "thi",
        
        # Hoga variations
        "honga": "hoga", "hongey": "honge",
        
        # Accha variations
        "acha": "accha", "achha": "accha", "achchha": "accha",
        
        # Bahut variations
        "bhaut": "bahut", "bohot": "bahut", "boht": "bahut",
        
        # Theek variations
        "thik": "theek", "thek": "theek", "teek": "theek",
        
        # Karo variations
        "kro": "karo", "krro": "karo",
        
        # Dekho variations
        "dkho": "dekho", "dekh": "dekho",
        
        # Please variations (English word commonly used)
        "plz": "please", "pls": "please", "plss": "please",
        
        # Thanks variations
        "thnx": "thanks", "thx": "thanks", "thanku": "thank you",
        "shukriya": "shukriya", "dhanyavaad": "dhanyavaad",
        
        # Common contractions
        "u": "you", "ur": "your", "r": "are", "b4": "before",
        "2day": "today", "2morrow": "tomorrow", "2mrw": "tomorrow",
        
        # Yeh/Woh variations
        "ye": "yeh", "yah": "yeh",
        "wo": "woh", "wahi": "wohi",
        
        # Bhi variations
        "b": "bhi", "v": "bhi",
        
        # Zyada variations
        "jyada": "zyada", "jayda": "zyada", "zada": "zyada",
    }
    
    # Common Hindi words that should be preserved (not translated)
    PRESERVE_HINDI_WORDS = {
        "namaste", "dhanyavaad", "shukriya", "ji", "sahab", 
        "bhai", "didi", "beta", "beti", "papa", "mummy",
        "yaar", "dost", "guru", "pandit", "swami",
        "karma", "dharma", "yoga", "mantra", "guru",
        # UPSC specific terms
        "loksabha", "lok sabha", "rajyasabha", "rajya sabha", 
        "sansad", "vidhan sabha", "panchayat", "zila", "tehsil",
        "patwari", "sarpanch", "pradhan", "mukhiya",
    }
    
    # Devanagari pattern
    DEVANAGARI_PATTERN = re.compile(r'[\u0900-\u097F]+')
    
    # Word boundary pattern for Hindi words in Roman script
    HINGLISH_WORD_PATTERN = re.compile(r'\b[a-zA-Z]+\b')
    
    def __init__(self):
        # Build reverse lookup for faster matching
        self._variant_lookup = {
            variant.lower(): standard.lower() 
            for variant, standard in self.SPELLING_NORMALIZATIONS.items()
        }
    
    def normalize(self, text: str) -> NormalizationResult:
        """
        Normalize Hinglish text
        
        Args:
            text: Input Hinglish text
            
        Returns:
            NormalizationResult with normalized text and metadata
        """
        if not text:
            return NormalizationResult(
                original=text,
                normalized=text,
                standardized_words={},
                separated_hindi="",
                separated_english=""
            )
        
        standardized_words = {}
        normalized_text = text
        
        # Step 1: Normalize spelling variations
        def replace_word(match):
            word = match.group(0)
            word_lower = word.lower()
            
            if word_lower in self._variant_lookup:
                standard = self._variant_lookup[word_lower]
                # Preserve original case pattern
                if word.isupper():
                    standard = standard.upper()
                elif word[0].isupper():
                    standard = standard.capitalize()
                
                standardized_words[word] = standard
                return standard
            return word
        
        normalized_text = self.HINGLISH_WORD_PATTERN.sub(replace_word, normalized_text)
        
        # Step 2: Separate Hindi and English portions
        separated_hindi = self._extract_hindi_portions(normalized_text)
        separated_english = self._extract_english_portions(normalized_text)
        
        return NormalizationResult(
            original=text,
            normalized=normalized_text,
            standardized_words=standardized_words,
            separated_hindi=separated_hindi,
            separated_english=separated_english
        )
    
    def _extract_hindi_portions(self, text: str) -> str:
        """Extract Devanagari portions from text"""
        matches = self.DEVANAGARI_PATTERN.findall(text)
        return " ".join(matches)
    
    def _extract_english_portions(self, text: str) -> str:
        """Extract likely English words from text"""
        words = self.HINGLISH_WORD_PATTERN.findall(text)
        
        # Filter out known Hindi/Hinglish words
        english_words = []
        for word in words:
            word_lower = word.lower()
            # Keep if not a Hindi marker and not in normalization dict
            if (word_lower not in self._variant_lookup and 
                word_lower not in self.PRESERVE_HINDI_WORDS and
                not self._is_likely_hindi_word(word_lower)):
                english_words.append(word)
        
        return " ".join(english_words)
    
    def _is_likely_hindi_word(self, word: str) -> bool:
        """
        Heuristic to detect if a word is likely Hindi written in Roman script
        Based on common Hindi word patterns
        """
        hindi_patterns = [
            r'.*[aeiou]n[aeiou]$',  # e.g., karna, bolna
            r'.*[aeiou]ng[aeiou]$',  # e.g., honge, jayenge
            r'.*[aeiou]y[aeiou]$',   # e.g., gaya, kiya
            r'^(un|in|an).*',        # Common Hindi prefixes
            r'.*wala$',              # e.g., doodh wala
            r'.*wali$',              # e.g., chai wali
        ]
        
        return any(re.match(pattern, word) for pattern in hindi_patterns)
    
    def standardize_for_translation(self, text: str) -> str:
        """
        Prepare Hinglish text for translation by:
        1. Normalizing spellings
        2. Adding markers for Hindi portions
        """
        result = self.normalize(text)
        
        # Mark Devanagari portions for the translator
        marked_text = result.normalized
        
        # Replace Devanagari with marked version
        def mark_devanagari(match):
            return f"[HINDI:{match.group(0)}]"
        
        marked_text = self.DEVANAGARI_PATTERN.sub(mark_devanagari, marked_text)
        
        return marked_text
    
    def split_by_language(self, text: str) -> List[Tuple[str, str]]:
        """
        Split text into segments by language
        
        Returns:
            List of (segment, language) tuples where language is 'hi', 'en', or 'hinglish'
        """
        segments = []
        current_segment = ""
        current_lang = None
        
        words = text.split()
        
        for word in words:
            # Check if word contains Devanagari
            if self.DEVANAGARI_PATTERN.search(word):
                word_lang = "hi"
            elif word.lower() in self._variant_lookup or self._is_likely_hindi_word(word.lower()):
                word_lang = "hinglish"
            else:
                word_lang = "en"
            
            if current_lang is None:
                current_lang = word_lang
                current_segment = word
            elif word_lang == current_lang or word_lang == "hinglish" or current_lang == "hinglish":
                current_segment += " " + word
            else:
                if current_segment:
                    segments.append((current_segment.strip(), current_lang))
                current_segment = word
                current_lang = word_lang
        
        if current_segment:
            segments.append((current_segment.strip(), current_lang))
        
        return segments


# Singleton instance
_normalizer_instance: Optional[HinglishNormalizer] = None


def get_hinglish_normalizer() -> HinglishNormalizer:
    """Get or create the Hinglish normalizer singleton"""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = HinglishNormalizer()
    return _normalizer_instance
