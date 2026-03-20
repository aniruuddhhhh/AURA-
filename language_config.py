
LANGUAGE_1 = 'ta'  # Tamil (change to 'hi', 'es', 'te', etc.)
LANGUAGE_2 = 'hi'  # Hindi (change to your 2nd language)

ALL_LANGUAGES = {
    # Always included
    'en': {
        'name': 'English',
        'native': 'English',
        'flag': '🇬🇧',
        'voice_code': 'en-US',
        'rtl': False,
    },
    
    # Indian Languages
    'ta': {
        'name': 'Tamil',
        'native': 'தமிழ்',
        'flag': '🇮🇳',
        'voice_code': 'ta-IN',
        'rtl': False,
    },
    'hi': {
        'name': 'Hindi',
        'native': 'हिन्दी',
        'flag': '🇮🇳',
        'voice_code': 'hi-IN',
        'rtl': False,
    },
    'te': {
        'name': 'Telugu',
        'native': 'తెలుగు',
        'flag': '🇮🇳',
        'voice_code': 'te-IN',
        'rtl': False,
    },
    'kn': {
        'name': 'Kannada',
        'native': 'ಕನ್ನಡ',
        'flag': '🇮🇳',
        'voice_code': 'kn-IN',
        'rtl': False,
    },
    'ml': {
        'name': 'Malayalam',
        'native': 'മലയാളം',
        'flag': '🇮🇳',
        'voice_code': 'ml-IN',
        'rtl': False,
    },
    'bn': {
        'name': 'Bengali',
        'native': 'বাংলা',
        'flag': '🇮🇳',
        'voice_code': 'bn-IN',
        'rtl': False,
    },
    'mr': {
        'name': 'Marathi',
        'native': 'मराठी',
        'flag': '🇮🇳',
        'voice_code': 'mr-IN',
        'rtl': False,
    },
    
    # International Languages
    'es': {
        'name': 'Spanish',
        'native': 'Español',
        'flag': '🇪🇸',
        'voice_code': 'es-ES',
        'rtl': False,
    },
    'zh': {
        'name': 'Chinese',
        'native': '中文',
        'flag': '🇨🇳',
        'voice_code': 'zh-CN',
        'rtl': False,
    },
    'ar': {
        'name': 'Arabic',
        'native': 'العربية',
        'flag': '🇸🇦',
        'voice_code': 'ar-SA',
        'rtl': True,  # Right-to-left
    },
    'fr': {
        'name': 'French',
        'native': 'Français',
        'flag': '🇫🇷',
        'voice_code': 'fr-FR',
        'rtl': False,
    },
    'de': {
        'name': 'German',
        'native': 'Deutsch',
        'flag': '🇩🇪',
        'voice_code': 'de-DE',
        'rtl': False,
    },
    'pt': {
        'name': 'Portuguese',
        'native': 'Português',
        'flag': '🇵🇹',
        'voice_code': 'pt-PT',
        'rtl': False,
    },
}

SUPPORTED_LANGUAGES = {
    'en': ALL_LANGUAGES['en'],  # English always included
}

if LANGUAGE_1 in ALL_LANGUAGES and LANGUAGE_1 != 'en':
    SUPPORTED_LANGUAGES[LANGUAGE_1] = ALL_LANGUAGES[LANGUAGE_1]

if LANGUAGE_2 in ALL_LANGUAGES and LANGUAGE_2 != 'en' and LANGUAGE_2 != LANGUAGE_1:
    SUPPORTED_LANGUAGES[LANGUAGE_2] = ALL_LANGUAGES[LANGUAGE_2]

DEFAULT_LANGUAGE = 'en'

VOICE_LANGUAGE_CODES = {
    code: lang['voice_code'] 
    for code, lang in SUPPORTED_LANGUAGES.items()
}


