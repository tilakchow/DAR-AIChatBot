"""
DAR — Luxury Property AI Advisor · Streamlit Application.
Ultra-premium real estate client advisory powered by DarGlobal & Wasalt RAG pipeline.
"""

import os
import sys
import time
from typing import Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath('.'))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# Automatically inject Streamlit Cloud secrets into os.environ if present
if hasattr(st, "secrets"):
    try:
        for k, v in st.secrets.items():
            if isinstance(v, str) and k not in os.environ:
                os.environ[k] = v
    except Exception:
        pass

from src.rag.retriever import HybridRetriever
from src.rag.prompt import SYSTEM_PROMPT, format_context_prompt
from src.rag.openrouter_client import OpenRouterClient, OpenRouterError
from src.rag.guardrails import validate_user_input, GuardrailViolation, RATE_LIMITER, ANSWER_CACHE
from src.rag.schema import clean_answer_text

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="DAR — Luxury Property AI Advisor",
    page_icon="🏛️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# 2. Centralized Production-Grade Custom CSS (Obsidian & Champagne Gold Theme)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* =========================================================================
       GOOGLE FONTS (Cinzel for luxury serif titles, Plus Jakarta Sans for UI)
       ========================================================================= */
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700;800&family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

    /* =========================================================================
       CLEAN CANVAS & REMOVE STREAMLIT CHROME
       ========================================================================= */
    #MainMenu { visibility: hidden !important; display: none !important; }
    footer { visibility: hidden !important; display: none !important; }
    header[data-testid="stHeader"] { visibility: hidden !important; display: none !important; }
    .stDeployButton { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }

    /* Root App Background: Deep Obsidian Navy with Ambient Radial Glow */
    .stApp {
        background: radial-gradient(circle at 50% -12%, #182742 0%, #0B111E 48%, #05080F 100%) !important;
        color: #F8FAFC !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased !important;
    }

    .block-container {
        max-width: 880px !important;
        padding-top: 1.8rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    /* =========================================================================
       LUXURY HERO BRANDING SECTION
       ========================================================================= */
    .luxury-hero {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, rgba(22, 34, 58, 0.72) 0%, rgba(10, 16, 28, 0.85) 100%);
        border: 1px solid rgba(212, 175, 55, 0.26);
        border-radius: 20px;
        padding: 1.35rem 1.65rem;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: 0 14px 34px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        transition: border-color 0.3s ease;
    }

    .luxury-hero:hover {
        border-color: rgba(212, 175, 55, 0.42);
    }

    .hero-brand {
        display: flex;
        align-items: center;
        gap: 1.15rem;
    }

    .brand-crest {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 52px;
        height: 52px;
        border-radius: 14px;
        background: linear-gradient(135deg, #1F2E4A 0%, #0E1626 100%);
        border: 1.5px solid rgba(212, 175, 55, 0.55);
        box-shadow: 0 0 18px rgba(212, 175, 55, 0.25);
        font-size: 1.6rem;
    }

    .brand-details {
        display: flex;
        flex-direction: column;
    }

    .brand-title {
        font-family: 'Cinzel', Georgia, serif;
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        background: linear-gradient(135deg, #FFF9EB 0%, #E8C87A 50%, #C5A059 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.15;
    }

    .brand-sub-badge {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        color: #D4AF37;
        background: rgba(212, 175, 55, 0.12);
        padding: 2px 7px;
        border-radius: 6px;
        border: 1px solid rgba(212, 175, 55, 0.3);
        margin-left: 8px;
        vertical-align: middle;
        -webkit-text-fill-color: #D4AF37;
    }

    .brand-tagline {
        font-size: 0.85rem;
        color: #94A3B8;
        font-weight: 400;
        margin-top: 4px;
        letter-spacing: 0.01em;
    }

    .hero-status {
        display: flex;
        align-items: center;
        gap: 8px;
        background: rgba(14, 22, 38, 0.8);
        border: 1px solid rgba(212, 175, 55, 0.22);
        padding: 7px 14px;
        border-radius: 9999px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    .status-pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 10px #10B981;
        animation: pulse-glow 2.2s infinite ease-in-out;
    }

    @keyframes pulse-glow {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.45; transform: scale(1.2); }
    }

    .status-text {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.07em;
        color: #E2E8F0;
        text-transform: uppercase;
    }

    /* =========================================================================
       SUGGESTED QUESTION CHIPS (PILL BUTTONS)
       ========================================================================= */
    div[data-testid="stHorizontalBlock"] {
        gap: 0.55rem !important;
        margin-bottom: 1.4rem !important;
    }

    div[data-testid="stHorizontalBlock"] div[data-testid="column"] button {
        background: linear-gradient(145deg, rgba(22, 33, 56, 0.8), rgba(13, 20, 36, 0.9)) !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(212, 175, 55, 0.25) !important;
        border-radius: 9999px !important;
        font-size: 0.83rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.015em !important;
        padding: 0.52rem 0.9rem !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        width: 100% !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    div[data-testid="stHorizontalBlock"] div[data-testid="column"] button:hover {
        background: linear-gradient(145deg, rgba(32, 48, 80, 0.95), rgba(19, 29, 50, 0.98)) !important;
        border-color: #D4AF37 !important;
        color: #FFF9EB !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 22px rgba(212, 175, 55, 0.26), 0 0 10px rgba(212, 175, 55, 0.16) !important;
    }

    div[data-testid="stHorizontalBlock"] div[data-testid="column"] button:active {
        transform: translateY(0) !important;
    }

    /* =========================================================================
       CHAT MESSAGE BUBBLES
       ========================================================================= */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0.45rem 0 !important;
        margin-bottom: 0.65rem !important;
    }

    /* Avatar styling */
    [data-testid="stChatMessageAvatar"] {
        background: linear-gradient(135deg, #1F2E4A, #0E1626) !important;
        border: 1.5px solid rgba(212, 175, 55, 0.45) !important;
        border-radius: 50% !important;
        box-shadow: 0 0 12px rgba(212, 175, 55, 0.2) !important;
        width: 38px !important;
        height: 38px !important;
    }

    /* User Message Container & Bubble */
    div[data-testid="stChatMessage"]:has([aria-label*="user"]),
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        flex-direction: row-reverse !important;
    }

    div[data-testid="stChatMessageContent"][aria-label*="user"],
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) div[data-testid="stChatMessageContent"] {
        background: linear-gradient(135deg, #1E293B 0%, #131E30 100%) !important;
        border: 1px solid rgba(148, 163, 184, 0.26) !important;
        border-radius: 18px 4px 18px 18px !important;
        padding: 0.95rem 1.35rem !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3) !important;
        color: #F8FAFC !important;
        max-width: 82% !important;
        margin-left: auto !important;
        margin-right: 0 !important;
        font-size: 0.94rem !important;
        line-height: 1.6 !important;
    }

    /* Assistant Message Bubble */
    div[data-testid="stChatMessageContent"][aria-label*="assistant"],
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) div[data-testid="stChatMessageContent"] {
        background: linear-gradient(145deg, rgba(18, 27, 46, 0.82) 0%, rgba(10, 16, 28, 0.92) 100%) !important;
        border: 1px solid rgba(212, 175, 55, 0.22) !important;
        border-left: 3.5px solid #D4AF37 !important;
        border-radius: 4px 18px 18px 18px !important;
        padding: 1.15rem 1.45rem !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        color: #F1F5F9 !important;
        max-width: 88% !important;
        font-size: 0.94rem !important;
        line-height: 1.68 !important;
    }

    /* Assistant text highlights */
    div[data-testid="stChatMessageContent"][aria-label*="assistant"] strong {
        color: #F6E7BD !important;
        font-weight: 600 !important;
    }

    div[data-testid="stChatMessageContent"][aria-label*="assistant"] p {
        margin-bottom: 0.55rem !important;
    }

    div[data-testid="stChatMessageContent"][aria-label*="assistant"] p:last-child {
        margin-bottom: 0 !important;
    }

    /* =========================================================================
       DEBUG EXPANDER & SOURCES ACCORDION
       ========================================================================= */
    [data-testid="stExpander"] {
        background: rgba(10, 16, 28, 0.6) !important;
        border: 1px solid rgba(212, 175, 55, 0.16) !important;
        border-radius: 10px !important;
        margin-top: 0.55rem !important;
        overflow: hidden !important;
    }

    [data-testid="stExpander"] summary {
        font-size: 0.78rem !important;
        color: #94A3B8 !important;
        font-weight: 500 !important;
        letter-spacing: 0.03em !important;
        padding: 0.38rem 0.75rem !important;
        transition: color 0.2s ease;
    }

    [data-testid="stExpander"] summary:hover {
        color: #D4AF37 !important;
    }

    [data-testid="stExpander"] pre {
        background-color: rgba(5, 8, 15, 0.7) !important;
        border: 1px solid rgba(212, 175, 55, 0.12) !important;
        border-radius: 8px !important;
        padding: 0.6rem !important;
        font-size: 0.75rem !important;
    }

    /* =========================================================================
       CHAT INPUT FIELD
       ========================================================================= */
    [data-testid="stChatInput"] {
        background-color: transparent !important;
    }

    [data-testid="stChatInput"] textarea {
        background: rgba(13, 20, 36, 0.88) !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(212, 175, 55, 0.32) !important;
        border-radius: 14px !important;
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.45) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        font-size: 0.92rem !important;
        padding: 0.75rem 1rem !important;
        transition: all 0.25s ease !important;
    }

    [data-testid="stChatInput"] textarea:focus {
        border-color: #D4AF37 !important;
        box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.35), 0 8px 30px rgba(0, 0, 0, 0.6) !important;
    }

    [data-testid="stChatInput"] button {
        color: #D4AF37 !important;
        transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    [data-testid="stChatInput"] button:hover {
        transform: scale(1.12) !important;
        color: #FFF9EB !important;
    }

    /* =========================================================================
       PINNED LUXURY DISCLAIMER
       ========================================================================= */
    .luxury-disclaimer {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        font-size: 0.72rem;
        color: #64748B;
        letter-spacing: 0.025em;
        margin-top: 1.3rem;
        margin-bottom: 0.35rem;
        text-align: center;
        padding: 0.35rem 0.75rem;
    }

    .luxury-disclaimer .disc-icon {
        color: #D4AF37;
        font-size: 0.76rem;
        opacity: 0.85;
    }

    /* =========================================================================
       SPINNER ANIMATION
       ========================================================================= */
    .stSpinner > div {
        border-top-color: #D4AF37 !important;
    }

    .stSpinner {
        color: #E8C87A !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em !important;
    }

    .rtl-text {
        direction: rtl;
        text-align: right;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
    }

    /* =========================================================================
       RESPONSIVE DESIGN
       ========================================================================= */
    @media (max-width: 640px) {
        .luxury-hero {
            flex-direction: column;
            align-items: flex-start;
            gap: 12px;
            padding: 1.1rem;
        }
        .hero-status {
            align-self: flex-start;
        }
        .brand-title {
            font-size: 1.45rem;
        }
        div[data-testid="stChatMessageContent"][aria-label*="user"],
        div[data-testid="stChatMessageContent"][aria-label*="assistant"] {
            max-width: 95% !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 3. Cached RAG Retriever & OpenRouter Client
# -----------------------------------------------------------------------------
@st.cache_resource
def get_retriever():
    return HybridRetriever()

@st.cache_resource
def get_client():
    return OpenRouterClient()

retriever = get_retriever()
client = get_client()

# -----------------------------------------------------------------------------
# 4. Session State Initialization
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Welcome to DAR Luxury Property Advisory. I specialize in DarGlobal's elite international developments (The Astera, Trump International Towers, Les Vagues, DG1) and Wasalt's verified prime properties across Saudi Arabia. How may I assist your portfolio today?",
            "sources": [],
            "debug": None
        }
    ]

# -----------------------------------------------------------------------------
# 5. Luxury Hero Section
# -----------------------------------------------------------------------------
st.markdown("""
<div class="luxury-hero">
    <div class="hero-brand">
        <div class="brand-crest">
            <span>🏛️</span>
        </div>
        <div class="brand-details">
            <div class="brand-title">
                DAR <span class="brand-sub-badge">PRIVATE PORTFOLIO</span>
            </div>
            <div class="brand-tagline">
                AI Property Advisor for DarGlobal International & Wasalt Saudi Arabia
            </div>
        </div>
    </div>
    <div class="hero-status">
        <div class="status-pulse"></div>
        <span class="status-text">Verified Intelligence</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. Curated Suggested Question Chips
# -----------------------------------------------------------------------------
sample_chips = [
    {
        "icon": "💎",
        "label": "The Astera Prices",
        "query": "What are the starting prices for The Astera?"
    },
    {
        "icon": "🏙️",
        "label": "Trump Tower Dubai",
        "query": "Tell me about Trump International Hotel & Tower Dubai."
    },
    {
        "icon": "🏡",
        "label": "Wasalt Riyadh Villas",
        "query": "What villas are for sale in Riyadh on Wasalt?"
    },
    {
        "icon": "🌍",
        "label": "مشروع ذا أستيرا",
        "query": "ما هي تفاصيل مشروع ذا أستيرا؟"
    }
]

cols = st.columns(len(sample_chips))
selected_query = None

for i, chip in enumerate(sample_chips):
    with cols[i]:
        btn_label = f"{chip['icon']} {chip['label']}"
        if st.button(btn_label, key=f"chip_btn_{i}", help=chip["query"]):
            selected_query = chip["query"]

# -----------------------------------------------------------------------------
# 7. Helper & Query Processing Logic
# -----------------------------------------------------------------------------
def is_arabic(text: str) -> bool:
    import re
    return bool(re.search(r'[\u0600-\u06FF]', text or ""))

def process_query(user_query: str):
    """Execute the end-to-end RAG pipeline and return answer, sources, debug dict."""
    client_ip = "127.0.0.1"

    # 1. Rate limiting check
    if not RATE_LIMITER.check(client_ip):
        return (
            "Rate limit exceeded. Please wait a moment before sending another query.",
            [],
            {"error": "rate_limited"}
        )

    # 2. Input validation & injection check
    try:
        validate_user_input(user_query)
    except GuardrailViolation as gv:
        return (
            gv.message,
            [],
            {"error": "guardrail_violation", "code": gv.status_code}
        )

    # 3. Answer cache check
    cached = ANSWER_CACHE.get(user_query, None)
    if cached:
        return (
            cached.get("answer_text", cached.get("answer", "")),
            cached.get("sources", []),
            {
                "model_used": cached.get("model_used", "cache"),
                "latency_ms": 0.0,
                "cached": True
            }
        )

    start_time = time.monotonic()

    # 4. Hybrid retrieval
    retrieved = retriever.retrieve(user_query, top_k=4)
    chunks_dicts = [r.to_dict() for r in retrieved]

    if not retrieved:
        latency = round((time.monotonic() - start_time) * 1000, 2)
        decline = "I don't have enough verified information in the DarGlobal or Wasalt database to answer this question."
        return (
            decline,
            [],
            {"model_used": "rules-engine", "latency_ms": latency, "cached": False}
        )

    # 5. Format prompt with untrusted context
    user_prompt, sources = format_context_prompt(user_query, chunks_dicts)

    # 6. Call OpenRouter
    try:
        completion = client.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        total_latency = round((time.monotonic() - start_time) * 1000, 2)
        answer_text, highlights = clean_answer_text(completion.content)

        response_data = {
            "answer_text": answer_text,
            "highlights": highlights,
            "sources": sources,
            "model_used": completion.model_used,
            "latency_ms": total_latency,
            "cached": False,
            "answer": answer_text
        }
        ANSWER_CACHE.set(user_query, None, response_data)

        return (
            answer_text,
            sources,
            {
                "model_used": completion.model_used,
                "latency_ms": total_latency,
                "cached": False
            }
        )
    except OpenRouterError as ore:
        return (
            ore.user_facing_message,
            [],
            {"error": "openrouter_error", "code": ore.status_code}
        )

# -----------------------------------------------------------------------------
# 8. Render Chat History
# -----------------------------------------------------------------------------
for msg in st.session_state.messages:
    role = msg["role"]
    avatar = "👤" if role == "user" else "🏛️"
    with st.chat_message(role, avatar=avatar):
        content = msg["content"]
        if is_arabic(content):
            st.markdown(f'<div class="rtl-text">{content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(content)
        
        # Collapsed Debug Info
        debug = msg.get("debug")
        msg_sources = msg.get("sources", [])
        if debug:
            with st.expander("Debug Info", expanded=False):
                model_name = debug.get("model_used", "N/A")
                latency = debug.get("latency_ms", 0.0)
                is_cached = debug.get("cached", False)
                st.code(f"Model: {model_name}\nLatency: {latency}ms\nCached: {is_cached}", language="yaml")
                if msg_sources:
                    st.caption("Referenced Sources:")
                    for s in msg_sources:
                        sid = s.get("id") or s.get("index") or "•"
                        title = s.get("title") or s.get("url") or f"Source {sid}"
                        url = s.get("url", "#")
                        st.markdown(f"- [{sid}] [{title}]({url})")

# -----------------------------------------------------------------------------
# 9. Input Handling (Chat Input or Sample Button)
# -----------------------------------------------------------------------------
prompt = st.chat_input("Inquire about DarGlobal residences or Wasalt property listings...")
query_to_run = selected_query or prompt

if query_to_run:
    # Append user message
    st.session_state.messages.append({
        "role": "user",
        "content": query_to_run,
        "sources": [],
        "debug": None
    })
    
    with st.chat_message("user", avatar="👤"):
        if is_arabic(query_to_run):
            st.markdown(f'<div class="rtl-text">{query_to_run}</div>', unsafe_allow_html=True)
        else:
            st.markdown(query_to_run)

    # Generate assistant message
    with st.chat_message("assistant", avatar="🏛️"):
        with st.spinner("Consulting luxury property portfolio & verified records..."):
            ans_text, sources, debug_info = process_query(query_to_run)
            
            if is_arabic(ans_text):
                st.markdown(f'<div class="rtl-text">{ans_text}</div>', unsafe_allow_html=True)
            else:
                st.markdown(ans_text)
            
            if debug_info:
                with st.expander("Debug Info", expanded=False):
                    model_name = debug_info.get("model_used", "N/A")
                    latency = debug_info.get("latency_ms", 0.0)
                    is_cached = debug_info.get("cached", False)
                    st.code(f"Model: {model_name}\nLatency: {latency}ms\nCached: {is_cached}", language="yaml")
                    if sources:
                        st.caption("Referenced Sources:")
                        for s in sources:
                            sid = s.get("id") or s.get("index") or "•"
                            title = s.get("title") or s.get("url") or f"Source {sid}"
                            url = s.get("url", "#")
                            st.markdown(f"- [{sid}] [{title}]({url})")

    st.session_state.messages.append({
        "role": "assistant",
        "content": ans_text,
        "sources": sources,
        "debug": debug_info
    })

# -----------------------------------------------------------------------------
# 10. Refined Pinned Luxury Disclaimer
# -----------------------------------------------------------------------------
st.markdown(
    '<div class="luxury-disclaimer">'
    '<span class="disc-icon">⚜️</span>'
    '<span>Verified luxury listings intelligence · Independent financial & legal due diligence recommended · Subject to real-time market updates</span>'
    '</div>',
    unsafe_allow_html=True
)
