"""
DAR-24, DAR-25 · FastAPI Web Server & Chat UI.

Acceptance criteria (from DAR-24 & DAR-25):
  ✓ Serves POST /api/chat, GET /health, GET /api/stats
  ✓ Chat response includes the answer, source list, model used, and latency
  ✓ openapi.yaml is generated from the app, not hand-written
  ✓ Chat UI with Arabic RTL support, clickable source links, and Wasalt attribution
"""

import os
import sys
import json
import time
import yaml
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.abspath('.'))

from src.rag.retriever import HybridRetriever
from src.rag.prompt import SYSTEM_PROMPT, format_context_prompt, PROMPT_VERSION
from src.rag.openrouter_client import OpenRouterClient, OpenRouterError
from src.rag.guardrails import validate_user_input, GuardrailViolation, RATE_LIMITER, ANSWER_CACHE
from src.rag.schema import SourceItem, ChatResponse, clean_answer_text, FormattedAnswer

app = FastAPI(
    title="DAR — DarGlobal AI Property Assistant API",
    description="Retrieval-Augmented Generation (RAG) assistant for DarGlobal and Wasalt real estate.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Initialize retriever
retriever = HybridRetriever()

# Initialize OpenRouter client
client = OpenRouterClient()


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str = Field(..., max_length=1000, json_schema_extra={"example": "What are the starting prices for The Astera by Aston Martin?"})
    site: Optional[Literal["darglobal", "wasalt"]] = Field(None, description="Optional filter by property portal")





# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for Docker & deployment monitoring (DAR-24, DAR-27)."""
    return {
        "status": "ok",
        "service": "DAR AI Property Assistant",
        "version": "1.0.0",
        "prompt_version": PROMPT_VERSION,
        "indexed_chunks": len(retriever.chunks_by_id)
    }


@app.get("/api/stats", tags=["System"])
def get_stats():
    """Return dataset statistics from data/summary.json (DAR-19, DAR-24)."""
    summary_path = os.path.join("data", "summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "no summary.json found"}


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest, req: Request):
    """Ask a question to the DarGlobal and Wasalt property assistant (DAR-24)."""
    client_ip = req.client.host if req.client else "127.0.0.1"

    # 1. Rate limiting check (DAR-23)
    if not RATE_LIMITER.check(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait a moment before sending another message."
        )

    # 2. Input validation & prompt-injection check (DAR-23)
    try:
        validate_user_input(request.query)
    except GuardrailViolation as gv:
        raise HTTPException(status_code=gv.status_code, detail=gv.message)

    # 3. Answer cache check (DAR-23)
    cached_val = ANSWER_CACHE.get(request.query, request.site)
    if cached_val:
        cached_val["cached"] = True
        return cached_val

    start_time = time.monotonic()

    # 4. Hybrid retrieval (DAR-20)
    retrieved = retriever.retrieve(request.query, top_k=4, site_filter=request.site)
    chunks_dicts = [r.to_dict() for r in retrieved]

    # If no relevant chunks found in the database, decline early
    if not retrieved:
        latency = round((time.monotonic() - start_time) * 1000, 2)
        decline_msg = "I don't have enough verified information in the DarGlobal or Wasalt database to answer this question."
        resp = {
            "answer_text": decline_msg,
            "highlights": [],
            "sources": [],
            "model_used": "rules-engine",
            "latency_ms": latency,
            "cached": False,
            "answer": decline_msg
        }
        return resp

    # 5. Format prompt with untrusted context and citations (DAR-21)
    user_prompt, sources = format_context_prompt(request.query, chunks_dicts)

    # 6. Call OpenRouter with fallback models (DAR-22)
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

        # Cache valid response (DAR-23)
        ANSWER_CACHE.set(request.query, request.site, response_data)

        return response_data

    except OpenRouterError as ore:
        raise HTTPException(status_code=ore.status_code or 502, detail=ore.user_facing_message)


@app.get("/openapi.yaml", include_in_schema=False)
def export_openapi_yaml():
    """Export the app's OpenAPI 3.1 specification to YAML (DAR-24)."""
    openapi_schema = app.openapi()
    yaml_spec = yaml.dump(openapi_schema, sort_keys=False, allow_unicode=True)
    return Response(content=yaml_spec, media_type="text/yaml")


# ---------------------------------------------------------------------------
# DAR-25: Interactive Chat UI with Arabic RTL Support & Citations
# ---------------------------------------------------------------------------

HTML_UI = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DAR — AI Property Assistant</title>
  <!-- Markdown parser and sanitizer -->
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    :root {
      --bg: #090b10;
      --card-bg: #0f131c;
      --border: rgba(255, 255, 255, 0.08);
      --text: #f1f5f9;
      --text-muted: #8c98a9;
      --accent: #d4b886;
      --accent-hover: #e2cb9f;
      --user-msg-bg: #18202f;
      --bot-msg-bg: #0f131c;
      --font: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
    }
    header {
      background: var(--card-bg);
      border-bottom: 1px solid var(--border);
      padding: 1.1rem 1.6rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .header-brand {
      display: flex;
      align-items: center;
      gap: 0.9rem;
    }
    .monogram {
      width: 38px;
      height: 38px;
      border-radius: 9px;
      background: #171d2a;
      border: 1px solid rgba(212, 184, 134, 0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.88rem;
      letter-spacing: 0.06em;
      color: var(--accent);
    }
    header h1 { font-size: 1.05rem; font-weight: 700; color: #ffffff; letter-spacing: 0.02em; }
    header p { font-size: 0.8rem; color: var(--text-muted); }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #131924;
      color: #cbd5e1;
      padding: 0.35rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.72rem;
      font-weight: 500;
      border: 1px solid var(--border);
    }
    .badge::before {
      content: "";
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
    }
    #chat-container {
      flex: 1;
      overflow-y: auto;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.15rem;
    }
    .msg {
      max-width: 82%;
      padding: 0.95rem 1.3rem;
      border-radius: 12px;
      line-height: 1.62;
      font-size: 0.92rem;
      position: relative;
    }
    .msg.user {
      align-self: flex-end;
      background: var(--user-msg-bg);
      color: #fff;
      border: 1px solid rgba(255, 255, 255, 0.09);
      border-bottom-right-radius: 0.25rem;
    }
    .msg.bot {
      align-self: flex-start;
      background: var(--bot-msg-bg);
      border: 1px solid var(--border);
      border-bottom-left-radius: 0.25rem;
      box-shadow: 0 4px 18px rgba(0, 0, 0, 0.2);
    }
    .msg.bot p { margin-bottom: 0.5rem; }
    .msg.bot p:last-child { margin-bottom: 0; }
    .msg.bot ul, .msg.bot ol { margin: 0.4rem 0 0.5rem 1.25rem; }
    .msg.bot li { margin-bottom: 0.25rem; }
    .msg.bot strong { color: #ffffff; font-weight: 600; }
    .msg.bot code { background: rgba(15, 23, 42, 0.7); padding: 0.15rem 0.35rem; border-radius: 0.25rem; font-size: 0.85em; font-family: monospace; }
    .msg.rtl {
      direction: rtl;
      text-align: right;
    }
    /* Citation pills row */
    .citations-container {
      margin-top: 0.75rem;
      padding-top: 0.5rem;
      border-top: 1px solid var(--border);
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.45rem;
    }
    .citations-label {
      font-size: 0.68rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 600;
      margin-right: 0.2rem;
    }
    .source-chip {
      height: 24px;
      padding: 0 8px;
      border-radius: 6px;
      background: #141a26;
      border: 1px solid var(--border);
      color: #cbd5e1;
      font-size: 0.72rem;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      text-decoration: none;
      position: relative;
      transition: all 0.18s ease;
    }
    .source-chip:hover {
      background: #1b2333;
      color: var(--accent);
      border-color: rgba(212, 184, 134, 0.4);
    }
    .source-chip::after {
      content: attr(data-tooltip);
      position: absolute;
      bottom: calc(100% + 6px);
      left: 50%;
      transform: translateX(-50%) translateY(4px);
      background: #090b10;
      color: #f8fafc;
      border: 1px solid rgba(255, 255, 255, 0.15);
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 400;
      white-space: nowrap;
      max-width: 280px;
      overflow: hidden;
      text-overflow: ellipsis;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.15s ease, transform 0.15s ease;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
      z-index: 1000;
    }
    .source-chip:hover::after {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
    /* Debug info panel */
    .debug-panel {
      margin-top: 0.5rem;
      padding-top: 0.35rem;
      border-top: 1px solid var(--border);
      font-size: 0.7rem;
      color: #526071;
    }
    .debug-panel summary {
      cursor: pointer;
      user-select: none;
      opacity: 0.7;
      transition: opacity 0.2s;
      outline: none;
    }
    .debug-panel summary:hover {
      opacity: 1;
      color: var(--accent);
    }
    .debug-content {
      margin-top: 0.35rem;
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
      background: #090b10;
      padding: 0.35rem 0.6rem;
      border-radius: 0.375rem;
      font-family: monospace;
      font-size: 0.68rem;
    }
    .cached-badge {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      padding: 1px 6px;
      border-radius: 9999px;
      font-size: 0.65rem;
    }
    /* Bottom controls */
    .bottom-section {
      background: var(--card-bg);
      border-top: 1px solid var(--border);
      display: flex;
      flex-direction: column;
    }
    .sample-bar {
      display: flex;
      gap: 0.5rem;
      overflow-x: auto;
      padding: 0.55rem 1.5rem;
      background: #0b0e14;
      border-bottom: 1px solid var(--border);
    }
    .sample-chip {
      background: #11151f;
      border: 1px solid var(--border);
      color: #94a3b8;
      padding: 0.35rem 0.75rem;
      border-radius: 8px;
      font-size: 0.78rem;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.18s ease;
    }
    .sample-chip:hover { color: #ffffff; border-color: rgba(212, 184, 134, 0.4); background: #171d2a; }
    #input-form {
      padding: 0.75rem 1.5rem;
      display: flex;
      gap: 0.75rem;
    }
    #query-input {
      flex: 1;
      background: #11151f;
      border: 1px solid var(--border);
      border-radius: 10px;
      color: var(--text);
      padding: 0.75rem 1rem;
      font-size: 0.92rem;
      outline: none;
      transition: border-color 0.2s;
    }
    #query-input:focus { border-color: rgba(212, 184, 134, 0.5); }
    button {
      background: #171d2a;
      color: var(--accent);
      font-weight: 600;
      border: 1px solid rgba(212, 184, 134, 0.35);
      padding: 0.75rem 1.4rem;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s;
    }
    button:hover { background: var(--accent); color: #090b10; }
    .disclaimer-pinned {
      text-align: center;
      font-size: 0.72rem;
      color: #526071;
      padding: 0.35rem 1.5rem 0.55rem;
      border-top: 1px solid var(--border);
      background: #090b10;
    }
  </style>
</head>
<body>
  <header>
    <div class="header-brand">
      <div class="monogram">DAR</div>
      <div>
        <h1>DAR — AI Property Assistant</h1>
        <p>DarGlobal International Residences & Wasalt Kingdom Portfolios</p>
      </div>
    </div>
    <div class="badge">Verified Portfolio Index</div>
  </header>

  <div id="chat-container">
    <div class="msg bot">
      Welcome. I provide verified specifications, current pricing, and unit availability for DarGlobal international residences and Wasalt Saudi properties. What project or location are you reviewing today?
    </div>
  </div>

  <div class="bottom-section">
    <div class="sample-bar">
      <div class="sample-chip" onclick="ask('What are the starting prices for The Astera?')">The Astera · Starting Prices</div>
      <div class="sample-chip" onclick="ask('Tell me about Trump International Hotel & Tower Dubai.')">Trump Tower Dubai · Specifications</div>
      <div class="sample-chip" onclick="ask('What villas are for sale in Riyadh on Wasalt?')">Riyadh Villas · Wasalt Listings</div>
      <div class="sample-chip" onclick="ask('ما هي تفاصيل مشروع ذا أستيرا؟')">مشروع ذا أستيرا · تفاصيل المشروع</div>
    </div>

    <form id="input-form" onsubmit="sendMsg(event)">
      <input type="text" id="query-input" placeholder="Inquire about DarGlobal residences or Wasalt property listings..." autocomplete="off">
      <button type="submit" id="send-btn">Send</button>
    </form>

    <div class="disclaimer-pinned">
      Verified intelligence from indexed DarGlobal and Wasalt portfolios · Independent financial & legal due diligence advised
    </div>
  </div>

  <script>
    const chatContainer = document.getElementById('chat-container');
    const input = document.getElementById('query-input');

    if (window.marked) {
      marked.setOptions({ gfm: true, breaks: true });
    }

    function isArabic(text) {
      return /[\u0600-\u06FF]/.test(text);
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    function renderMarkdown(md) {
      if (!md) return '';
      if (window.marked && window.DOMPurify) {
        return DOMPurify.sanitize(marked.parse(md));
      } else if (window.marked) {
        return marked.parse(md);
      }
      return escapeHtml(md).replace(/\n/g, '<br>');
    }

    function ask(q) {
      input.value = q;
      sendMsg(new Event('submit'));
    }

    async function sendMsg(e) {
      e.preventDefault();
      const q = input.value.trim();
      if (!q) return;

      input.value = '';
      
      // User message
      const userDiv = document.createElement('div');
      userDiv.className = 'msg user' + (isArabic(q) ? ' rtl' : '');
      userDiv.textContent = q;
      chatContainer.appendChild(userDiv);
      chatContainer.scrollTop = chatContainer.scrollHeight;

      // Loading bot message
      const botDiv = document.createElement('div');
      botDiv.className = 'msg bot';
      botDiv.textContent = 'Searching property database and generating answer...';
      chatContainer.appendChild(botDiv);
      chatContainer.scrollTop = chatContainer.scrollHeight;

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q })
        });
        const data = await res.json();

        if (!res.ok) {
          botDiv.textContent = data.detail || 'An error occurred while processing your request.';
          return;
        }

        const answerText = data.answer_text || (typeof data.answer === 'string' ? data.answer : (data.answer?.full_text || ''));

        botDiv.className = 'msg bot' + (isArabic(answerText) ? ' rtl' : '');

        // 1. Render formatted markdown answer
        let finalHtml = renderMarkdown(answerText);

        // 2. Render model, latency, and reference links inside collapsed debug panel
        let sourcesDebug = '';
        if (data.sources && data.sources.length > 0) {
          sourcesDebug = '<div style="margin-top:6px; border-top:1px solid rgba(51,65,85,0.4); padding-top:4px; font-size:0.65rem;">' +
            '<div><strong>Referenced Sources:</strong></div>' +
            data.sources.map(s => `<div>[${s.id || s.index}] <a href="${escapeHtml(s.url)}" target="_blank" style="color:#38bdf8; text-decoration:none;">${escapeHtml(s.title || s.url)}</a></div>`).join('') +
            '</div>';
        }

        finalHtml += `
          <details class="debug-panel">
            <summary>Debug Info</summary>
            <div class="debug-content">
              <span><strong>Model:</strong> ${escapeHtml(data.model_used || 'unknown')}</span>
              <span><strong>Latency:</strong> ${data.latency_ms}ms</span>
              ${data.cached ? '<span class="cached-badge">Cached</span>' : ''}
              ${sourcesDebug}
            </div>
          </details>
        `;

        botDiv.innerHTML = finalHtml;

      } catch (err) {
        botDiv.textContent = 'Network error or service unavailable. Please try again.';
      }

      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_ui():
    """Serve the single-page chat UI (DAR-25)."""
    return HTML_UI
