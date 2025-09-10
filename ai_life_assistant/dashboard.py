# dashboard.py
import streamlit as st
import requests
import os
import time

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")

# ------------------ iOS-like theming ------------------
st.set_page_config(page_title="AI Life Assistant", page_icon="🟣", layout="centered")
st.markdown(
    """
    <style>
    .block-container { max-width: 980px !important; padding-top: 2.5rem; padding-bottom: 3rem; }
      :root {
        --bg: #0f0f10; /* deep charcoal */
        --card: #17181a; /* dark card */
        --primary: #7c5cff; /* iOS-style purple */
        --text: #f3f4f6; /* near white */
        --muted: #a1a1aa;
        --accent: #22d3ee; /* teal */
      }
      .stApp { background: radial-gradient(1200px 800px at 10% -10%, rgba(124,92,255,.2), transparent),
                               radial-gradient(1000px 600px at 110% 10%, rgba(34,211,238,.12), transparent),
                               var(--bg) !important; color: var(--text); }
      h1, h2, h3, h4 { color: var(--text); }
    .ios-card { background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02));
            border: 1px solid rgba(255,255,255,.08); border-radius: 20px; padding: 20px 22px; box-shadow: 0 12px 30px rgba(0,0,0,.35); margin: 18px 0 26px; }
      .pill { display:inline-block; padding:6px 12px; border-radius:999px; background:rgba(124,92,255,.15); color:#c8b6ff; font-weight:600; border:1px solid rgba(124,92,255,.25); }
    .chat-bubble { max-width: 80%; padding: 12px 16px; border-radius: 16px; margin: 10px 0; line-height: 1.6; }
      .user { background: rgba(124,92,255,.2); border: 1px solid rgba(124,92,255,.35); color: #e9e3ff; margin-left:auto; }
      .bot { background: rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); color:#f5f5f5; margin-right:auto; }
      .send-row button { border-radius: 12px !important; background: var(--primary) !important; color: white !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; margin-bottom: 14px; }
      .stTabs [data-baseweb="tab"] { background: rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.08); border-radius: 12px; padding: 10px 14px; color:#ddd; }
      .stTabs [aria-selected="true"] { background: linear-gradient(180deg, rgba(124,92,255,.25), rgba(124,92,255,.12)); color: #fff !important; border-color: rgba(124,92,255,.45); }
    textarea, .stTextInput input { background: rgba(255,255,255,.06) !important; color: #fff !important; border-radius: 12px !important; }
    [data-testid="stVerticalBlock"] > div { margin-bottom: 8px; }
    .section-title { margin-top: 6px; margin-bottom: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='pill'>🟣 AI Life Assistant</div>", unsafe_allow_html=True)
st.markdown("<h1 style='margin-top:8px'>Your everyday AI companion</h1>", unsafe_allow_html=True)

# ------------------ Session State for chat ------------------
SESSION_ID = "default"

def load_history():
    try:
        r = requests.get(f"{BASE_URL}/chat/history", params={"session_id": SESSION_ID}, timeout=5)
        return r.json().get("messages", [])
    except Exception:
        return []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history() or [
        {"role": "model", "content": "Hey! I’m here to help with planning, writing, and more. 😊"}
    ]
if "should_clear_input" not in st.session_state:
    st.session_state.should_clear_input = False

tab_chat, tab_sum, tab_plan, tab_rephrase, tab_quote = st.tabs(["Chat", "Summarize", "Planner", "Rephrase", "Quote"])

# ------------------ Chat Tab ------------------
with tab_chat:
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    chat_container = st.container()
    with chat_container:
        for m in st.session_state.chat_history:
            role = m.get("role", "model")
            bubble_class = "user" if role == "user" else "bot"
            avatar = "🧑🏻" if role == "user" else "🤖"
            st.markdown(
                f"<div style='display:flex;gap:8px;align-items:flex-start;{ 'justify-content:flex-end;' if role=='user' else ''}'>"
                f"<div>{'' if role=='user' else avatar}</div>"
                f"<div class='chat-bubble {bubble_class}'>{m.get('content','')}</div>"
                f"<div>{avatar if role=='user' else ''}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    cols = st.columns([1, 5, 1])
    with cols[1]:
        # Clear input before instantiating widget if flagged
        if st.session_state.get("should_clear_input"):
            st.session_state.chat_input = ""
            st.session_state.should_clear_input = False
        user_msg = st.text_input("Message", key="chat_input", placeholder="Type a message…", label_visibility="collapsed")
        send = st.button("Send", use_container_width=True)
    if send and user_msg.strip():
        message = user_msg.strip()
        st.session_state.chat_history.append({"role": "user", "content": message})
        reply = ""
        # Typing indicator + streaming
        with st.spinner("Assistant is typing…"):
            try:
                with requests.post(
                    f"{BASE_URL}/chat/stream",
                    json={"messages": st.session_state.chat_history, "session_id": SESSION_ID},
                    stream=True,
                    timeout=120,
                ) as resp:
                    resp.raise_for_status()
                    placeholder = st.empty()
                    for line in resp.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        reply += line
                        # Live-updating bubble
                        placeholder.markdown(
                            f"<div style='display:flex;gap:8px;align-items:flex-start;'>"
                            f"<div>🤖</div>"
                            f"<div class='chat-bubble bot'>{reply}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
            except Exception as e:
                # Fallback to non-streaming endpoint
                try:
                    res = requests.post(
                        f"{BASE_URL}/chat",
                        json={"messages": st.session_state.chat_history, "session_id": SESSION_ID},
                        timeout=60,
                    )
                    reply = res.json().get("reply", "") or reply
                except Exception as e2:
                    reply = reply or f"[Client error: {e2}]"
        if not reply:
            reply = "(No response)"
        st.session_state.chat_history.append({"role": "model", "content": reply})
        # Schedule clearing the input on next run
        st.session_state.should_clear_input = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ Summarizer ------------------
with tab_sum:
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    text = st.text_area("Enter text to summarize")
    if st.button("Summarize", key="sum_btn"):
        res = requests.post(f"{BASE_URL}/summarize", json={"text": text})
        st.success(res.json().get("summary", "No response"))
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ Planner ------------------
with tab_plan:
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    tasks = st.text_area("Tasks (comma separated)")
    if st.button("Generate Plan", key="plan_btn"):
        res = requests.post(f"{BASE_URL}/planner", json={"tasks": tasks})
        st.info(res.json().get("plan", ""))
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ Rephraser ------------------
with tab_rephrase:
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    txt = st.text_area("Text to rephrase")
    if st.button("Rephrase", key="re_btn"):
        res = requests.post(f"{BASE_URL}/rephrase", json={"text": txt})
        st.write(res.json().get("rephrased", ""))
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ Quote ------------------
with tab_quote:
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    mood = st.selectbox("Mood", ["Happy", "Sad", "Stressed", "Excited", "Tired"])
    if st.button("Get Quote", key="q_btn"):
        res = requests.post(f"{BASE_URL}/quote", json={"mood": mood})
        st.success(res.json().get("quote", ""))
    st.markdown("</div>", unsafe_allow_html=True)

