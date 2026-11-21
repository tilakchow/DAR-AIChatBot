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
    page_title="DAR — Property Intelligence & Advisory",
    page_icon="🏛️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# 2. Bespoke Editorial Dark Theme (Refined Obsidian & Warm Titanium)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

    /* Remove Streamlit Default Chrome */
    #MainMenu { visibility: hidden !important; display: none !important; }
    footer { visibility: hidden !important; display: none !important; }
    header[data-testid="stHeader"] { visibility: hidden !important; display: none !important; }
    .stDeployButton { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }

    /* Root Canvas: Architectural Obsidian Slate */
    .stApp {
        background: #090B10 !important;
        color: #F1F5F9 !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        -webkit-font-smoothing: antialiased !important;
    }

    .block-container {
        max-width: 860px !important;
        padding-top: 1.75rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    /* -------------------------------------------------------------------------
       EDITORIAL BRAND HEADER
       ------------------------------------------------------------------------- */
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #0F131C;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.25rem 1.6rem;
        margin-bottom: 1.35rem;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
    }

    .brand-left {
        display: flex;
        align-items: center;
        gap: 1.1rem;
    }

    .brand-monogram {
        width: 44px;
        height: 44px;
        border-radius: 11px;
        background: #171D2A;
        border: 1px solid rgba(212, 184, 134, 0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.95rem;
        letter-spacing: 0.06em;
        color: #D4B886;
    }

    .brand-copy {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .brand-title-row {
        display: flex;
        align-items: center;
        gap: 0.55rem;
    }

    .brand-name {
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        color: #FFFFFF;
        text-transform: uppercase;
    }

    .brand-tag {
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        color: #D4B886;
        background: rgba(212, 184, 134, 0.1);
        border: 1px solid rgba(212, 184, 134, 0.25);
        padding: 2px 7px;
        border-radius: 5px;
        text-transform: uppercase;
    }

    .brand-subtitle {
        font-size: 0.82rem;
        color: #8C98A9;
        font-weight: 400;
        letter-spacing: 0.01em;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        background: #131924;
        border: 1px solid rgba(255, 255, 255, 0.07);
        padding: 6px 12px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 0.03em;
        color: #CBD5E1;
    }

    .status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #10B981;
    }

    /* -------------------------------------------------------------------------
       SUGGESTION BUTTONS (CURATED INQUIRIES)
       ------------------------------------------------------------------------- */
    div[data-testid="stHorizontalBlock"] {
        gap: 0.5rem !important;
        margin-bottom: 1.25rem !important;
    }

    div[data-testid="stHorizontalBlock"] div[data-testid="column"] button {
        background: #11151F !important;
        color: #CBD5E1 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        font-size: 0.81rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.01em !important;
        padding: 0.52rem 0.85rem !important;
        box-shadow: none !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    div[data-testid="stHorizontalBlock"] div[data-testid="column"] button:hover {
        background: #171E2B !important;
        border-color: rgba(212, 184, 134, 0.45) !important;
        color: #FFFFFF !important;
    }

    /* -------------------------------------------------------------------------
       CHAT MESSAGES
       ------------------------------------------------------------------------- */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0.35rem 0 !important;
        margin-bottom: 0.5rem !important;
    }

    /* Avatars */
    [data-testid="stChatMessageAvatar"] {
        background: #131924 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        width: 34px !important;
        height: 34px !important;
    }

    /* User Message Container & Bubble */
    div[data-testid="stChatMessage"]:has([aria-label*="user"]),
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        flex-direction: row-reverse !important;
    }

    div[data-testid="stChatMessageContent"][aria-label*="user"],
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) div[data-testid="stChatMessageContent"] {
        background: #18202F !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 14px 4px 14px 14px !important;
        padding: 0.85rem 1.15rem !important;
        color: #F8FAFC !important;
        max-width: 80% !important;
        margin-left: auto !important;
        margin-right: 0 !important;
        font-size: 0.92rem !important;
        line-height: 1.55 !important;
    }

    /* Assistant Message Bubble */
    div[data-testid="stChatMessageContent"][aria-label*="assistant"],
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) div[data-testid="stChatMessageContent"] {
        background: #0F131C !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 4px 14px 14px 14px !important;
        padding: 1.05rem 1.35rem !important;
        color: #E2E8F0 !important;
        max-width: 88% !important;
        font-size: 0.92rem !important;
        line-height: 1.62 !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
    }

    div[data-testid="stChatMessageContent"][aria-label*="assistant"] strong {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }

    div[data-testid="stChatMessageContent"][aria-label*="assistant"] p {
        margin-bottom: 0.5rem !important;
    }

    div[data-testid="stChatMessageContent"][aria-label*="assistant"] p:last-child {
        margin-bottom: 0 !important;
    }

    /* -------------------------------------------------------------------------
       ELEGANT SOURCE PILLS (VERIFIED EVIDENCE)
       ------------------------------------------------------------------------- */
    .sources-row {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.85rem;
        padding-top: 0.75rem;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
    }

    .sources-tag {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        color: #64748B;
        text-transform: uppercase;
        margin-right: 0.25rem;
    }

    .source-chip-link {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: #141A26;
        border: 1px solid rgba(255, 255, 255, 0.09);
        color: #94A3B8;
        font-size: 0.75rem;
        font-weight: 500;
        padding: 3px 9px;
        border-radius: 6px;
        text-decoration: none !important;
        transition: all 0.18s ease;
    }

    .source-chip-link:hover {
        background: #1B2333;
        border-color: rgba(212, 184, 134, 0.4);
        color: #D4B886;
    }

    .source-chip-portal {
        color: #D4B886;
        font-weight: 600;
        font-size: 0.7rem;
    }

    /* Discreet telemetry metadata */
    .msg-telemetry {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.7rem;
        color: #475569;
        margin-top: 0.45rem;
        letter-spacing: 0.02em;
    }

    .msg-telemetry span {
        display: inline-flex;
        align-items: center;
    }

    /* -------------------------------------------------------------------------
       EXPANDER FOR RAW TELEMETRY (CLEAN & SUBTLE)
       ------------------------------------------------------------------------- */
    [data-testid="stExpander"] {
        background: transparent !important;
        border: none !important;
        margin-top: 0.35rem !important;
    }

    [data-testid="stExpander"] summary {
        font-size: 0.72rem !important;
        color: #475569 !important;
        font-weight: 500 !important;
        padding: 0.15rem 0.3rem !important;
        transition: color 0.18s ease;
    }

    [data-testid="stExpander"] summary:hover {
        color: #94A3B8 !important;
    }

    [data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
        padding: 0.4rem 0 !important;
    }

    /* -------------------------------------------------------------------------
       CHAT INPUT FIELD
       ------------------------------------------------------------------------- */
    [data-testid="stChatInput"] {
        background-color: transparent !important;
    }

    [data-testid="stChatInput"] textarea {
        background: #11151F !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        font-size: 0.91rem !important;
        padding: 0.75rem 1rem !important;
        transition: border-color 0.2s ease !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
    }

    [data-testid="stChatInput"] textarea:focus {
        border-color: rgba(212, 184, 134, 0.5) !important;
        box-shadow: 0 0 0 1px rgba(212, 184, 134, 0.3), 0 4px 24px rgba(0, 0, 0, 0.4) !important;
    }

    [data-testid="stChatInput"] button {
        color: #D4B886 !important;
    }

    /* -------------------------------------------------------------------------
       FOOTER LEGAL DISCLAIMER
       ------------------------------------------------------------------------- */
    .brand-disclaimer {
        text-align: center;
        font-size: 0.72rem;
        color: #526071;
        letter-spacing: 0.02em;
        margin-top: 1.25rem;
        margin-bottom: 0.25rem;
        padding: 0.25rem 0.5rem;
    }

    .brand-disclaimer a {
        color: #64748B;
        text-decoration: underline;
    }

    .rtl-text {
        direction: rtl;
        text-align: right;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
    }

    @media (max-width: 640px) {
        .brand-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
            padding: 1rem;
        }
        .status-pill {
            align-self: flex-start;
        }
        div[data-testid="stChatMessageContent"][aria-label*="user"],
        div[data-testid="stChatMessageContent"][aria-label*="assistant"] {
            max-width: 95% !important;
        }
    }
