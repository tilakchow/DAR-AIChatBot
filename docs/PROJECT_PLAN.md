# DAR Project Plan (Linear Status Model)

- **Project Lead:** Varun
- **Target Deadline:** Friday, 20 November 2026
- **Status Date:** 18 November 2026
- **Methodology:** Linear Issues with strict Acceptance Criteria & Honesty Rule

---

## Burndown Summary

| Milestone | Total Issues | Story Points | Done | Progress % | Status |
|---|---|---|---|---|---|
| **M1 Discovery & Requirements** | 7 | 11 | 7 | 100% | **Done** |
| **M2 Data Collection** | 7 | 15 | 7 | 100% | **Done** |
| **M3 Data Processing & Indexing** | 5 | 9 | 5 | 100% | **Done** |
| **M4 Chatbot (RAG + OpenRouter)** | 7 | 17 | 7 | 100% | **Done** |
| **M5 Containerisation** | 4 | 5 | 4 | 100% | **Done** |
| **M6 Deployment** | 5 | 6 | 2 | 40% | **In Progress (Awaiting Live Host Push)** |
| **M7 Evaluation & QA** | 5 | 8 | 5 | 100% | **Done** |
| **M8 Documentation & Submission** | 8 | 14 | 8 | 100% | **Done** |
| **TOTAL** | **48** | **85** | **45** | **94%** | **In Progress / Deployment Ready** |

---

## Detailed Issue Tracking (DAR-1 to DAR-48)

### Milestone M1: Discovery & Requirements
- [x] **DAR-1:** Analyse assignment brief and constraints -> **Done** (Spike, 1pt)
- [x] **DAR-2:** Review robots.txt, llms.txt and crawl rules -> **Done** (Spike, 1pt)
- [x] **DAR-3:** Map site structure and structured data -> **Done** (Spike, 2pt)
- [x] **DAR-4:** Shortlist free OpenRouter models and rate limits -> **Done** (Spike, 1pt)
- [x] **DAR-5:** Create Linear-style project plan -> **Done** (Docs, 2pt)
- [x] **DAR-6:** Write PRD (`docs/01-requirements/PRD.md`) -> **Done** (Docs, 2pt)
- [x] **DAR-7:** Write SRS (`docs/01-requirements/SRS.md`) -> **Done** (Docs, 2pt)

### Milestone M2: Data Collection
- [x] **DAR-8:** Wildcard robots.txt checker (`src/scraper/robots_checker.py`, 27 tests pass) -> **Done** (Feature, 2pt)
- [x] **DAR-9:** Sitemap discovery for XML and gzipped sitemaps (`src/scraper/sitemap.py`, 23 tests pass) -> **Done** (Feature, 2pt)
- [x] **DAR-10:** Polite fetcher with rate limiting and retries (`src/scraper/fetcher.py`, 19 tests pass) -> **Done** (Feature, 3pt)
- [x] **DAR-11:** Define crawl scope and caps per site (`src/scraper/scope.py`, 4 tests pass) -> **Done** (Task, 1pt)
- [x] **DAR-12:** Extract JSON-LD facts, FAQs and listings (`src/scraper/extractor.py`, 2 tests pass) -> **Done** (Feature, 3pt)
- [x] **DAR-13:** Run full scrape and record crawl log (`src/scraper/crawl_runner.py`) -> **Done** (Task, 2pt)
- [x] **DAR-14:** Spike fallback if bot protection blocks static fetching (`ADR-0004`) -> **Done** (Spike, 2pt)

### Milestone M3: Data Processing & Indexing
- [x] **DAR-15:** Clean text and scrub personal data (`src/processing/cleaner.py`, 5 tests pass) -> **Done** (Feature, 2pt)
- [x] **DAR-16:** Chunk documents by page, FAQ and listing (`src/processing/chunker.py`, 4 tests pass) -> **Done** (Feature, 2pt)
- [x] **DAR-17:** Deduplicate pages and listings (6 duplicates dropped) -> **Done** (Task, 1pt)
- [x] **DAR-18:** Build BM25 and embedding index (`src/processing/index_builder.py`) -> **Done** (Feature, 3pt)
- [x] **DAR-19:** Generate `data/summary.json` (179 chunks, 90 FAQs, 28 listings) -> **Done** (Task, 1pt)

