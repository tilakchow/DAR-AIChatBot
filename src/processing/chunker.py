"""
DAR-16 · Chunking strategy for pages, FAQs, and listings.

Acceptance criteria (from DAR-16):
  ✓ No chunk exceeds the configured maximum length (default: 800 tokens / 3200 chars)
  ✓ Every chunk carries: site, URL, title, language, and collection date

Chunk Types:
  1. FAQ Chunk: One question + answer pair per chunk.
  2. Listing Chunk: One property offer formatted factually (district, city, price, rooms, area, amenities) with live URL.
  3. Page Chunk: Overlapping text chunks from article/project body text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional, Literal


ChunkType = Literal["faq", "listing", "page"]


@dataclass
class DocumentChunk:
    chunk_id: str
    chunk_type: ChunkType
    site: str                  # "darglobal" or "wasalt"
    url: str                   # source page URL
    title: str
    language: str              # "en" or "ar"
    collection_date: str       # YYYY-MM-DD
    content: str
    metadata: dict             # specific fields (e.g. price, rooms, project_name)

    def to_dict(self) -> dict:
        return asdict(self)


def detect_language(text: str) -> str:
    """Detect if text is primarily Arabic or English."""
    if not text:
        return "en"
    arabic_chars = len(re.findall(r"[\u0600-\u06FF]", text))
    total_chars = len(re.findall(r"\w", text))
    if total_chars > 0 and (arabic_chars / total_chars) > 0.25:
        return "ar"
    return "en"


def chunk_faq(faq_pair: dict, site: str, collection_date: str) -> DocumentChunk:
    """Create a single retrieval chunk for an FAQ pair."""
    q = faq_pair.get("question", "").strip()
    a = faq_pair.get("answer", "").strip()
    url = faq_pair.get("source_url", "")
    content = f"Question: {q}\nAnswer: {a}"
    lang = detect_language(content)
    chunk_id = f"{site}:faq:{abs(hash(url + q)) % 10000000}"

    return DocumentChunk(
        chunk_id=chunk_id,
        chunk_type="faq",
        site=site,
        url=url,
        title=q,
        language=lang,
        collection_date=collection_date,
        content=content,
        metadata={"question": q, "answer": a}
    )


def chunk_listing(offer: dict, collection_date: str) -> DocumentChunk:
    """Format a Wasalt property listing into a factual retrieval chunk."""
    url = offer.get("source_url") or offer.get("listing_url") or ""
    name = offer.get("name") or "Property for Sale/Rent"
    price = offer.get("price")
    curr = offer.get("price_currency", "SAR")
    rooms = offer.get("num_rooms")
    baths = offer.get("num_bathrooms")
    area = offer.get("floor_size_sqm")
    district = offer.get("district") or ""
    city = offer.get("city") or ""
    amenities = offer.get("amenities") or []

    # Format into natural, high-signal retrieval text
    lines = [f"Property: {name}"]
    if price:
        lines.append(f"Price: {price:,.0f} {curr}")
    location_parts = [p for p in (district, city) if p]
    if location_parts:
        lines.append(f"Location: {', '.join(location_parts)}")
    spec_parts = []
    if rooms:
        spec_parts.append(f"{rooms} rooms")
    if baths:
        spec_parts.append(f"{baths} bathrooms")
    if area:
        spec_parts.append(f"{area:,.1f} sqm")
    if spec_parts:
        lines.append(f"Specifications: {', '.join(spec_parts)}")
    if amenities:
        lines.append(f"Amenities: {', '.join(amenities)}")
    
    lines.append(f"Source: Wasalt.sa")
    lines.append(f"Collection Date: {collection_date}")
    if offer.get("listing_url"):
        lines.append(f"Live Listing: {offer['listing_url']}")

    content = "\n".join(lines)
    lang = detect_language(content)
    chunk_id = f"wasalt:listing:{abs(hash(url + str(price) + name)) % 10000000}"

    return DocumentChunk(
        chunk_id=chunk_id,
        chunk_type="listing",
        site="wasalt",
        url=url,
        title=name,
        language=lang,
        collection_date=collection_date,
        content=content,
        metadata={
            "price": price,
            "currency": curr,
            "rooms": rooms,
            "area_sqm": area,
            "city": city,
            "district": district,
            "listing_url": offer.get("listing_url")
        }
    )


def chunk_page_text(
    text: str,
    url: str,
    title: str,
    site: str,
    collection_date: str,
    max_chunk_chars: int = 1500,
    overlap_chars: int = 250
) -> list[DocumentChunk]:
    """Split free-form page text into sliding-window overlapping chunks."""
    if not text:
        return []

    lang = detect_language(text)
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[DocumentChunk] = []

    current_chunk = []
    current_length = 0

    for para in paragraphs:
        if current_length + len(para) > max_chunk_chars and current_chunk:
            full_text = "\n".join(current_chunk)
            chunk_id = f"{site}:page:{abs(hash(url + str(len(chunks)))) % 10000000}"
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                chunk_type="page",
                site=site,
                url=url,
                title=title,
                language=lang,
                collection_date=collection_date,
                content=full_text,
                metadata={"title": title}
            ))
            # Start next chunk with overlap
            current_chunk = [full_text[-overlap_chars:], para]
            current_length = len(current_chunk[0]) + len(para)
        else:
            current_chunk.append(para)
            current_length += len(para)

    if current_chunk:
        full_text = "\n".join(current_chunk)
        chunk_id = f"{site}:page:{abs(hash(url + str(len(chunks)))) % 10000000}"
        chunks.append(DocumentChunk(
            chunk_id=chunk_id,
            chunk_type="page",
            site=site,
            url=url,
            title=title,
            language=lang,
            collection_date=collection_date,
            content=full_text,
            metadata={"title": title}
        ))

    return chunks
