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
    query: str = Field(..., example="What are the starting prices for The Astera by Aston Martin?", max_length=1000)
    site: Optional[Literal["darglobal", "wasalt"]] = Field(None, description="Optional filter by property portal")


class SourceItem(BaseModel):
    index: int
    title: str
    url: str
    site: str
    chunk_type: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    model_used: str
    latency_ms: float
    cached: bool = False


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
        resp = {
            "answer": "I don't have enough verified information in the DarGlobal or Wasalt database to answer this question.",
            "sources": [],
            "model_used": "rules-engine",
            "latency_ms": latency,
            "cached": False
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
        response_data = {
            "answer": completion.content,
            "sources": sources,
            "model_used": completion.model_used,
            "latency_ms": total_latency,
            "cached": False
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
  <title>DAR — DarGlobal & Wasalt AI Property Assistant</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --user-msg-bg: #0369a1;
      --bot-msg-bg: #1e293b;
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
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
    }
    header {
      background: var(--card-bg);
      border-bottom: 1px solid var(--border);
      padding: 1rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    header h1 { font-size: 1.25rem; font-weight: 700; color: var(--accent); }
    header p { font-size: 0.85rem; color: var(--text-muted); }
    .badge {
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      border: 1px solid var(--accent);
    }
    #chat-container {
      flex: 1;
      overflow-y: auto;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }
    .msg {
      max-width: 80%;
      padding: 1rem 1.25rem;
      border-radius: 1rem;
      line-height: 1.6;
      font-size: 0.95rem;
      position: relative;
    }
    .msg.user {
      align-self: flex-end;
      background: var(--user-msg-bg);
      color: #fff;
      border-bottom-right-radius: 0.25rem;
    }
    .msg.bot {
      align-self: flex-start;
      background: var(--bot-msg-bg);
      border: 1px solid var(--border);
      border-bottom-left-radius: 0.25rem;
    }
    .msg.rtl {
      direction: rtl;
      text-align: right;
    }
    .sources-box {
      margin-top: 0.75rem;
      padding-top: 0.75rem;
      border-top: 1px solid var(--border);
      font-size: 0.8rem;
    }
    .sources-box a {
      color: var(--accent);
      text-decoration: none;
      display: inline-block;
      margin-right: 0.75rem;
    }
    .sources-box a:hover { text-decoration: underline; }
    .attribution-tag {
      font-size: 0.75rem;
      color: #fbbf24;
      font-weight: 600;
      margin-top: 0.4rem;
    }
    .meta-tag {
      font-size: 0.7rem;
      color: var(--text-muted);
      margin-top: 0.5rem;
    }
    #input-form {
      background: var(--card-bg);
      border-top: 1px solid var(--border);
      padding: 1rem 1.5rem;
      display: flex;
      gap: 0.75rem;
    }
    #query-input {
      flex: 1;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      color: var(--text);
      padding: 0.75rem 1rem;
      font-size: 0.95rem;
      outline: none;
    }
    #query-input:focus { border-color: var(--accent); }
    button {
      background: var(--accent);
      color: #0f172a;
      font-weight: 700;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 0.75rem;
      cursor: pointer;
      transition: background 0.2s;
    }
    button:hover { background: var(--accent-hover); color: #fff; }
    .sample-bar {
      display: flex;
      gap: 0.5rem;
      overflow-x: auto;
      padding: 0.5rem 1.5rem;
      background: #1e293b;
      border-top: 1px solid var(--border);
    }
    .sample-chip {
      background: #0f172a;
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 0.35rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      cursor: pointer;
      white-space: nowrap;
    }
    .sample-chip:hover { color: var(--accent); border-color: var(--accent); }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>DAR — AI Property Assistant</h1>
      <p>DarGlobal Luxury Developments & Wasalt Saudi Property Listings</p>
    </div>
    <div class="badge">OpenRouter RAG · Free Tier</div>
  </header>

  <div id="chat-container">
    <div class="msg bot">
      Hello! I am DAR, your AI property assistant. You can ask me questions about DarGlobal's international luxury residences (such as The Astera, Trump International Towers, Les Vagues, DG1) or Wasalt's verified property listings in Saudi Arabia.
      <br><br>
      Feel free to ask in English or Arabic (العربية).
    </div>
  </div>

  <div class="sample-bar">
    <div class="sample-chip" onclick="ask('What are the starting prices for The Astera?')">Starting prices for The Astera</div>
    <div class="sample-chip" onclick="ask('Tell me about Trump International Hotel & Tower Dubai.')">Trump Tower Dubai</div>
    <div class="sample-chip" onclick="ask('What villas are for sale in Riyadh on Wasalt?')">Villas for sale in Riyadh</div>
    <div class="sample-chip" onclick="ask('ما هي تفاصيل مشروع ذا أستيرا؟')">تفاصيل مشروع ذا أستيرا (عربي)</div>
  </div>

  <form id="input-form" onsubmit="sendMsg(event)">
    <input type="text" id="query-input" placeholder="Ask about DarGlobal projects or Wasalt property listings..." autocomplete="off">
    <button type="submit" id="send-btn">Send</button>
  </form>

  <script>
    const chatContainer = document.getElementById('chat-container');
    const input = document.getElementById('query-input');

    function isArabic(text) {
      return /[\u0600-\u06FF]/.test(text);
    }

    function ask(q) {
      input.value = q;
      document.getElementById('input-form').dispatchEvent(new Event('submit'));
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

        botDiv.className = 'msg bot' + (isArabic(data.answer) ? ' rtl' : '');
        botDiv.innerHTML = data.answer.replace(/\\n/g, '<br>');

        // Check if Wasalt attribution required
        const hasWasalt = (data.sources || []).some(s => s.site === 'wasalt');
        if (hasWasalt && !data.answer.includes('Wasalt.sa')) {
          const attr = document.createElement('div');
          attr.className = 'attribution-tag';
          attr.textContent = 'Source: Wasalt.sa';
          botDiv.appendChild(attr);
        }

        // Add source citations
        if (data.sources && data.sources.length > 0) {
          const sBox = document.createElement('div');
          sBox.className = 'sources-box';
          sBox.innerHTML = '<strong>Verified Sources:</strong><br>';
          data.sources.forEach(s => {
            const a = document.createElement('a');
            a.href = s.url;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            a.textContent = `[${s.index}] ${s.title || s.url}`;
            sBox.appendChild(a);
          });
          botDiv.appendChild(sBox);
        }

        // Latency and model metadata
        const meta = document.createElement('div');
        meta.className = 'meta-tag';
        meta.textContent = `Model: ${data.model_used} · Latency: ${data.latency_ms}ms ${data.cached ? '· (Cached)' : ''}`;
        botDiv.appendChild(meta);

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
