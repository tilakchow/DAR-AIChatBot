"""
DAR-24 / DAR-25 · Structured RAG Schemas and Text Post-Processing.

Provides structured response models and sanitization to deliver clean,
conversational answers without inline footnote citations or disclaimer clutter:
  {
    "answer_text": "...",
    "highlights": [...],
    "sources": [{"id": 1, "title": "...", "url": "..."}],
    "model_used": "...",
    "latency_ms": 123.4,
    "cached": false
  }
"""

from __future__ import annotations

import re
from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator


def clean_answer_text(raw_text: str) -> tuple[str, list[str]]:
    """
    Sanitize raw model response:
    - Strips inline footnote citations like [1], [2], [1][2], [1, 2]
    - Strips repetitive opening boilerplate ("Based on the verified information...", etc.)
    - Strips per-message disclaimer boilerplate ("Disclaimer: I am an AI...", etc.)
    - Normalizes punctuation and extracts structured bullet highlights.
    """
    text = (raw_text or "").strip()
    if not text:
        return "", []

    # Handle decline / out-of-scope gracefully
    if "enough verified information" in text.lower():
        clean_text = "I don't have enough verified information in the DarGlobal or Wasalt database to answer this question."
        return clean_text, []

    # 1. Strip repetitive disclaimer blocks
    text = re.sub(r'(\n|^)\s*\*?Disclaimer:.*', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'(\n|^)\s*\*?Important Note[s]?:.*', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'(\n|^)\s*Property prices and availability change frequently.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(\n|^)\s*\*?Source:\s*Wasalt\.sa.*', '', text, flags=re.IGNORECASE)

    # 2. Strip opening boilerplate phrases
    boilerplate_pattern = r'^\s*(?:(?:Based on|According to) [^\n,:]*(?:database|records|listings|context|information)[^\n,:]*[,:\n]\s*|Here is what I can confirm about [^\n,:]*[:\n]\s*)'
    text = re.sub(boilerplate_pattern, '', text, flags=re.IGNORECASE)

    # 3. Strip inline citation numbers like [1], [2], [1][2], [1, 2]
    text = re.sub(r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]', '', text)

    # 4. Clean up spaces before punctuation (e.g. 'Downtown .' -> 'Downtown.')
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = text.strip()

    # 5. Extract bullet highlights
    highlights: list[str] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if line.startswith(('-', '*', '•')) or re.match(r'^\d+\.', line):
            cleaned_pt = re.sub(r'^[-*•\d\.]+\s*', '', line).strip()
            # Clean any leftover bold markers in highlights if needed
            cleaned_pt = re.sub(r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]', '', cleaned_pt).strip()
            if cleaned_pt:
                highlights.append(cleaned_pt)

    # Cap highlights at 4 max
    highlights = highlights[:4]

    return text, highlights


class SourceItem(BaseModel):
    """Structured citation item for a verified knowledge source."""
    id: int = Field(..., description="1-based source identifier")
    title: str = Field(..., description="Source document or listing title")
    url: str = Field(..., description="Verified canonical URL")
    site: Optional[str] = Field(None, description="Portal: darglobal or wasalt")
    chunk_type: Optional[str] = Field(None, description="Type: page, faq, or listing")
    index: Optional[int] = Field(None, description="Backward compatibility index alias")

    @model_validator(mode="before")
    @classmethod
    def sync_id_and_index(cls, data: Any):
        if isinstance(data, dict):
            if "id" not in data and "index" in data:
                data["id"] = data["index"]
            elif "index" not in data and "id" in data:
                data["index"] = data["id"]
        return data


class FormattedAnswer(BaseModel):
    """Backward-compatible model for older tests expecting FormattedAnswer."""
    summary: str
    key_points: list[str] = Field(default_factory=list)
    properties_mentioned: list[str] = Field(default_factory=list)
    disclaimer: Optional[str] = None
    full_text: str

    @classmethod
    def from_raw_text(cls, text: str) -> FormattedAnswer:
        clean_text, hl = clean_answer_text(text)
        return cls(
            summary=clean_text.splitlines()[0] if clean_text else "",
            key_points=hl,
            properties_mentioned=[],
            disclaimer=None,
            full_text=clean_text
        )


class ChatResponse(BaseModel):
    """Structured response payload complying with requirements."""
    answer_text: str = Field(..., description="Clean conversational answer text")
    highlights: list[str] = Field(default_factory=list, description="Key bullet highlights or specifications")
    sources: list[SourceItem] = Field(default_factory=list, description="Verified sources with id, title, and url")
    model_used: str = Field(..., description="OpenRouter model name")
    latency_ms: float = Field(..., description="Request latency in milliseconds")
    cached: bool = Field(False, description="Whether the answer was served from the answer cache")
    # Backward compatibility alias
    answer: Optional[Any] = Field(None, description="Backward compatibility alias for answer_text")

    @model_validator(mode="before")
    @classmethod
    def populate_compat_fields(cls, data: Any):
        if isinstance(data, dict):
            if "answer_text" in data and "answer" not in data:
                data["answer"] = data["answer_text"]
            elif "answer" in data and "answer_text" not in data:
                ans = data["answer"]
                if isinstance(ans, dict) and "full_text" in ans:
                    data["answer_text"] = ans["full_text"]
                elif hasattr(ans, "full_text"):
                    data["answer_text"] = ans.full_text
                else:
                    data["answer_text"] = str(ans)
        return data
