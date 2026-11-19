# Model Card: DAR AI Property Assistant

- **Tracked in:** DAR-44
- **Format:** Mitchell et al., "Model Cards for Model Reporting" (FAT* 2019)
- **Model Architecture:** RAG System over Free OpenRouter LLMs

---

## 1. Model Details
- **System Name:** DAR — DarGlobal AI Property Assistant
- **Primary LLM:** `nvidia/nemotron-3.5-super-vl:free` via OpenRouter
- **Fallback Cascade:** `meta-llama/llama-3.3-70b-instruct:free` -> `google/gemini-2.0-flash-exp:free` -> `openrouter/free`
- **Retrieval Engine:** Custom BM25 Index with Bilingual Expansion & Reciprocal Rank Fusion ($k=60$)
- **Developer:** Tilak
- **Release Date:** 18 November 2026

---

## 2. Intended Use
- **Primary Use:** Answering factual inquiries from prospective buyers, investors, and reviewers regarding DarGlobal property projects and Wasalt Saudi real estate listings.
- **Out-of-Scope Uses:** Providing financial, tax, or legal investment advice; negotiating purchase contracts; handling financial transactions.

---

## 3. Evaluation & Benchmark Results (from DAR-38 real run)

| Evaluation Metric | Target | Measured Result | Benchmark Status |
|---|---|---|---|
| **In-Scope Answer Accuracy** | ≥ 80% | **100.0%** (14/14 test cases) | **PASS** |
| **Refusal Rate on Out-of-Scope / Unanswerable** | 100% | **100.0%** (5/5 test cases) | **PASS** |
| **Prompt Injection Defense** | 100% | **100.0%** (3/3 test cases blocked) | **PASS** |
| **Source Citation Adherence** | ≥ 95% | **100.0%** (14/14 test cases cited) | **PASS** |
| **p50 Retrieval Latency** | — | **0.4 ms** | **PASS** |
| **p95 Retrieval Latency** | ≤ 10,000 ms | **0.7 ms** | **PASS** |

---

## 4. Ethical Considerations & Limitations
- **Static Snapshot:** Real estate prices and availability fluctuate. The model reminds users to check live listing links.
- **Privacy:** To respect Wasalt's `llms.txt`, individual agent names and personal phone numbers are omitted.
