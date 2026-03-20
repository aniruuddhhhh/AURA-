
import streamlit as st
from audio_recorder_streamlit import audio_recorder

from session_manager_realtime import (
    save_message, load_chat_history, clear_chat_history,
    save_journal_entry, get_journals, get_todays_journals,
    get_preference, set_preference, reindex_unindexed_entries,
)
from aura_tools_gemini import run_query  # ← Using Gemini version!

try:
    from voice_processor import transcribe_audio, get_available_backends
    VOICE_ENABLED = True
except ImportError:
    VOICE_ENABLED = False

st.set_page_config(
    page_title="AURA Ultimate (Gemini)",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
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
    font-family: 'Space Grotesk', sans-serif !important;
  }

  .aura-card {
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
  }

  .aura-header {
    background: linear-gradient(135deg, #0a1628 0%, #0f2040 100%);
    border-bottom: 1px solid #1e2d4a;
    padding: 20px 0 10px 0;
    margin-bottom: 20px;
  }

  .pulse-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #4285f4;
    border-radius: 50%;
    animation: pulse 2s infinite;
    margin-right: 6px;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.3); }
  }

  .tag {
    display: inline-block;
    background: #1e2d4a;
    color: #7dd3fc;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    margin: 2px;
    font-family: 'JetBrains Mono', monospace;
  }

  .realtime-badge {
    background: #10b981;
    color: #d1fae5;
    font-weight: 600;
  }

  .voice-badge {
    background: #dc2626;
    color: #fecaca;
    font-weight: 600;
  }

  .gemini-badge {
    background: #4285f4;
    color: #dbeafe;
    font-weight: 600;
  }

  .indexed-badge {
    background: #3b82f6;
    color: #dbeafe;
  }

  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

if "user_name" not in st.session_state:
    st.session_state.user_name = get_preference("user_name", "User")

if "voice_backend" not in st.session_state and VOICE_ENABLED:
    st.session_state.voice_backend = get_preference("voice_backend", "google")

