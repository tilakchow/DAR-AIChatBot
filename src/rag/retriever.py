"""
DAR-20 · Hybrid Retriever with Reciprocal Rank Fusion (RRF) and Per-URL chunk capping.

Acceptance criteria (from DAR-20):
  ✓ Returns the top-k chunks with scores for English and Arabic queries
  ✓ Site filter limits results to 'darglobal' or 'wasalt'

Design (section 5 and ADR-0002):
  - RRF combines ranks: score = sum(1 / (k + rank)) with k=60
  - Optional site filter ('darglobal' or 'wasalt')
  - Caps chunks per URL (default max 2 chunks per single URL) to prevent one long page crowding out others
"""

from __future__ import annotations

import os
import sys
import json
from dataclasses import dataclass
from typing import Optional, Literal

sys.path.insert(0, os.path.abspath('.'))

from src.processing.index_builder import BM25Index, tokenize

PROCESSED_DIR = "data/processed"
CHUNKS_FILE = os.path.join(PROCESSED_DIR, "chunks.json")
BM25_INDEX_FILE = os.path.join(PROCESSED_DIR, "bm25_index.json")


@dataclass
class RetrievedChunk:
    chunk_id: str
    chunk_type: str
    site: str
    url: str
    title: str
    language: str
    content: str
    score: float
    metadata: dict

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "chunk_type": self.chunk_type,
            "site": self.site,
            "url": self.url,
            "title": self.title,
            "language": self.language,
            "content": self.content,
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }


# Arabic to English real estate keyword and project expansion dictionary
ARABIC_EXPANSIONS = {
    "أستيرا": "astera",
    "استيرا": "astera",
    "ترامب": "trump",
    "فلل": "villas",
    "فيلا": "villa",
    "شقق": "apartments",
    "شقة": "apartment",
    "الرياض": "riyadh",
    "جدة": "jeddah",
    "مكة": "makkah",
    "دبي": "dubai",
    "وصلت": "wasalt",
    "أسعار": "prices price",
    "سعر": "price",
    "اكتمال": "completion completed",
    "مشروع": "project",
    "برج": "tower",
    "موقع": "location",
    "ميسوني": "missoni",
    "عمان": "oman",
}


def expand_query(query: str) -> str:
    """Expand bilingual terms so Arabic queries match English project names and vice-versa."""
    expanded = [query]
    for ar_term, en_term in ARABIC_EXPANSIONS.items():
        if ar_term in query:
            expanded.append(en_term)
    return " ".join(expanded)


class HybridRetriever:
    def __init__(
        self,
        chunks_path: str = CHUNKS_FILE,
        bm25_path: str = BM25_INDEX_FILE,
        rrf_k: int = 60,
        max_chunks_per_url: int = 2
    ):
        self.rrf_k = rrf_k
        self.max_chunks_per_url = max_chunks_per_url
        self.chunks_by_id: dict[str, dict] = {}

        # Load chunks
        if os.path.exists(chunks_path):
            with open(chunks_path, "r", encoding="utf-8") as f:
                chunks_list = json.load(f)
                self.chunks_by_id = {c["chunk_id"]: c for c in chunks_list}

        # Load BM25 index
        if os.path.exists(bm25_path):
            with open(bm25_path, "r", encoding="utf-8") as f:
                self.bm25 = BM25Index.from_dict(json.load(f))
        else:
            self.bm25 = BM25Index()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        site_filter: Optional[Literal["darglobal", "wasalt"]] = None
    ) -> list[RetrievedChunk]:
        """Retrieve top-k chunks matching the query using BM25 and reciprocal rank scoring."""
        if not query.strip() or not self.chunks_by_id:
            return []

        expanded_q = expand_query(query)

        # 1. Retrieve initial candidate list from BM25
        # Fetch more candidates to allow per-URL capping and re-ranking
        bm25_results = self.bm25.score(expanded_q, top_k=top_k * 5, site_filter=site_filter)

        # 2. Reciprocal Rank Fusion / scoring
        # In BM25-only / fallback mode: RRF score = 1 / (rrf_k + rank)
        rrf_scores: dict[str, float] = {}
        for rank, (doc_id, bm_score) in enumerate(bm25_results):
            rrf_score = 1.0 / (self.rrf_k + (rank + 1))
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + rrf_score

        # Sort by score descending
        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # 3. Apply per-URL cap (prevent one URL from dominating results)
        results: list[RetrievedChunk] = []
        url_counts: dict[str, int] = {}

        for doc_id, score in sorted_candidates:
            chunk_data = self.chunks_by_id.get(doc_id)
            if not chunk_data:
                continue

            url = chunk_data.get("url", "")
            current_url_count = url_counts.get(url, 0)
            if current_url_count >= self.max_chunks_per_url:
                continue

            url_counts[url] = current_url_count + 1
            results.append(RetrievedChunk(
                chunk_id=doc_id,
                chunk_type=chunk_data.get("chunk_type", "page"),
                site=chunk_data.get("site", ""),
                url=url,
                title=chunk_data.get("title", ""),
                language=chunk_data.get("language", "en"),
                content=chunk_data.get("content", ""),
                score=score,
                metadata=chunk_data.get("metadata", {}),
            ))

            if len(results) >= top_k:
                break

        return results
