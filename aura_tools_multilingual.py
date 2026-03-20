
import sys
import os

from aura_tools_gemini import (
    run_query as run_query_base,
    search_journals_realtime,
    execute_sql,
    generate_gemini_sql,
    get_enhanced_template_sql,
    parse_date,
    CURRENT_USER_ID,
    GEMINI_AVAILABLE,
)

from multilingual_support import (
    detect_language,
    translate_text,
    get_language_instruction,
    prepare_search_query,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
)

import google.generativeai as genai
GEMINI_MODEL = "gemini-2.5-flash"

def run_query_multilingual(user_input: str, chat_history: list[dict] | None = None, user_language: str = 'en') -> str:
    """
    Multilingual wrapper for run_query.
    
    Args:
        user_input: User's query in any supported language
        chat_history: Previous messages
        user_language: User's preferred language (en, hi, es)
    
    Returns:
        Response in user's preferred language
    """
    try:
        print(f"\n[AURA Multilingual] Query: {user_input}")
        print(f"[AURA Multilingual] User language: {user_language}")
        
        detected_lang = detect_language(user_input)
        print(f"[AURA Multilingual] Detected language: {detected_lang}")

        if detected_lang != 'en':
            english_query = translate_text(user_input, 'en', detected_lang)
            print(f"[AURA Multilingual] Translated query: {english_query}")
        else:
            english_query = user_input
        
        search_query = prepare_search_query(user_input, detected_lang)
        print(f"[AURA Multilingual] Running base query...")
        
        base_response = run_query_base(english_query, chat_history)

        if not base_response or "Error" in base_response or "error" in base_response:
            return base_response
        
        if user_language == 'en':
            return base_response

        print(f"[AURA Multilingual] Generating response in {user_language}...")
        
        if not GEMINI_AVAILABLE:
            print("[AURA Multilingual] ⚠️  Gemini not available, returning English response")
            return base_response
        
        try:
            model = genai.GenerativeModel(GEMINI_MODEL)
            
            lang_name = SUPPORTED_LANGUAGES.get(user_language, {}).get('native', user_language)
            
            multilingual_prompt = f"""You are AURA, a health intelligence assistant.

The user asked (in {lang_name}): {user_input}

Here is the data and analysis in English:
{base_response}

YOUR TASK:
1. Translate and adapt this response to {lang_name}
2. Maintain all data, numbers, and dates exactly as they appear
3. Keep the same sections (📊 Health Data, 📓 Journal Entries, 💡 AI Insights, etc.)
4. Make the language natural and conversational in {lang_name}
5. Keep any English proper nouns (like month names, technical terms) as-is if they're clearer

Respond entirely in {lang_name}:"""
            
            response = model.generate_content(multilingual_prompt)
            multilingual_response = response.text.strip()
            
            if multilingual_response and len(multilingual_response) > 10:
                print(f"[AURA Multilingual] ✅ Response generated in {user_language}")
                return multilingual_response
            else:
                print(f"[AURA Multilingual] ⚠️  Response too short, returning English")
                return base_response
            
        except Exception as e:
            print(f"[AURA Multilingual] ⚠️  Translation error: {e}")
            return base_response
    
    except Exception as e:
        print(f"[AURA Multilingual] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return f"Sorry, I encountered an error: {str(e)}"

def search_journals_multilingual(query: str, date: str = None, user_language: str = 'en') -> str:
    """
    Search journals with cross-language support.
    Can search in Hindi for English journals and vice versa.
    """
    print(f"[Journal Search] Query language: {user_language}")
    
    if user_language != 'en':
        english_query = translate_text(query, 'en', user_language)
        print(f"[Journal Search] Searching with: {english_query}")
    else:
        english_query = query
    
    results = search_journals_realtime(english_query, date)
    
    return results

run_query = run_query_multilingual


if __name__ == "__main__":
    print("="*80)
    print("AURA MULTILINGUAL TEST")
    print("="*80)
    
    # Test English
    print("\n1. English Query:")
    result = run_query_multilingual("how was my sleep on april 17th?", user_language='en')
    print(result[:200] + "...")
    
    # Test Hindi
    print("\n2. Hindi Query:")
    result = run_query_multilingual("17 अप्रैल को मेरी नींद कैसी थी?", user_language='hi')
    print(result[:200] + "...")
    
    # Test Spanish
    print("\n3. Spanish Query:")
    result = run_query_multilingual("¿Cómo fue mi sueño el 17 de abril?", user_language='es')
    print(result[:200] + "...")
    
    print("\n" + "="*80)
