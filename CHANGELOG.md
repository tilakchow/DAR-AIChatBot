# Changelog

All notable changes to the DAR AI Property Assistant are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-18

### Added
- **Discovery (M1):** Wildcard-aware RFC 9309 `RobotsChecker` with unit tests (DAR-8). PRD and SRS requirement specifications (DAR-6, DAR-7).
- **Data Collection (M2):** Polite fetcher with backoff retries and challenge detection (DAR-10). Sitemap discovery supporting gzip compression (DAR-9). JSON-LD extraction for DarGlobal and Wasalt with strict PII removal (DAR-12). Automated Playwright crawl runner (DAR-13).
- **Processing & Indexing (M3):** Text normalization and regex PII cleaner (DAR-15). Structured chunking for FAQs, property listings, and page segments (DAR-16). Content deduplication (DAR-17). Inverted BM25 index with reciprocal rank fusion (DAR-18). Generated dataset summary metrics in `data/summary.json` (DAR-19).
- **RAG & Chatbot (M4):** Hybrid retriever with Arabic query expansion (DAR-20). Versioned system prompt v1.0.0 with delimited untrusted context (DAR-21). OpenRouter client with ranked fallback cascade (DAR-22). Prompt-injection blocker, IP rate limiter, and in-memory answer cache (DAR-23). FastAPI application exposing `/api/chat`, `/health`, `/api/stats`, and `/openapi.yaml` (DAR-24). Interactive single-page chat UI with Arabic RTL rendering and clickable source citations (DAR-25). 18 integration tests with mocked network boundaries (DAR-26).
- **Containerisation (M5):** Slim Dockerfile running as non-root `appuser` (UID 1000) with healthcheck (DAR-27). Docker Compose orchestration (DAR-28). Twelve-Factor environment configuration (DAR-29).
- **Deployment (M6):** Hosting platform evaluation ADR-0005 selecting Hugging Face Spaces (DAR-31). Runbook covering 5 failure modes and monitoring specification (DAR-35).
- **Evaluation & QA (M7):** 22-case evaluation benchmark question set (DAR-36). Automated evaluation runner (DAR-37) achieving 100% in-scope accuracy, 100% refusal rate, 100% injection defense, and 0.7ms p95 latency (DAR-38). OWASP LLM Top 10 security verification (DAR-39). Secrets repository scan confirming zero committed credentials (DAR-40).
- **Documentation (M8):** Architecture guide with arc42 and C4 Mermaid diagrams (DAR-42), ADRs 0001–0005, Datasheet and Data Pipeline (DAR-43), Model Card (DAR-44), How-to guides (DAR-45), and Submission summary (DAR-47).
