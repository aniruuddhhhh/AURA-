import streamlit as st
from datetime import datetime

from session_manager_realtime import (
    save_message, load_chat_history, clear_chat_history,
    save_journal_entry, get_journals,
    get_preference, set_preference,
)
from multilingual_support import (
    SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE,
    get_language_display, get_all_languages,
    detect_language, translate_text,
    store_journal_multilingual, get_voice_language_code,
    get_ui_text, get_sample_questions,
)

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

try:
    from aura_tools_multilingual import run_query_multilingual
    run_query = run_query_multilingual
except ImportError:
    
    from aura_tools_gemini import run_query
    print("⚠️  Using non-multilingual aura_tools. Install aura_tools_multilingual.py for full support.")

try:
    from audio_recorder_streamlit import audio_recorder
    import speech_recognition as sr
    VOICE_ENABLED = True
except ImportError:
    VOICE_ENABLED = False

st.set_page_config(
    page_title="AURA Health Intelligence",
    page_icon="🏥",  # Hospital emoji - more widely supported
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Noto+Sans:wght@400;500&family=Noto+Sans+Devanagari:wght@400;500&display=swap');

  html, body, [class*="css"] {
    font-family: 'Space Grotesk', 'Noto Sans', 'Noto Sans Devanagari', sans-serif;
  }

  .stApp {
    background: #0a0e1a;
    color: #e2e8f0;
  }

  [data-testid="stSidebar"] {
    background: #0f1729 !important;
    border-right: 1px solid #1e2d4a;
  }

  [data-testid="stChatMessage"] {
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    margin-bottom: 8px;
  }

  [data-testid="stChatInput"] textarea {
    background: #111827 !important;
    border: 1px solid #2d4a7a !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
  }

  .stButton > button {
    background: linear-gradient(135deg, #1a3a6b, #2d6aad);
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
    transition: all 0.2s;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, #2d6aad, #3d8fd4);
    transform: translateY(-1px);
  }

  .stTextInput > div > div > input,
  .stTextArea > div > div > textarea {
    background: #111827 !important;
    border: 1px solid #1e2d4a !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-family: 'Space Grotesk', 'Noto Sans', 'Noto Sans Devanagari', sans-serif !important;
  }

  .language-badge {
    display: inline-block;
    background: linear-gradient(135deg, #1e3a8a, #3b82f6);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    margin: 2px;
    font-weight: 500;
  }

  .aura-card {
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
  }

  .pulse-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #22c55e;
    border-radius: 50%;
    animation: pulse 2s infinite;
    margin-right: 6px;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.3); }
  }

  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

if "user_name" not in st.session_state:
    st.session_state.user_name = get_preference("user_name", "User")

if "user_language" not in st.session_state:
    st.session_state.user_language = get_preference("user_language", DEFAULT_LANGUAGE)