def show_main_app():

    with st.sidebar:
        st.markdown(f"""
        <div style='padding: 12px 0;'>
          <span class='pulse-dot'></span>
          <span style='font-weight:600; color:#e2e8f0;'>Hello, {st.session_state.user_name}</span>
        </div>
        <div style='padding: 4px 0 12px 20px;'>
          <span style='font-size:0.7rem; color:#4285f4;'>🤖 Gemini 2.5</span>
          <span style='font-size:0.7rem; color:#10b981; margin-left:10px;'>⚡ Real-Time</span>
          {f"<span style='font-size:0.7rem; color:#dc2626; margin-left:10px;'>🎤 Voice</span>" if VOICE_ENABLED else ""}
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        pages = ["💬 Chat with AURA", "📓 My Journals", "📊 Quick Stats"]
        if VOICE_ENABLED:
            pages.append("🎤 Voice Settings")
        
        page = st.radio("Navigate", pages, label_visibility="collapsed")

        st.divider()
        st.markdown("<p style='color:#475569; font-size:0.8rem; font-weight:600;'>TRY ASKING</p>",
                    unsafe_allow_html=True)
        suggestions = [
            "What did I journal today?",
            "When did I see sunrise?",
            "Show my worst sleep days",
            "What was my heart rate yesterday?",
        ]
        for s in suggestions:
            if st.button(s, key=f"sug_{s}", use_container_width=True):
                st.session_state["prefill"] = s
                st.rerun()

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                clear_chat_history()
                st.session_state.messages = []
                st.rerun()
        with col_b:
            if st.button("⚙️ Settings", use_container_width=True):
                st.session_state["show_settings"] = True
                st.rerun()

    if st.session_state.get("show_settings", False):
        with st.expander("⚙️ Settings", expanded=True):
            new_name = st.text_input("Your name", value=st.session_state.user_name)
            
            st.divider()
            st.markdown("**🔄 Reindex Journals**")
            st.caption("If entries aren't showing up in search, try reindexing")
            if st.button("🔄 Reindex Unindexed Entries"):
                count = reindex_unindexed_entries()
                st.success(f"Reindexed {count} entries!")
            
            st.divider()
            
            if st.button("Save"):
                set_preference("user_name", new_name)
                st.session_state.user_name = new_name
                st.session_state["show_settings"] = False
                st.success("Settings saved!")
                st.rerun()
            if st.button("Close"):
                st.session_state["show_settings"] = False
                st.rerun()

    if page == "💬 Chat with AURA":
        st.markdown("""
        <div class='aura-header'>
          <h2 style='margin:0; color:#e2e8f0;'>🤖 AURA Gemini 2.5 <span style='color:#4285f4; font-size:1rem; font-weight:400;'>AI Insights • Real-Time • Voice</span></h2>
          <p style='margin:4px 0 0 0; color:#475569; font-size:0.85rem;'>
            Powered by Google Gemini 2.5 Flash (Latest) • AI-powered health insights • Instant journal retrieval
          </p>
        </div>
        """, unsafe_allow_html=True)

        # chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])

        prefill = st.session_state.pop("prefill", None)

        prompt = st.chat_input("Ask AURA about your health...") or prefill

        if prompt:
            # Show user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_message("user", prompt)
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("🤖 Gemini analyzing your health data..."):
                    try:
                        history = [
                            m for m in st.session_state.messages[:-1]
                            if m["role"] in ("user", "assistant")
                        ][-20:]
                        answer = run_query(prompt, chat_history=history)
                    except Exception as e:
                        answer = f"⚠️ AURA encountered an error: {e}"

                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                save_message("assistant", answer)

    elif page == "📓 My Journals":
        st.markdown("<h2 style='color:#e2e8f0;'>📓 My Journal (Real-Time + Voice)</h2>", unsafe_allow_html=True)
        st.caption("Entries are instantly searchable • Voice entries supported • Powered by Gemini")

        with st.expander("✏️ Write a new entry", expanded=True):
            if VOICE_ENABLED:
                tab1, tab2 = st.tabs(["✍️ Text Entry", "🎤 Voice Entry"])
            else:
                tab1 = st.container()
                tab2 = None
            
            with (tab1 if VOICE_ENABLED else st.container()):
                phase_options = ["Morning", "Afternoon", "Evening", "Night", "Post-workout", "Stressed", "Relaxed", "Other"]
                phase = st.selectbox("Phase / Context", phase_options, key="text_phase")
                entry_text = st.text_area(
                    "What's on your mind today?",
                    placeholder="e.g. Had a really stressful meeting at 2pm, felt my heart racing afterwards...",
                    height=120,
                    key="text_entry"
                )
                if st.button("💾 Save Entry (Instant Search)", use_container_width=True):
                    if entry_text.strip():
                        save_journal_entry(entry_text.strip(), phase)
                        st.success("✅ Entry saved and indexed! Instantly searchable.")
                        st.rerun()
                    else:
                        st.warning("Please write something before saving.")
            
            if VOICE_ENABLED and tab2:
                with tab2:
                    st.markdown("🎤 **Record your journal entry**")
                    st.caption("Click the microphone button below to start recording")
                    
                    phase_voice = st.selectbox("Phase / Context", phase_options, key="voice_phase")
                    
                    audio_bytes = audio_recorder(
                        text="",
                        recording_color="#dc2626",
                        neutral_color="#475569",
                        icon_name="microphone",
                        icon_size="2x",
                    )
                    
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/wav")
                        
                        if st.button("📝 Transcribe & Save (Instant Search)", use_container_width=True, type="primary"):
                            with st.spinner("🎤 Transcribing your voice..."):
                                transcription, error = transcribe_audio(
                                    audio_bytes, 
                                    backend=st.session_state.voice_backend
                                )
                                
                                if transcription:
                                    st.success("✅ Transcription complete!")
                                    st.markdown("**Transcribed text:**")
                                    st.info(transcription)
                                    
                                    save_journal_entry(
                                        f"🎤 [Voice Entry] {transcription}", 
                                        phase_voice
                                    )
                                    st.success("✅ Voice entry saved and indexed! Instantly searchable.")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Transcription failed: {error}")
                                    st.info("Try speaking more clearly or check your voice settings.")

        st.divider()
        
        st.markdown("<h4 style='color:#10b981;'>⚡ Today's Entries</h4>", unsafe_allow_html=True)
        todays_journals = get_todays_journals()
        
        if todays_journals:
            for j in todays_journals:
                indexed_status = "✅ Indexed" if j.get('indexed') else "⏳ Pending"
                is_voice = "🎤" in j['entry']
                
                with st.container():
                    st.markdown(f"""
                    <div class='aura-card'>
                      <div style='margin-bottom:6px;'>
                        <span class='realtime-badge'>TODAY</span>
                        <span class='tag'>{j['timestamp'][11:19]}</span>
                        <span class='tag'>{j['phase'] or 'General'}</span>
                        {"<span class='voice-badge'>VOICE</span>" if is_voice else ""}
                        <span class='gemini-badge'>GEMINI</span>
                        <span class='tag'>{indexed_status}</span>
                      </div>
                      <p style='margin:0; color:#cbd5e1; line-height:1.6;'>{j['entry']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No entries today yet. Write your first entry above!")
        
        st.divider()
        
        st.markdown("<h4 style='color:#94a3b8;'>Past Entries</h4>", unsafe_allow_html=True)
        journals = get_journals(limit=20)
        
        if journals:
            for j in journals:
                if j['timestamp'][:10] == (todays_journals[0]['timestamp'][:10] if todays_journals else ''):
                    continue
                
                indexed_status = "✅" if j.get('indexed') else "⏳"
                is_voice = "🎤" in j['entry']
                
                with st.container():
                    st.markdown(f"""
                    <div class='aura-card'>
                      <div style='margin-bottom:6px;'>
                        <span class='tag'>{j['timestamp'][:10]}</span>
                        <span class='tag'>{j['phase'] or 'General'}</span>
                        {"<span class='voice-badge'>VOICE</span>" if is_voice else ""}
                        <span class='tag'>{indexed_status}</span>
                      </div>
                      <p style='margin:0; color:#cbd5e1; line-height:1.6;'>{j['entry']}</p>
                    </div>
                    """, unsafe_allow_html=True)

    elif page == "📊 Quick Stats":
        st.markdown("<h2 style='color:#e2e8f0;'>📊 Quick Stats</h2>", unsafe_allow_html=True)
        st.caption("Live queries powered by Gemini AI")

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

            st.divider()

            todays_count = len(get_todays_journals())
            voice_count = len([j for j in get_todays_journals() if "🎤" in j['entry']])
            st.metric("📓 Journal Entries Today", todays_count, f"🎤 {voice_count} voice")

            conn.close()
        except Exception as e:
            st.error(f"Could not connect to database: {e}")

    elif page == "🎤 Voice Settings" and VOICE_ENABLED:
        st.markdown("<h2 style='color:#e2e8f0;'>🎤 Voice Settings</h2>", unsafe_allow_html=True)
        st.caption("Configure speech-to-text for voice journaling")
        
        backends = get_available_backends()
        
        st.markdown("### Available Speech-to-Text Backends")
        
        for backend in backends:
            with st.expander(f"{backend['display_name']} {'✅' if backend['available'] else '❌'}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Quality:** {backend['quality']}")
                    st.markdown(f"**Speed:** {backend['speed']}")
                
                with col2:
                    st.markdown(f"**Cost:** {backend['cost']}")
                    st.markdown(f"**Requires:** {backend['requires']}")
                
                if backend['available']:
                    if st.button(f"Use {backend['display_name']}", key=f"use_{backend['name']}"):
                        st.session_state.voice_backend = backend['name']
                        set_preference("voice_backend", backend['name'])
                        st.success(f"Switched to {backend['display_name']}")
                        st.rerun()
                else:
                    st.warning(f"Not available. {backend['requires']}")
        
        st.divider()
        
        current = st.session_state.voice_backend
        current_backend = next((b for b in backends if b['name'] == current), None)
        
        if current_backend:
            st.success(f"**Current Backend:** {current_backend['display_name']}")


if not VOICE_ENABLED:
    st.info("💡 Voice journaling not installed. Install with: pip install -r voice_requirements.txt")

show_main_app()