UI_TRANSLATIONS = {
    'greeting': {
        'en': 'Hello',
        'ta': 'வணக்கம்',
        'hi': 'नमस्ते',
        'te': 'నమస్కారం',
        'kn': 'ನಮಸ್ಕಾರ',
        'ml': 'നമസ്കാരം',
        'bn': 'নমস্কার',
        'mr': 'नमस्कार',
        'es': 'Hola',
        'zh': '你好',
        'ar': 'مرحبا',
        'fr': 'Bonjour',
        'de': 'Hallo',
        'pt': 'Olá',
    },
    'navigate': {
        'en': 'Navigate',
        'ta': 'செல்லவும்',
        'hi': 'नेविगेट करें',
        'te': 'నావిగేట్',
        'es': 'Navegar',
        'zh': '导航',
        'ar': 'التنقل',
        'fr': 'Naviguer',
    },
    'chat': {
        'en': '💬 Chat with AURA',
        'ta': '💬 AURA உடன் அரட்டை',
        'hi': '💬 AURA से बात करें',
        'te': '💬 AURA తో చాట్',
        'es': '💬 Chatear con AURA',
        'zh': '💬 与AURA聊天',
        'ar': '💬 الدردشة مع AURA',
        'fr': '💬 Discuter avec AURA',
    },
    'journals': {
        'en': '📓 My Journals',
        'ta': '📓 என் நாட்குறிப்பு',
        'hi': '📓 मेरी डायरी',
        'te': '📓 నా జర్నల్స్',
        'es': '📓 Mis Diarios',
        'zh': '📓 我的日记',
        'ar': '📓 يومياتي',
        'fr': '📓 Mes Journaux',
    },
    'stats': {
        'en': '📊 Quick Stats',
        'ta': '📊 விரைவு புள்ளிவிவரங்கள்',
        'hi': '📊 त्वरित आँकड़े',
        'te': '📊 శీఘ్ర గణాంకాలు',
        'es': '📊 Estadísticas',
        'zh': '📊 快速统计',
        'ar': '📊 إحصائيات سريعة',
        'fr': '📊 Statistiques',
    },
    'try_asking': {
        'en': 'TRY ASKING',
        'ta': 'கேட்க முயற்சிக்கவும்',
        'hi': 'पूछने की कोशिश करें',
        'te': 'అడగడానికి ప్రయత్నించండి',
        'es': 'PRUEBA PREGUNTANDO',
        'zh': '尝试询问',
        'ar': 'حاول السؤال',
        'fr': 'ESSAYEZ DE DEMANDER',
    },
    'clear_chat': {
        'en': '🗑️ Clear Chat',
        'ta': '🗑️ அரட்டையை அழி',
        'hi': '🗑️ चैट साफ़ करें',
        'te': '🗑️ చాట్ క్లియర్',
        'es': '🗑️ Limpiar Chat',
        'zh': '🗑️ 清除聊天',
        'ar': '🗑️ مسح الدردشة',
        'fr': '🗑️ Effacer le Chat',
    },
    'settings': {
        'en': '⚙️ Settings',
        'ta': '⚙️ அமைப்புகள்',
        'hi': '⚙️ सेटिंग्स',
        'te': '⚙️ సెట్టింగ్స్',
        'es': '⚙️ Configuración',
        'zh': '⚙️ 设置',
        'ar': '⚙️ الإعدادات',
        'fr': '⚙️ Paramètres',
    },
    'write_entry': {
        'en': 'Write a new entry',
        'ta': 'புதிய குறிப்பு எழுதவும்',
        'hi': 'नई प्रविष्टि लिखें',
        'te': 'కొత్త ఎంట్రీ రాయండి',
        'es': 'Escribir nueva entrada',
        'zh': '写新条目',
        'ar': 'اكتب إدخال جديد',
        'fr': 'Écrire une nouvelle entrée',
    },
    'save_entry': {
        'en': '💾 Save Entry',
        'ta': '💾 சேமி',
        'hi': '💾 सहेजें',
        'te': '💾 సేవ్',
        'es': '💾 Guardar',
        'zh': '💾 保存',
        'ar': '💾 حفظ',
        'fr': '💾 Enregistrer',
    },
    'placeholder_journal': {
        'en': "What's on your mind today?",
        'ta': 'இன்று உங்கள் மனதில் என்ன உள்ளது?',
        'hi': 'आज आपके मन में क्या है?',
        'te': 'ఈరోజు మీ మనస్సులో ఏమి ఉంది?',
        'es': '¿Qué tienes en mente hoy?',
        'zh': '今天你在想什么？',
        'ar': 'ما الذي يدور في ذهنك اليوم؟',
        'fr': "Qu'avez-vous en tête aujourd'hui?",
    },
    'chat_placeholder': {
        'en': 'Ask AURA about your health...',
        'ta': 'உங்கள் ஆரோக்கியம் பற்றி AURA-விடம் கேளுங்கள்...',
        'hi': 'अपने स्वास्थ्य के बारे में AURA से पूछें...',
        'te': 'మీ ఆరోగ్యం గురించి AURA ని అడగండి...',
        'es': 'Pregúntale a AURA sobre tu salud...',
        'zh': '向AURA询问您的健康状况...',
        'ar': 'اسأل AURA عن صحتك...',
        'fr': 'Demandez à AURA sur votre santé...',
    },
}