</style>
""", unsafe_allow_html=True)


def resolve_api_key() -> str:
    """Resolve OpenRouter API key from st.secrets or os.environ, sanitizing any accidental line breaks."""
    if hasattr(st, "secrets"):
        try:
            if "OPENROUTER_API_KEY" in st.secrets:
                val = str(st.secrets["OPENROUTER_API_KEY"]).strip().replace("\n", "").replace("\r", "").strip("\"'")
                if val:
                    return val
        except Exception:
            pass
    return os.environ.get("OPENROUTER_API_KEY", "").strip().replace("\n", "").replace("\r", "").strip("\"'")

# -----------------------------------------------------------------------------
# 3. Cached RAG Retriever & OpenRouter Client
# -----------------------------------------------------------------------------
@st.cache_resource
def get_retriever():
    return HybridRetriever()

@st.cache_resource
def get_client(api_key: str):
    return OpenRouterClient(api_key=api_key)

retriever = get_retriever()

# -----------------------------------------------------------------------------
# 4. Session State Initialization
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Welcome. I provide verified specifications, current pricing, and unit availability for DarGlobal international residences and Wasalt Saudi properties. What project or location are you reviewing today?",
            "sources": [],
            "debug": None
        }
    ]

# -----------------------------------------------------------------------------
# 5. Editorial Brand Header
# -----------------------------------------------------------------------------
indexed_count = len(retriever.chunks_by_id) if hasattr(retriever, "chunks_by_id") else 4217

st.markdown(f"""
<div class="brand-header">
    <div class="brand-left">
        <div class="brand-monogram">DAR</div>
        <div class="brand-copy">
            <div class="brand-title-row">
                <span class="brand-name">DAR Advisory</span>
                <span class="brand-tag">PORTFOLIO INTELLIGENCE</span>
            </div>
            <div class="brand-subtitle">
                DarGlobal International Residences & Wasalt Saudi Property Portfolios
            </div>
        </div>
    </div>
    <div class="status-pill">
        <div class="status-dot"></div>
        <span>{indexed_count:,} Verified Chunks</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. Curated Inquiries (Suggested Chips)