### Milestone M4: Chatbot (RAG + OpenRouter)
- [x] **DAR-20:** Hybrid retriever with reciprocal rank fusion (`src/rag/retriever.py`) -> **Done** (Feature, 3pt)
- [x] **DAR-21:** Versioned system prompt v1.0.0 (`src/rag/prompt.py`, `docs/05-ai/PROMPTS.md`) -> **Done** (Task, 2pt)
- [x] **DAR-22:** OpenRouter client with model fallbacks (`src/rag/openrouter_client.py`) -> **Done** (Feature, 2pt)
- [x] **DAR-23:** Guardrails, rate limiting and answer cache (`src/rag/guardrails.py`) -> **Done** (Feature, 3pt)
- [x] **DAR-24:** Expose chat, health and stats API endpoints (`src/api/main.py`, `openapi.yaml`) -> **Done** (Feature, 2pt)
- [x] **DAR-25:** Build chat UI with sources and RTL support (`src/api/main.py`) -> **Done** (Feature, 2pt)
- [x] **DAR-26:** Unit and integration tests (`tests/test_api_and_rag.py`, 18 tests pass) -> **Done** (Task, 3pt)

### Milestone M5: Containerisation
- [x] **DAR-27:** Write Dockerfile with non-root user and healthcheck (`Dockerfile`) -> **Done** (Feature, 2pt)
- [x] **DAR-28:** Add docker-compose for local runs (`docker-compose.yml`) -> **Done** (Task, 1pt)
- [x] **DAR-29:** Create `.env.example` and config reference (`docs/07-reference/CONFIG.md`) -> **Done** (Docs, 1pt)
- [x] **DAR-30:** Verify image and Docker quick start (`docs/06-howto/RUN_WITH_DOCKER.md`) -> **Done** (Task, 1pt)

### Milestone M6: Deployment
- [x] **DAR-31:** Choose hosting platform (`docs/03-adrs/ADR-0005.md`) -> **Done** (Spike, 1pt)
- [ ] **DAR-32:** Deploy container to chosen host (`docs/06-howto/DEPLOY.md`) -> **In Progress** (Awaiting user cloud repo remote, 2pt)
- [ ] **DAR-33:** Configure production secrets -> **In Progress** (Configured via host secrets manager / `.env`, 1pt)
- [ ] **DAR-34:** Smoke-test the live public URL -> **In Progress** (Pre-tested locally on `:7860/health`, pending public URL, 1pt)
- [x] **DAR-35:** Write runbook and monitoring notes (`docs/08-ops/RUNBOOK.md`, `MONITORING.md`) -> **Done** (Docs, 1pt)

### Milestone M7: Evaluation & QA
- [x] **DAR-36:** Write evaluation question set (`tests/eval_questions.json`, 22 test cases) -> **Done** (Task, 2pt)
- [x] **DAR-37:** Implement evaluation runner (`src/eval/runner.py`) -> **Done** (Feature, 2pt)
- [x] **DAR-38:** Run evaluation and record results (`data/evaluation_results.json`, `docs/09-quality/EVALUATION.md`) -> **Done** (Task, 1pt)
- [x] **DAR-39:** Test OWASP LLM Top 10 guardrails (`docs/09-quality/GUARDRAILS.md`) -> **Done** (Task, 2pt)
- [x] **DAR-40:** Scan repository for secrets (verified clean, 0 API keys in git) -> **Done** (Task, 1pt)

### Milestone M8: Documentation & Submission
- [x] **DAR-41:** Write README, CHANGELOG, LICENSE, SECURITY, CONTRIBUTING -> **Done** (Docs, 2pt)
- [x] **DAR-42:** Write architecture doc, C4 diagrams and ADRs 0001–0005 -> **Done** (Docs, 3pt)
- [x] **DAR-43:** Write datasheet and data pipeline doc (`docs/04-data/`) -> **Done** (Docs, 2pt)
- [x] **DAR-44:** Write model card and prompt doc (`docs/05-ai/`) -> **Done** (Docs, 2pt)
- [x] **DAR-45:** Write how-to guides and reference docs (`docs/06-howto/`, `docs/07-reference/`) -> **Done** (Docs, 2pt)
- [x] **DAR-46:** Write operations and quality docs (`docs/08-ops/`, `docs/09-quality/`) -> **Done** (Docs, 1pt)
- [x] **DAR-47:** Draft submission summary for reply email (`docs/10-submission/SUBMISSION.md`) -> **Done** (Docs, 1pt)
- [x] **DAR-48:** Run Definition of Done checklist (`docs/10-submission/FINAL_REPORT.md`) -> **Done** (Task, 1pt)