SAMPLE_QUESTIONS = {
    'en': [
        "Why was my heart rate high on April 12?",
        "How was my sleep last week?",
        "What caused my stress spike?",
    ],
    'ta': [
        "ஏப்ரல் 12 அன்று என் இதயத் துடிப்பு ஏன் அதிகமாக இருந்தது?",
        "கடந்த வாரம் என் தூக்கம் எப்படி இருந்தது?",
        "என் செயல்பாடு எப்படி இருந்தது?",
    ],
    'hi': [
        "12 अप्रैल को मेरी हृदय गति अधिक क्यों थी?",
        "पिछले सप्ताह मेरी नींद कैसी थी?",
        "मेरी गतिविधि कैसी रही?",
    ],
    'te': [
        "ఏప్రిల్ 12న నా హృదయ స్పందన రేటు ఎందుకు ఎక్కువగా ఉంది?",
        "గత వారం నా నిద్ర ఎలా ఉంది?",
        "నా కార్యాచరణ ఎలా ఉంది?",
    ],
    'es': [
        "¿Por qué mi frecuencia cardíaca fue alta el 12 de abril?",
        "¿Cómo fue mi sueño la semana pasada?",
        "¿Cuál fue mi actividad?",
    ],
    'zh': [
        "为什么4月12日我的心率很高？",
        "上周我睡得怎么样？",
        "我的活动怎么样？",
    ],
    'ar': [
        "لماذا كان معدل ضربات قلبي مرتفعًا في 12 أبريل؟",
        "كيف كان نومي الأسبوع الماضي؟",
        "كيف كان نشاطي؟",
    ],
    'fr': [
        "Pourquoi ma fréquence cardiaque était-elle élevée le 12 avril?",
        "Comment était mon sommeil la semaine dernière?",
        "Quelle était mon activité?",
    ],
}

if __name__ == "__main__":
    print("="*80)
    print("🌍 AURA LANGUAGE CONFIGURATION")
    print("="*80)
    
    print(f"\n📌 Active Languages ({len(SUPPORTED_LANGUAGES)}):")
    for code, lang in SUPPORTED_LANGUAGES.items():
        print(f"   {lang['flag']} {lang['native']} ({code}) - Voice: {lang['voice_code']}")
    
    print(f"\n🔧 To change languages:")
    print(f"   1. Edit language_config.py")
    print(f"   2. Change LANGUAGE_1 = '{LANGUAGE_1}' to your preferred code")
    print(f"   3. Change LANGUAGE_2 = '{LANGUAGE_2}' to your preferred code")
    print(f"   4. Save and restart the app")
    
    print(f"\n📋 Available Languages:")
    for code, lang in sorted(ALL_LANGUAGES.items()):
        status = "✅ ACTIVE" if code in SUPPORTED_LANGUAGES else "⚪ Available"
        print(f"   {status} - {code}: {lang['flag']} {lang['native']} ({lang['name']})")
    
    print("\n" + "="*80)