# -----------------------------------------------------------------------------
sample_chips = [
    {
        "label": "The Astera · Starting Prices",
        "query": "What are the starting prices for The Astera?"
    },
    {
        "label": "Trump Tower Dubai · Specifications",
        "query": "Tell me about Trump International Hotel & Tower Dubai."
    },
    {
        "label": "Riyadh Villas · Wasalt Listings",
        "query": "What villas are for sale in Riyadh on Wasalt?"
    },
    {
        "label": "مشروع ذا أستيرا · تفاصيل المشروع",
        "query": "ما هي تفاصيل مشروع ذا أستيرا؟"
    }
]

cols = st.columns(len(sample_chips))
selected_query = None

for i, chip in enumerate(sample_chips):
    with cols[i]:
        if st.button(chip["label"], key=f"chip_btn_{i}", help=chip["query"]):
            selected_query = chip["query"]

# -----------------------------------------------------------------------------
# 7. Query Processing Logic
# -----------------------------------------------------------------------------
def is_arabic(text: str) -> bool:
    import re
    return bool(re.search(r'[\u0600-\u06FF]', text or ""))

def render_sources_html(sources: list) -> str:
    """Render clean, elegant source chips with portal tags."""
    if not sources:
        return ""
    chips_html = []
    for s in sources:
        sid = s.get("id") or s.get("index") or "•"
        title = s.get("title") or s.get("url") or f"Source {sid}"
        url = s.get("url", "#")
        site = s.get("site", "")
        site_label = "DarGlobal" if site == "darglobal" else ("Wasalt" if site == "wasalt" else "Source")
        chips_html.append(
            f'<a class="source-chip-link" href="{url}" target="_blank" rel="noopener noreferrer">'
            f'<span class="source-chip-portal">{site_label}</span> {title} ↗'
            f'</a>'
        )
    return (
        f'<div class="sources-row">'
        f'<span class="sources-tag">Verified Sources</span>'
        f'{"".join(chips_html)}'
        f'</div>'
    )

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
    api_key = resolve_api_key()
    client = get_client(api_key)
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
        
        # Render verified source pills directly under assistant answers
        msg_sources = msg.get("sources", [])
        if role == "assistant" and msg_sources:
            st.markdown(render_sources_html(msg_sources), unsafe_allow_html=True)

        # Subtle telemetry info
        debug = msg.get("debug")
        if debug and role == "assistant":
            model_name = debug.get("model_used", "")
            latency = debug.get("latency_ms", 0.0)
            is_cached = debug.get("cached", False)
            if model_name:
                cached_tag = " · Cached" if is_cached else ""
                telemetry_str = f"⚡ {latency}ms · {model_name}{cached_tag}"
                st.markdown(f'<div class="msg-telemetry"><span>{telemetry_str}</span></div>', unsafe_allow_html=True)

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
        with st.spinner("Retrieving verified portfolio records..."):
            ans_text, sources, debug_info = process_query(query_to_run)
            
            if is_arabic(ans_text):
                st.markdown(f'<div class="rtl-text">{ans_text}</div>', unsafe_allow_html=True)
            else:
                st.markdown(ans_text)
            
            if sources:
                st.markdown(render_sources_html(sources), unsafe_allow_html=True)

            if debug_info:
                model_name = debug_info.get("model_used", "")
                latency = debug_info.get("latency_ms", 0.0)
                is_cached = debug_info.get("cached", False)
                if model_name:
                    cached_tag = " · Cached" if is_cached else ""
                    telemetry_str = f"⚡ {latency}ms · {model_name}{cached_tag}"
                    st.markdown(f'<div class="msg-telemetry"><span>{telemetry_str}</span></div>', unsafe_allow_html=True)

    st.session_state.messages.append({
        "role": "assistant",
        "content": ans_text,
        "sources": sources,
        "debug": debug_info
    })

# -----------------------------------------------------------------------------
# 10. Refined Pinned Legal Disclaimer
# -----------------------------------------------------------------------------
st.markdown(
    '<div class="brand-disclaimer">'
    'Verified intelligence from indexed DarGlobal and Wasalt portfolios · Independent financial & legal due diligence advised'
    '</div>',
    unsafe_allow_html=True
)
