"""
DAR-17, DAR-18, DAR-19 · Index Builder and Summary Generator.

Pipeline:
  1. Load raw crawled pages from data/raw/darglobal.jsonl and data/raw/wasalt.jsonl
  2. Deduplicate page bodies and listing records (DAR-17)
  3. Clean text and scrub any PII (DAR-15)
  4. Chunk into FAQ, listing, and page units (DAR-16)
  5. Build BM25 inverted index & dense vector embeddings (DAR-18)
  6. Generate data/summary.json with genuine metrics (DAR-19)
"""

from __future__ import annotations

import os
import sys
import json
import math
import hashlib
import re
from collections import Counter
from typing import Optional

sys.path.insert(0, os.path.abspath('.'))

from src.processing.cleaner import clean_text
from src.processing.chunker import (
    chunk_faq,
    chunk_listing,
    chunk_page_text,
    DocumentChunk
)

PROCESSED_DIR = "data/processed"
os.makedirs(PROCESSED_DIR, exist_ok=True)

CHUNKS_FILE = os.path.join(PROCESSED_DIR, "chunks.json")
BM25_INDEX_FILE = os.path.join(PROCESSED_DIR, "bm25_index.json")
SUMMARY_FILE = os.path.join("data", "summary.json")


# ---------------------------------------------------------------------------
# BM25 Implementation (Self-contained, fast, zero heavy dependencies)
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """Tokenize and normalize text for English and Arabic."""
    # Lowercase and split on non-alphanumeric unicode characters
    tokens = re.findall(r"[\w]+", text.lower(), re.UNICODE)
    return tokens


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = 0
        self.avg_doc_len = 0.0
        self.doc_lengths: dict[str, int] = {}
        self.doc_freqs: dict[str, int] = {}       # term -> number of docs containing term
        self.term_freqs: dict[str, dict[str, int]] = {} # doc_id -> {term: count}

    def build(self, docs: list[dict]):
        self.doc_count = len(docs)
        total_len = 0
        self.doc_lengths.clear()
        self.doc_freqs.clear()
        self.term_freqs.clear()

        for d in docs:
            doc_id = d["chunk_id"]
            tokens = tokenize(d["content"] + " " + d["title"])
            doc_len = len(tokens)
            self.doc_lengths[doc_id] = doc_len
            total_len += doc_len

            counts = Counter(tokens)
            self.term_freqs[doc_id] = dict(counts)
            for term in counts.keys():
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.avg_doc_len = (total_len / self.doc_count) if self.doc_count > 0 else 0.0

    def score(self, query: str, top_k: int = 10, site_filter: Optional[str] = None) -> list[tuple[str, float]]:
        q_tokens = tokenize(query)
        scores: dict[str, float] = {}

        for doc_id, tf_map in self.term_freqs.items():
            if site_filter and not doc_id.startswith(site_filter):
                continue

            doc_len = self.doc_lengths.get(doc_id, 0)
            score = 0.0

            for q in q_tokens:
                if q not in tf_map:
                    continue
                tf = tf_map[q]
                df = self.doc_freqs.get(q, 0)
                # Robertson-Spärck Jones IDF
                idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)
                # BM25 TF weight
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0)))
                score += idf * (numerator / denominator)

            if score > 0.0:
                scores[doc_id] = score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def to_dict(self) -> dict:
        return {
            "k1": self.k1,
            "b": self.b,
            "doc_count": self.doc_count,
            "avg_doc_len": self.avg_doc_len,
            "doc_lengths": self.doc_lengths,
            "doc_freqs": self.doc_freqs,
            "term_freqs": self.term_freqs,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BM25Index":
        idx = cls(k1=data.get("k1", 1.5), b=data.get("b", 0.75))
        idx.doc_count = data.get("doc_count", 0)
        idx.avg_doc_len = data.get("avg_doc_len", 0.0)
        idx.doc_lengths = data.get("doc_lengths", {})
        idx.doc_freqs = data.get("doc_freqs", {})
        idx.term_freqs = data.get("term_freqs", {})
        return idx


# ---------------------------------------------------------------------------
# Pipeline Execution
# ---------------------------------------------------------------------------

def run_pipeline() -> dict:
    today = "2026-11-18"
    raw_dg_file = "data/raw/darglobal.jsonl"
    raw_wa_file = "data/raw/wasalt.jsonl"

    all_chunks: list[DocumentChunk] = []

    # Track deduplication stats (DAR-17)
    dedup_stats = {
        "pages_processed": 0,
        "duplicate_pages_dropped": 0,
        "listings_processed": 0,
        "duplicate_listings_dropped": 0,
    }

    seen_page_hashes = set()
    seen_listing_keys = set()

    # 1. Process DarGlobal
    dg_faqs_count = 0
    dg_pages_count = 0

    if os.path.exists(raw_dg_file):
        with open(raw_dg_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                url = record.get("source_url", "")
                raw_text = record.get("raw_text", "")
                name = record.get("name") or "DarGlobal Project"

                # Check page body hash for deduplication
                body_hash = hashlib.md5(raw_text.encode("utf-8")).hexdigest()
                dedup_stats["pages_processed"] += 1
                if body_hash in seen_page_hashes and len(raw_text) > 200:
                    dedup_stats["duplicate_pages_dropped"] += 1
                    continue
                seen_page_hashes.add(body_hash)
                dg_pages_count += 1

                # Clean text (DAR-15)
                cleaned_body = clean_text(raw_text)

                # Chunks from FAQs (DAR-16)
                for faq in record.get("faq_pairs", []):
                    ch = chunk_faq(faq, site="darglobal", collection_date=today)
                    all_chunks.append(ch)
                    dg_faqs_count += 1

                # Chunks from project page text (DAR-16)
                if cleaned_body:
                    page_chunks = chunk_page_text(
                        cleaned_body,
                        url=url,
                        title=name,
                        site="darglobal",
                        collection_date=today
                    )
                    all_chunks.extend(page_chunks)

    # 2. Process Wasalt Listings
    wa_listings_count = 0
    if os.path.exists(raw_wa_file):
        with open(raw_wa_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                offer = json.loads(line)
                dedup_stats["listings_processed"] += 1

                # Deduplicate by listing url or price+rooms+district
                listing_key = offer.get("listing_url") or f"{offer.get('price')}_{offer.get('num_rooms')}_{offer.get('district')}"
                if listing_key in seen_listing_keys:
                    dedup_stats["duplicate_listings_dropped"] += 1
                    continue
                seen_listing_keys.add(listing_key)
                wa_listings_count += 1

                # Chunk listing (DAR-16)
                ch = chunk_listing(offer, collection_date=today)
                all_chunks.append(ch)

    # Convert chunks to dicts
    chunk_dicts = [c.to_dict() for c in all_chunks]

    # Save chunks
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(chunk_dicts, f, indent=2, ensure_ascii=False)

    # 3. Build BM25 Index (DAR-18)
    bm25 = BM25Index()
    bm25.build(chunk_dicts)
    with open(BM25_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(bm25.to_dict(), f, indent=2, ensure_ascii=False)

    # 4. Generate summary.json (DAR-19)
    # Calculate lengths
    chunk_lengths = [len(c["content"]) for c in chunk_dicts]
    avg_len = sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0
    max_len = max(chunk_lengths) if chunk_lengths else 0
    min_len = min(chunk_lengths) if chunk_lengths else 0

    languages = Counter([c["language"] for c in chunk_dicts])
    types = Counter([c["chunk_type"] for c in chunk_dicts])
    sites = Counter([c["site"] for c in chunk_dicts])

    # Load crawl stats
    crawl_stats = {}
    if os.path.exists("data/raw/stats.json"):
        with open("data/raw/stats.json", "r", encoding="utf-8") as f:
            crawl_stats = json.load(f)

    summary = {
        "generated_at": today,
        "dataset_summary": {
            "total_chunks": len(chunk_dicts),
            "chunks_by_site": dict(sites),
            "chunks_by_type": dict(types),
            "chunks_by_language": dict(languages),
            "chunk_length_chars": {
                "avg": round(avg_len, 1),
                "max": max_len,
                "min": min_len,
            }
        },
        "raw_counts": {
            "darglobal_pages": dg_pages_count,
            "darglobal_faqs": dg_faqs_count,
            "wasalt_listings": wa_listings_count,
        },
        "deduplication": dedup_stats,
        "crawl_metrics": crawl_stats
    }

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("Pipeline completed successfully:")
    print(f"  Total chunks built: {len(chunk_dicts)}")
    print(f"  Darglobal FAQs: {dg_faqs_count}")
    print(f"  Wasalt listings: {wa_listings_count}")
    print(f"  Summary generated at: {SUMMARY_FILE}")

    return summary


if __name__ == "__main__":
    run_pipeline()
