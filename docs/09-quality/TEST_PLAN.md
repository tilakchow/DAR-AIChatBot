# Test Plan & Verification Results

- **Tracked in:** DAR-46
- **Test Date:** 2026-11-18
- **Framework:** `pytest` / Python `unittest.mock`

---

## Test Suites & Coverage Scope

| Suite | File | Test Count | Scope & Verification | Status |
|---|---|---|---|---|
| **Robots Checker (DAR-8)** | `tests/test_robots_checker.py` | 27 tests | RFC 9309 wildcard matching (`*`, `$`), crawl-delay parsing, DarGlobal wildcard disallows, Wasalt `/search` rejection | **PASS (27/27)** |
| **Polite Fetcher (DAR-10)** | `tests/test_fetcher.py` | 19 tests | Per-host min delay (1.5s), max 3 retries on 429/5xx, exponential backoff, Imperva/Cloudflare challenge detection | **PASS (19/19)** |
| **Sitemap Discovery (DAR-9)** | `tests/test_sitemap.py` | 23 tests | XML urlset and sitemapindex parsing, `.xml.gz` decompression, URL entity normalization | **PASS (23/23)** |
| **Scope & Extractor (DAR-11, 12)** | `tests/test_scope_and_extractor.py` | 6 tests | Category path scoping, schema.org JSON-LD extraction, zero seller PII stored | **PASS (6/6)** |
| **Cleaner & Chunker (DAR-15, 16)** | `tests/test_cleaner_and_chunker.py` | 9 tests | Regex phone/email scrubbing, price/date preservation, FAQ and listing chunk formatting | **PASS (9/9)** |
| **RAG & API Integration (DAR-20–26)** | `tests/test_api_and_rag.py` | 18 tests | BM25 retrieval, guardrails validation, injection blocking, OpenRouter client fallback, FastAPI endpoints | **PASS (18/18)** |
| **Evaluation Benchmark (DAR-36–38)** | `tests/eval_questions.json` | 22 cases | Accuracy, refusal, citation rate, and latency benchmarks | **PASS (22/22)** |

**Total Automated Test Count:** **124 tests** executed and passing.
Zero live OpenRouter API calls made during tests (all external network boundaries mocked).
