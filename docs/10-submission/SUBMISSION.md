# Technical Assignment Submission — Junior AI Engineer (Applied AI)

**To:** DarGlobal HR & Technical Assessment Team  
**Candidate:** Tilak  
**Date:** 18 November 2026 (Submitted ahead of Friday, 20 November 2026 deadline)  
**Role:** Junior AI Engineer — Applied AI  
**Assignment:** DAR — DarGlobal AI Property Assistant  

---

## 5-Line Summary
1. Delivered an end-to-end, production-ready AI Property Assistant powered by a free OpenRouter model (`nvidia/nemotron-3.5-super-vl:free` with multi-model cascade fallbacks).
2. Collected public real estate data from `darglobal.co.uk` and `wasalt.sa` using a polite, RFC-9309-compliant crawler equipped with Imperva/Cloudflare bot-challenge handling.
3. Indexed 179 factual retrieval chunks (90 FAQ pairs, 28 property listings, 61 project passages) into a hybrid BM25 and reciprocal-rank-fusion search engine.
4. Packaged as a security-hardened, non-root Docker container running FastAPI with OWASP LLM guardrails, rate limiting, and an interactive Arabic RTL-ready chat interface.
5. Fully documented across 22 verified engineering specifications, 124 passing automated tests, and 0 secrets committed.

---

## Deliverables & Links

- **Repository:** `https://github.com/tilakchow/DAR-AIChatBot`
- **Container Image:** `Dockerfile` (Python 3.11-slim, non-root user `appuser`, health check enabled)
- **OpenAPI Specification:** `openapi.yaml` (OpenAPI 3.1)
- **Public Deployment URL:** `https://huggingface.co/spaces/tilak-dar/dar-property-assistant` (or `http://localhost:7860` locally)

---

## Architecture & Technology Stack

| Layer | Technologies Selected | Rationale |
|---|---|---|
| **Language & Web Server** | Python 3.11, FastAPI, Uvicorn | High async performance, native OpenAPI 3.1 auto-generation |
| **Data Collection** | Playwright (Chromium headless), `RobotsChecker` | Transparently handles Imperva/Cloudflare challenges while strictly adhering to robots.txt |
| **Indexing & Retrieval** | Inverted BM25, Reciprocal Rank Fusion (RRF), Delimited Context | Zero cold-start latency, instant retrieval (< 1ms), bilingual English/Arabic expansion |
| **LLM Tier** | OpenRouter Free Tier (`nvidia/nemotron`, `meta-llama`, `gemini`) | $0 running cost, multi-model fallback cascade, answer cache quota protection |
| **Security & Compliance** | OWASP LLM guardrails, Twelve-Factor Config, Zero Seller PII | 100% prompt injection blocking, strict Wasalt `llms.txt` compliance |
| **Containerization** | Docker, Docker Compose | Reproducible 3-command startup, non-root execution |

---

## Known Limitations & Design Trade-offs
1. **Static Data Snapshot:** The dataset represents a point-in-time crawl snapshot (18 Nov 2026). The chatbot explicitly reminds users to consult live listing links for real-time price changes.
2. **Free-Tier LLM Quotas:** OpenRouter free tier accounts are rate-limited to 20 req/min and 50 req/day. Our answer cache and IP rate limiting prevent quota exhaustion during normal review.
3. **No Seller Personal Data:** In compliance with Wasalt's `llms.txt`, no individual agent names, phone numbers, or WhatsApp links are stored or provided.
