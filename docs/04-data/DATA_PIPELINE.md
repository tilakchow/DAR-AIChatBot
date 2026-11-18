# Data Ingestion & Processing Pipeline Specification

- **Tracked in:** DAR-43
- **Source of Truth:** Code in `src/scraper/` and `src/processing/`, metrics in `data/summary.json`

---

## Pipeline Overview

```
Sitemap / Seed URLs
       │
       ▼
[RobotsChecker (DAR-8)] ──> Disallowed URLs logged
       │
       ▼
[PoliteFetcher (DAR-10, 14)] ──> Rate limited (>= 1.5s delay)
       │
       ▼
[JSON-LD Extractor (DAR-12)] ──> Drops all seller/agent PII
       │
       ▼
[Text Cleaner (DAR-15)] ──> Normalizes Unicode & scrubs phone/email
       │
       ▼
[Chunker & Deduplicator (DAR-16, 17)] ──> FAQ, Listing & Page Chunks
       │
       ▼
[BM25 Index Builder (DAR-18)] ──> Saves data/processed/bm25_index.json
       │
       ▼
[Summary Generator (DAR-19)] ──> Saves data/summary.json
```

---

## Measured Pipeline Stages (18 Nov 2026 Run)

1. **Discovery & Scoping (DAR-8, DAR-9, DAR-11):**
   - DarGlobal sitemap parsed: 480 URLs discovered.
   - Scoped to 25 primary development, press, and FAQ URLs.
   - Wasalt category sitemaps inspected: 17 key regional category URLs selected across Riyadh, Jeddah, Dammam, and Makkah.

2. **Fetching & Challenge Bypass (DAR-10, DAR-14):**
   - Playwright headless Chromium executed client-side anti-bot challenges.
   - Total pages crawled: 42 attempted in 151.5 seconds.

3. **Extraction & Scrubbing (DAR-12, DAR-15):**
   - Extracted 100 raw FAQ pairs and 28 property listings.
   - 0 seller names or contact numbers retained.

4. **Deduplication (DAR-17):**
   - 6 duplicate page bodies dropped via MD5 hash comparison.
   - 0 duplicate listing IDs.

5. **Index Generation (DAR-18, DAR-19):**
   - Generated 179 total retrieval chunks.
   - Built inverted BM25 index with 2,410 unique normalized vocabulary tokens.
   - Output summary saved to `data/summary.json`.
