# DAR — DarGlobal AI Property Assistant

AI-powered property assistant answering queries on DarGlobal international luxury real estate and Wasalt Saudi property listings using Retrieval-Augmented Generation (RAG) and free OpenRouter language models.

## Live Application
- **Live URL:** `http://localhost:7860` (or configured cloud deployment)
- **API Documentation:** `/docs` (Swagger UI) and `/openapi.yaml`

---

## Key Capabilities
- **Factual Grounding:** Answers are generated strictly from scraped data with `[n]` bracket citations.
- **Bilingual & RTL:** Native support for English and Arabic text with automatic right-to-left UI rendering.
- **Zero-Cost Operation:** Uses free OpenRouter models with a cascade fallback strategy.
- **OWASP LLM Guardrails:** Built-in protection against prompt injection, rate-limiting, and PII protection.
- **Wasalt Policy Compliant:** Shows `"Source: Wasalt.sa"` on Wasalt data; never stores seller personal phone numbers or agent names.

---

## Architecture & Technology Stack

| Layer | Component | Technology |
|---|---|---|
| **Web Server** | REST API & Chat UI | Python 3.11, FastAPI, Uvicorn |
| **Data Ingestion** | Polite Web Crawler | Playwright, RobotsChecker (RFC 9309) |
| **Indexing** | Hybrid Search | Inverted BM25 Index, Reciprocal Rank Fusion |
| **LLM Tier** | Model Provider | OpenRouter Free Tier (Nemotron, Llama 3.3, Gemini) |
| **Security** | Defense in Depth | Regex Guardrails, IP Rate Limiter, Answer Cache |
| **Container** | Packaging | Docker, Docker Compose (Non-root user) |

---

## Quick Start with Docker (3 Commands)

```bash
# 1. Clone repository
git clone https://github.com/dar-project/dar-chatbot.git
cd dar-chatbot

# 2. Configure environment
cp .env.example .env
# Edit .env and set: OPENROUTER_API_KEY=your_key_here

# 3. Start application
docker compose up -d
```

Open `http://localhost:7860` in your web browser.

---

## Running Automated Tests

```bash
# Run full test suite (124 tests)
pytest
```

---

## Documentation Index
- [Architecture & C4 Diagrams](docs/02-architecture/ARCHITECTURE.md)
- [Architecture Decision Records (ADRs)](docs/03-adrs/)
- [Dataset Datasheet](docs/04-data/DATASHEET.md)
- [Model Card & Prompts](docs/05-ai/)
- [Local Setup & Docker Guide](docs/06-howto/)
- [API Specification](docs/07-reference/API.md)
- [Operations Runbook & Monitoring](docs/08-ops/)
- [Evaluation & Benchmark Results](docs/09-quality/EVALUATION.md)
- [Assignment Submission Summary](docs/10-submission/SUBMISSION.md)
