"""
Example usage of the Multilingual NLP Pipeline
"""
import asyncio
from app.services.multilingual import (
    LanguageDetector,
    HinglishNormalizer,
    TranslationPipeline,
    LanguageAwarePrompter,
    MultilingualProcessor
)


async def demo_language_detection():
    """Demonstrate language detection"""
    detector = LanguageDetector()
    
    test_cases = [
        "How to prepare for UPSC?",                           # English
        "UPSC की तैयारी कैसे करें?",                            # Hindi (Devanagari)
        "UPSC ki taiyari kaise karein?",                      # Hinglish (Roman)
        "Mujhe polity ke bare mein batao",                    # Hinglish
        "What is the संविधान of India?",                      # Mixed script
        "Please explain Article 370 ke baare mein",           # Hinglish with English
    ]
    
    print("=" * 60)
    print("LANGUAGE DETECTION DEMO")
    print("=" * 60)
    
    for text in test_cases:
        result = detector.detect(text)
        print(f"\nText: {text}")
        print(f"  Language: {result.language.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Script: {result.script}")
        print(f"  Code-mixing: {result.has_code_mixing}")


async def demo_hinglish_normalization():
    """Demonstrate Hinglish normalization"""
    normalizer = HinglishNormalizer()
    
    test_cases = [
        "kia aap mujhe btayenge ki UPSC exam kaise hota hai?",
        "mein nhi samjha, plz explain kro",
        "ye bohot mushkil hai, kya karu?",
    ]
    
    print("\n" + "=" * 60)
    print("HINGLISH NORMALIZATION DEMO")
    print("=" * 60)
    
    for text in test_cases:
        result = normalizer.normalize(text)
        print(f"\nOriginal: {text}")
        print(f"Normalized: {result.normalized}")
        if result.standardized_words:
            print(f"Standardized: {result.standardized_words}")


async def demo_full_pipeline():
    """Demonstrate the full multilingual processing pipeline"""
    processor = MultilingualProcessor()
    
    test_inputs = [
        "How do I start UPSC preparation?",
        "UPSC ki taiyari kaise shuru karein?",
        "मुझे भारतीय राजव्यवस्था के बारे में बताएं",
    ]
    
    print("\n" + "=" * 60)
    print("FULL PIPELINE DEMO")
    print("=" * 60)
    
    for text in test_inputs:
        processed = await processor.process_input(text)
        print(f"\n--- Input: {text} ---")
        print(f"Detected: {processed.detected_language.language.value}")
        print(f"Normalized: {processed.normalized_text}")
        print(f"\nSystem Prompt (truncated):")
        print(f"  {processed.prompt.system_prompt[:100]}...")
        print(f"\nResponse Instruction:")
        print(f"  {processed.prompt.response_language_instruction}")


async def demo_prompting_strategies():
    """Demonstrate different prompting strategies"""
    from app.services.multilingual.language_aware_prompter import PromptStyle
    
    prompter = LanguageAwarePrompter()
    
    question = "UPSC mein kitne papers hote hain?"
    
    print("\n" + "=" * 60)
    print("PROMPTING STRATEGIES DEMO")
    print("=" * 60)
    
    prompt = prompter.create_prompt(question)
    print(f"\nQuestion: {question}")
    print(f"Detected Language: {prompt.detected_language.value}")
    print(f"\nSystem Prompt:\n{prompt.system_prompt}")


async def main():
    """Run all demos"""
    await demo_language_detection()
    await demo_hinglish_normalization()
    await demo_full_pipeline()
    await demo_prompting_strategies()


if __name__ == "__main__":
    asyncio.run(main())
