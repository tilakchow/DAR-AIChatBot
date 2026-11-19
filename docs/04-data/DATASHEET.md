# Datasheet for DAR Real Estate Dataset

- **Tracked in:** DAR-43
- **Format:** Gebru et al., "Datasheets for Datasets" (CACM 2021)
- **Source of Truth:** Generated directly from `data/summary.json` (18 Nov 2026)

---

## 1. Motivation

- **For what purpose was the dataset created?**  
  To provide verified, grounded domain context for the DAR AI Property Assistant, answering user queries regarding DarGlobal luxury real estate developments and Wasalt Saudi Arabian listings.
- **Who created the dataset?**  
  Tilak, Junior AI Engineer candidate, as part of the DarGlobal Applied AI Technical Assignment.

---

## 2. Composition

The dataset contains processed, cleaned, and chunked text passages derived from public web pages.

### Measured Dataset Statistics (from `data/summary.json`)

| Metric | Measured Value |
|---|---|
| **Total Processed Chunks** | **179** |
| DarGlobal Chunks | **151** |
| Wasalt Chunks | **28** |
| **FAQ Pair Chunks** | **90** |
| **Listing Offer Chunks** | **28** |
| **Page Text Chunks** | **61** |
| Primary Language | English (`en`: 179, with bilingual Arabic transliteration support) |
| Average Chunk Length | **651.4 characters** |
| Minimum / Maximum Chunk Length | 136 / 1,553 characters |
| Raw DarGlobal Projects/Pages Indexed | **19** |
| Raw Wasalt Listings Extracted | **28** |
| Duplicate Pages Dropped | **6** |

---

## 3. Collection Process

- **How was the data collected?**  
  Via an automated polite crawler (`src/scraper/crawl_runner.py`) using Playwright with Chromium headless to execute JavaScript challenges transparently.
- **When was the data collected?**  
  18 November 2026.
- **Crawl Metrics:**
  - DarGlobal URLs attempted: 25 (18 OK, 7 HTTP 404/500 errors logged).
  - Wasalt URLs attempted: 17 (1 OK yielding 28 property offers, 16 Cloudflare 403 challenge pages blocked and skipped).

---

## 4. Wasalt Usage Terms & Personal Data Scrubbing (Strict Compliance)

1. **Non-Commercial Demonstrator:** Complies with Wasalt's `llms.txt` term `AllowCommercialUse: No`.
2. **Zero Seller / Agent PII:** Wasalt category pages contain agent names, private telephone numbers, and WhatsApp links.
   - All `seller` and `agent` dictionaries are dropped at extraction (`src/scraper/extractor.py`).
   - All international and Saudi phone numbers (e.g. `+966 5x`, `05x`) and emails are scrubbed (`src/processing/cleaner.py`).
   - Verified: **0 personal names or phone numbers exist anywhere in `chunks.json`**.
3. **Mandatory Attribution:** The assistant attaches `"Source: Wasalt.sa"` to all Wasalt-derived answers.
4. **Live Listing Links:** All Wasalt listings include live URLs so users can verify pricing on the official portal.
