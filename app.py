
import streamlit as st
import sqlite3
import pandas as pd

from session_manager import (
    save_message, load_chat_history, clear_chat_history,
    save_journal_entry, get_journals,
    get_preference, set_preference,
)

st.set_page_config(
    page_title="AURA Health Intelligence",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }

  .stApp { background: #0a0e1a; color: #e2e8f0; }

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
    width: 8px; height: 8px;
    background: #22c55e;
    border-radius: 50%;
    animation: pulse 2s infinite;
    margin-right: 6px;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.5; transform: scale(1.3); }
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

  /* Status badge */
  .status-ok   { color: #22c55e; font-size: 0.78rem; }
  .status-warn { color: #f59e0b; font-size: 0.78rem; }
  .status-err  { color: #ef4444; font-size: 0.78rem; }

  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="⏳ Loading AURA intelligence engine…")
def _load_aura():
  
    try:
        import aura_tools as _at
        return _at, None
    except Exception as exc:
        return None, str(exc)


if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

if "user_name" not in st.session_state:
    st.session_state.user_name = get_preference("user_name", "User")


def safe_run_query(prompt: str, history: list) -> str:
    tools, load_error = _load_aura()
    if load_error or tools is None:
        return (
            f"Error - AURA intelligence engine failed to load:\n\n```\n{load_error}\n```\n\n"
            "Make sure all dependencies are installed and `db_manager.py` has been run."
        )
    try:
        return tools.run_query(prompt, chat_history=history)
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"[app.py] Unhandled error in run_query:\n{tb}")
        return (
            f" Error -An error occurred while processing your query:\n\n"
            f"**{type(exc).__name__}: {exc}**\n\n"
            "_Check the terminal for the full traceback._"
        )



def show_main_app():

    with st.sidebar:
        st.markdown(
            f"<div style='padding:12px 0;'>"
            f"<span class='pulse-dot'></span>"
            f"<span style='font-weight:600;color:#e2e8f0;'>Hello, {st.session_state.user_name}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        tools, load_error = _load_aura()
        if tools is not None:
            st.markdown("<span class='status-ok'>● Engine online</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='status-err'>● Engine error — check terminal</span>", unsafe_allow_html=True)

        st.divider()

        page = st.radio(
            "Navigate",
            ["💬 Chat with AURA", "📓 My Journals", "📊 Quick Stats"],
            label_visibility="collapsed",
        )

        st.divider()

        st.markdown(
            "<p style='color:#475569;font-size:0.8rem;font-weight:600;'>TRY ASKING</p>",
            unsafe_allow_html=True,
        )
        suggestions = [
            "Why was my heart rate high on April 12?",
            "How was my sleep last week?",
            "What caused my stress spike on April 14?",
            "Show my worst sleep days",
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
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save"):
                    set_preference("user_name", new_name)
                    st.session_state.user_name = new_name
                    st.session_state["show_settings"] = False
                    st.success("Settings saved!")
                    st.rerun()
            with col2:
                if st.button("Close"):
                    st.session_state["show_settings"] = False
                    st.rerun()

    if page == "💬 Chat with AURA":
        st.markdown("""
        <div class='aura-header'>
          <h2 style='margin:0;color:#e2e8f0;'>
            🫀 AURA
            <span style='color:#3b82f6;font-size:1rem;font-weight:400;'>Health Intelligence</span>
          </h2>
          <p style='margin:4px 0 0 0;color:#475569;font-size:0.85rem;'>
            Connecting your biometrics with your life story
          </p>
        </div>
        """, unsafe_allow_html=True)

        for msg in st.session_state.messages:
            avatar = "🫀" if msg["role"] == "assistant" else "👤"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

        prefill = st.session_state.pop("prefill", None)
        prompt  = st.chat_input("Ask AURA about your health…") or prefill

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_message("user", prompt)
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            history = [
                m for m in st.session_state.messages[:-1]
                if m["role"] in ("user", "assistant")
            ][-20:]

            with st.chat_message("assistant", avatar="🫀"):
                answer = None
                with st.spinner("🔍 Analysing biometrics and journals…"):
                    answer = safe_run_query(prompt, history)
                st.markdown(answer)

            st.session_state.messages.append({"role": "assistant", "content": answer})
            save_message("assistant", answer)

    elif page == "📓 My Journals":
        st.markdown("<h2 style='color:#e2e8f0;'>📓 My Journal</h2>", unsafe_allow_html=True)
        st.caption("Journal entries are stored locally and used by AURA to explain your health patterns.")

        with st.expander("✏️ Write a new entry", expanded=True):
            phase_options = [
                "Morning", "Afternoon", "Evening", "Night",
                "Post-workout", "Stressed", "Relaxed", "Other",
            ]
            phase      = st.selectbox("Phase / Context", phase_options)
            entry_text = st.text_area(
                "What's on your mind today?",
                placeholder=(
                    "e.g. Had a really stressful meeting at 2pm, "
                    "felt my heart racing afterwards…"
                ),
                height=120,
            )
            if st.button("💾 Save Entry", use_container_width=True):
                if entry_text.strip():
                    save_journal_entry(entry_text.strip(), phase)
                    st.success("Entry saved! AURA will use this for future insights.")
                    st.rerun()
                else:
                    st.warning("Please write something before saving.")

        st.divider()
        st.markdown("<h4 style='color:#94a3b8;'>Past Entries</h4>", unsafe_allow_html=True)
        journals = get_journals()
        if not journals:
            st.info("No journal entries yet. Write your first entry above!")
        else:
            for j in journals:
                st.markdown(
                    f"<div class='aura-card'>"
                    f"<div style='margin-bottom:6px;'>"
                    f"<span class='tag'>{j['timestamp'][:10]}</span>"
                    f"<span class='tag'>{j['phase'] or 'General'}</span>"
                    f"</div>"
                    f"<p style='margin:0;color:#cbd5e1;line-height:1.6;'>{j['entry']}</p>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    elif page == "📊 Quick Stats":
        st.markdown("<h2 style='color:#e2e8f0;'>📊 Quick Stats</h2>", unsafe_allow_html=True)
        st.caption("Live queries directly from your health database.")

        try:
            conn = sqlite3.connect("aura_health.db")
        except Exception as exc:
            st.error(f"Could not connect to aura_health.db: {exc}")
            st.info("Run `python db_manager.py` first to build the database.")
            return

        c1, c2, c3 = st.columns(3)

        with c1:
            try:
                row = pd.read_sql(
                    "SELECT AVG(Value) as avg, MAX(Value) as mx FROM heart_rate", conn
                )
                avg_hr = row["avg"][0]
                max_hr = row["mx"][0]
                if avg_hr is not None:
                    st.metric("❤️ Avg Heart Rate", f"{avg_hr:.0f} BPM", f"Max: {max_hr:.0f}")
                else:
                    st.metric("❤️ Avg Heart Rate", "No data")
            except Exception:
                st.metric("❤️ Avg Heart Rate", "No data")

        with c2:
            try:
                row = pd.read_sql(
                    "SELECT AVG(TotalSteps) as avg FROM daily_activity", conn
                )
                avg_steps = row["avg"][0]
                if avg_steps is not None:
                    st.metric("👟 Avg Daily Steps", f"{avg_steps:,.0f}")
                else:
                    st.metric("👟 Avg Daily Steps", "No data")
            except Exception:
                st.metric("👟 Avg Daily Steps", "No data")

        with c3:
            try:
                row = pd.read_sql(
                    "SELECT AVG(TotalMinutesAsleep) as avg FROM sleep_logs", conn
                )
                avg_min = row["avg"][0]
                if avg_min is not None:
                    st.metric("😴 Avg Sleep", f"{avg_min / 60:.1f} hrs")
                else:
                    st.metric("😴 Avg Sleep", "No data")
            except Exception:
                st.metric("😴 Avg Sleep", "No data")

        st.divider()
        st.markdown(
            "<h4 style='color:#94a3b8;'>Recent High Heart-Rate Events (HR > 100)</h4>",
            unsafe_allow_html=True,
        )
        try:
            df_hr = pd.read_sql(
                "SELECT Time, Value FROM heart_rate WHERE Value > 100 "
                "ORDER BY Value DESC LIMIT 10",
                conn,
            )
            if not df_hr.empty:
                st.dataframe(df_hr, use_container_width=True)
            else:
                st.info("No elevated HR events found.")
        except Exception as exc:
            st.warning(f"Could not load heart rate data: {exc}")
        st.divider()
        st.markdown(
            "<h4 style='color:#94a3b8;'>Recent Sleep Logs</h4>",
            unsafe_allow_html=True,
        )
        try:
            df_sleep = pd.read_sql(
                "SELECT SleepDay, "
                "ROUND(TotalMinutesAsleep / 60.0, 2) AS Hours_Asleep, "
                "ROUND(TotalTimeInBed / 60.0, 2)     AS Hours_In_Bed "
                "FROM sleep_logs "
                "ORDER BY SleepDay DESC LIMIT 10",
                conn,
            )
            if not df_sleep.empty:
                st.dataframe(df_sleep, use_container_width=True)
            else:
                st.info("No sleep data found.")
        except Exception as exc:
            st.warning(f"Could not load sleep data: {exc}")
        conn.close()

show_main_app()