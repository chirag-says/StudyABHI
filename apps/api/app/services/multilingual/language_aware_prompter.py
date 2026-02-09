"""
Language-Aware Prompting Module
"""
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
from .language_detector import Language, DetectedLanguage, get_language_detector


class PromptStyle(str, Enum):
    TRANSLATE_PROCESS_TRANSLATE = "translate_process_translate"
    DIRECT_MULTILINGUAL = "direct_multilingual"
    ENGLISH_WITH_CONTEXT = "english_with_context"


@dataclass
class LanguageAwarePrompt:
    system_prompt: str
    user_prompt: str
    detected_language: Language
    prompt_style: PromptStyle
    response_language_instruction: str
    metadata: Dict[str, Any]


class LanguageAwarePrompter:
    SYSTEM_PROMPTS = {
        Language.ENGLISH: "You are an expert UPSC preparation assistant helping students prepare for Civil Services Examination.",
        Language.HINDI: "आप एक विशेषज्ञ UPSC तैयारी सहायक हैं।",
        Language.HINGLISH: "Aap ek expert UPSC preparation assistant hain. Hindi aur English mix karke respond karein.",
    }
    
    RESPONSE_INSTRUCTIONS = {
        Language.ENGLISH: "Respond in English.",
        Language.HINDI: "कृपया हिंदी में उत्तर दें।",
        Language.HINGLISH: "Respond in Hinglish (Hindi-English mix) using Roman script.",
    }

    def __init__(self, default_style: PromptStyle = PromptStyle.DIRECT_MULTILINGUAL):
        self.detector = get_language_detector()
        self.default_style = default_style

    def create_prompt(self, user_message: str, context: Optional[str] = None,
                     force_language: Optional[Language] = None) -> LanguageAwarePrompt:
        if force_language:
            lang = force_language
            confidence = 1.0
        else:
            detected = self.detector.detect(user_message)
            lang = detected.language
            confidence = detected.confidence
        
        system = self.SYSTEM_PROMPTS.get(lang, self.SYSTEM_PROMPTS[Language.ENGLISH])
        response_inst = self.RESPONSE_INSTRUCTIONS.get(lang, self.RESPONSE_INSTRUCTIONS[Language.ENGLISH])
        system += f"\n\n{response_inst}"
        
        user_prompt = f"Context:\n{context}\n\n{user_message}" if context else user_message
        
        return LanguageAwarePrompt(
            system_prompt=system,
            user_prompt=user_prompt,
            detected_language=lang,
            prompt_style=self.default_style,
            response_language_instruction=response_inst,
            metadata={"confidence": confidence}
        )


def create_language_aware_prompter(style: PromptStyle = PromptStyle.DIRECT_MULTILINGUAL) -> LanguageAwarePrompter:
    return LanguageAwarePrompter(default_style=style)