def show_main_app():
    with st.sidebar:
        st.markdown("### 🌍 Language / भाषा / Idioma")
        
        lang_options = get_all_languages()
        lang_labels = [display for code, display in lang_options]
        lang_codes = [code for code, display in lang_options]
        
        current_index = lang_codes.index(st.session_state.user_language) if st.session_state.user_language in lang_codes else 0
        
        selected_display = st.selectbox(
            "Select Language",
            lang_labels,
            index=current_index,
            label_visibility="collapsed"
        )
        
        selected_code = lang_codes[lang_labels.index(selected_display)]
        if selected_code != st.session_state.user_language:
            st.session_state.user_language = selected_code
            set_preference("user_language", selected_code)
            st.rerun()
        
        st.divider()
        
        greeting = get_ui_text('greeting', st.session_state.user_language)
        st.markdown(f"""
        <div style='padding: 12px 0;'>
          <span class='pulse-dot'></span>
          <span style='font-weight:600; color:#e2e8f0;'>{greeting}, {st.session_state.user_name}</span>
        </div>
        <div style='padding: 4px 0 12px 20px;'>
          <span class='language-badge'>{selected_display}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        page = st.radio(
            get_ui_text('navigate', st.session_state.user_language),
            [
                get_ui_text('chat', st.session_state.user_language),
                get_ui_text('journals', st.session_state.user_language),
                get_ui_text('stats', st.session_state.user_language)
            ],
            label_visibility="collapsed",
        )
        
        st.divider()
        
        st.markdown(f"<p style='color:#475569; font-size:0.8rem; font-weight:600;'>{get_ui_text('try_asking', st.session_state.user_language)}</p>",
                    unsafe_allow_html=True)
        
        suggestions = get_sample_questions(st.session_state.user_language)
        
        for s in suggestions:
            if st.button(s, key=f"sug_{s}", use_container_width=True):
                st.session_state["prefill"] = s
                st.rerun()
        
        st.divider()
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(get_ui_text('clear_chat', st.session_state.user_language), use_container_width=True):
                clear_chat_history()
                st.session_state.messages = []
                st.rerun()
        with col_b:
            if st.button(get_ui_text('settings', st.session_state.user_language), use_container_width=True):
                st.session_state["show_settings"] = True
                st.rerun()

    if st.session_state.get("show_settings", False):
        with st.expander("⚙️ " + get_ui_text('settings', st.session_state.user_language), expanded=True):
            new_name = st.text_input("Your name", value=st.session_state.user_name)
            if st.button("Save"):
                set_preference("user_name", new_name)
                st.session_state.user_name = new_name
                st.session_state["show_settings"] = False
                st.success("Settings saved!")
                st.rerun()
            if st.button("Close"):
                st.session_state["show_settings"] = False
                st.rerun()

    if page == get_ui_text('chat', st.session_state.user_language):
        header_html = """
        <div style='background: linear-gradient(135deg, #0a1628 0%, #0f2040 100%); border-bottom: 1px solid #1e2d4a; padding: 20px 0 10px 0; margin-bottom: 20px;'>
          <h2 style='margin:0; color:#e2e8f0;'>🌍 AURA <span style='color:#3b82f6; font-size:1rem; font-weight:400;'>Multilingual Health Intelligence</span></h2>
          <p style='margin:4px 0 0 0; color:#475569; font-size:0.85rem;'>
            English • हिन्दी • Español
          </p>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prefill = st.session_state.pop("prefill", None)
        prompt = st.chat_input(get_ui_text('chat_placeholder', st.session_state.user_language)) or prefill

        if prompt:
            detected_lang = detect_language(prompt)
            if detected_lang != st.session_state.user_language:
                print(f"[Language] Detected: {detected_lang}, User pref: {st.session_state.user_language}")
            
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_message("user", prompt)
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    try:
                        history = [m for m in st.session_state.messages[:-1]][-20:]
                        answer = run_query(
                            prompt, 
                            chat_history=history,
                            user_language=st.session_state.user_language
                        )
                    except TypeError:
                        answer = run_query(prompt, chat_history=history)
                    except Exception as e:
                        answer = f"⚠️ Error: {e}"

                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                save_message("assistant", answer)

    elif page == get_ui_text('journals', st.session_state.user_language):
        st.markdown(f"<h2 style='color:#e2e8f0;'>{get_ui_text('journals', st.session_state.user_language)}</h2>", unsafe_allow_html=True)
        
        with st.expander("✏️ " + get_ui_text('write_entry', st.session_state.user_language), expanded=True):
            entry_text = st.text_area(
                get_ui_text('placeholder_journal', st.session_state.user_language),
                placeholder=get_ui_text('placeholder_journal', st.session_state.user_language),
                height=120,
            )
            
            if VOICE_ENABLED:
                st.markdown("**🎤 Or record voice:**")
                audio_bytes = audio_recorder(
                    text="",
                    recording_color="#e74c3c",
                    neutral_color="#6c757d",
                    icon_name="microphone",
                    icon_size="2x",
                )
                
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/wav")
                    
                    try:
                        import io
                        from pydub import AudioSegment
                        
                        audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))
                        audio.export("temp.wav", format="wav")
                        
                        recognizer = sr.Recognizer()
                        with sr.AudioFile("temp.wav") as source:
                            audio_data = recognizer.record(source)
                            
                            lang_code = get_voice_language_code(st.session_state.user_language)
                            text = recognizer.recognize_google(audio_data, language=lang_code)
                            
                            entry_text = text
                            st.success(f"🎤 Transcribed: {text}")
                    except Exception as e:
                        st.error(f"Transcription error: {e}")
            
            if st.button(get_ui_text('save_entry', st.session_state.user_language), use_container_width=True):
                if entry_text.strip():
                    original, english = store_journal_multilingual(
                        entry_text.strip(), 
                        st.session_state.user_language
                    )
                    
                    phase = f"{get_language_display(st.session_state.user_language)}"
                    save_journal_entry(original, phase)
                    
                    st.success("✅ Entry saved!")
                    st.rerun()
                else:
                    st.warning("Please write something before saving.")

        st.divider()
        st.markdown("<h4 style='color:#94a3b8;'>Past Entries</h4>", unsafe_allow_html=True)
        journals = get_journals()
        if not journals:
            st.info("No journal entries yet.")
        else:
            for j in journals:
                lang_badge = f"<span class='language-badge'>{j['phase'] or 'General'}</span>" if j['phase'] else ""
                st.markdown(f"""
                <div class='aura-card'>
                  <div style='margin-bottom:6px;'>
                    <span style='color:#64748b; font-size:0.85rem;'>{j['timestamp'][:10]}</span>
                    {lang_badge}
                  </div>
                  <p style='margin:0; color:#cbd5e1; line-height:1.6;'>{j['entry']}</p>
                </div>
                """, unsafe_allow_html=True)

    elif page == get_ui_text('stats', st.session_state.user_language):
        st.markdown(f"<h2 style='color:#e2e8f0;'>{get_ui_text('stats', st.session_state.user_language)}</h2>", unsafe_allow_html=True)
        
        import sqlite3, pandas as pd
        try:
            conn = sqlite3.connect("aura_health.db")
            
            c1, c2, c3 = st.columns(3)
            
            with c1:
                try:
                    row = pd.read_sql("SELECT AVG(Value) as avg, MAX(Value) as mx FROM heart_rate", conn)
                    st.metric("❤️ Avg Heart Rate", f"{row['avg'][0]:.0f} BPM", f"Max: {row['mx'][0]:.0f}")
                except:
                    st.metric("❤️ Avg Heart Rate", "No data")
            
            with c2:
                try:
                    row = pd.read_sql("SELECT AVG(TotalSteps) as avg FROM daily_activity", conn)
                    st.metric("👟 Avg Daily Steps", f"{row['avg'][0]:,.0f}")
                except:
                    st.metric("👟 Avg Daily Steps", "No data")
            
            with c3:
                try:
                    row = pd.read_sql("SELECT AVG(TotalMinutesAsleep) as avg FROM sleep_logs", conn)
                    hrs = row['avg'][0] / 60
                    st.metric("😴 Avg Sleep", f"{hrs:.1f} hrs")
                except:
                    st.metric("😴 Avg Sleep", "No data")
            
            conn.close()
        except Exception as e:
            st.error(f"Database error: {e}")

show_main_app()
