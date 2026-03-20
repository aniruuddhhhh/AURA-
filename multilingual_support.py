
import os
from typing import Optional, Tuple

from language_config import (
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    VOICE_LANGUAGE_CODES,
    UI_TRANSLATIONS,
    SAMPLE_QUESTIONS,
)

GOOGLE_TRANSLATE_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "SET_YOUR_API")
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_AVAILABLE = True
except:
    GEMINI_AVAILABLE = False
def detect_language(text: str) -> str:
    """
    Detect language of text.
    Returns language code: 'en', 'hi', 'es'
    """
    if not text or len(text.strip()) < 3:
        return DEFAULT_LANGUAGE

    text_lower = text.lower()
 
    if any('\u0900' <= char <= '\u097F' for char in text):
        return 'hi'
    spanish_words = ['qué', 'cómo', 'dónde', 'cuándo', 'mi', 'dormir', 'fue', 'está']
    if any(word in text_lower for word in spanish_words):
        return 'es'
    return 'en'

def translate_text_gemini(text: str, target_lang: str, source_lang: str = None) -> str:
    """
    Translate text using Gemini (high quality).
    """
    if not GEMINI_AVAILABLE:
        return text
    
    try:
        if not source_lang:
            source_lang = detect_language(text)
        
        if source_lang == target_lang:
            return text

        target_name = SUPPORTED_LANGUAGES.get(target_lang, {}).get('name', target_lang)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""Translate this text to {target_name}. 
Only provide the translation, nothing else.

Text: {text}

Translation:"""
        
        response = model.generate_content(prompt)
        translation = response.text.strip()
        
        print(f"[Translation] {source_lang} → {target_lang}: {len(text)} chars")
        return translation
        
    except Exception as e:
        print(f"[Translation] Gemini error: {e}")
        return text

def translate_text_google(text: str, target_lang: str, source_lang: str = None) -> str:
    """
    Google Translate fallback - DISABLED due to dependency conflicts.
    Use Gemini instead (higher quality).
    """
    print(f"[Translation] Google Translate unavailable - using Gemini only")
    return text

def translate_text(text: str, target_lang: str, source_lang: str = None) -> str:
    """
    Translate text to target language using Gemini AI.
    Note: Google Translate disabled due to dependency conflicts.
    """
    if not text or len(text.strip()) == 0:
        return text

    if GEMINI_AVAILABLE:
        return translate_text_gemini(text, target_lang, source_lang)

    print(f"[Translation] ⚠️  Gemini not available - translation skipped")
    print(f"[Translation] 💡 Set GEMINI_API_KEY environment variable to enable translation")
    return text

def store_journal_multilingual(entry: str, user_lang: str) -> Tuple[str, str]:
    """
    Store journal in both original language and English (for search).
    Returns: (original_text, english_text)
    """
    original = entry

    if user_lang != 'en':
        english = translate_text(entry, 'en', user_lang)
    else:
        english = entry
    
    return original, english

def prepare_search_query(query: str, user_lang: str) -> str:
    """
    Prepare search query by translating to English if needed.
    This allows cross-language search.
    """
    if user_lang == 'en':
        return query

    english_query = translate_text(query, 'en', user_lang)
    print(f"[Search] Translated query: '{query}' → '{english_query}'")
    return english_query

def get_language_instruction(target_lang: str) -> str:
    """
    Get instruction for AI to respond in specific language.
    """
    if target_lang == 'en':
        return ""  # Default
    
    lang_name = SUPPORTED_LANGUAGES.get(target_lang, {}).get('native', 'English')
    
    return f"\n\nIMPORTANT: Respond in {lang_name}. The user prefers {lang_name} language."

def get_ui_text(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Get UI text in specified language."""
    return UI_TRANSLATIONS.get(key, {}).get(lang, UI_TRANSLATIONS.get(key, {}).get('en', key))


def get_language_display(lang_code: str) -> str:
    """Get display string for language: '🇬🇧 English'"""
    lang = SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES['en'])
    return f"{lang['flag']} {lang['native']}"

def get_all_languages() -> list:
    """Get list of all supported languages for UI dropdown."""
    return [
        (code, get_language_display(code)) 
        for code in SUPPORTED_LANGUAGES.keys()
    ]

def get_sample_questions(lang_code: str) -> list:
    """Get sample questions for specified language."""
    return SAMPLE_QUESTIONS.get(lang_code, SAMPLE_QUESTIONS.get('en', []))

def get_voice_language_code(lang_code: str) -> str:
    """Get language code for voice recognition."""
    return VOICE_LANGUAGE_CODES.get(lang_code, 'en-US')

if __name__ == "__main__":
    print("="*80)
    print("MULTILINGUAL SUPPORT TEST")
    print("="*80)
    
    # Test detection
    print("\n1. Language Detection:")
    print(f"   'Hello' → {detect_language('Hello')}")
    print(f"   'नमस्ते' → {detect_language('नमस्ते')}")
    print(f"   'Hola' → {detect_language('Hola')}")
    
    # Test translation
    print("\n2. Translation Test:")
    test_text = "I slept very well today"
    
    if GEMINI_AVAILABLE:
        print(f"   EN→HI: {translate_text(test_text, 'hi', 'en')}")
        print(f"   EN→ES: {translate_text(test_text, 'es', 'en')}")
    else:
        print("   ⚠️  Gemini not available")
    
    # Test language list
    print("\n3. Supported Languages:")
    for code, display in get_all_languages():
        print(f"   {display} ({code})")
    
    print("\n" + "="*80)
