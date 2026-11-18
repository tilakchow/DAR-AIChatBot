"""
DAR-23 · Guardrails, Input Validation, Prompt-Injection Blocker, Rate Limiting & Answer Cache.

Acceptance criteria (from DAR-23):
  ✓ Over-length input is rejected with HTTP 422
  ✓ Injection test strings are refused without an LLM call
  ✓ Per-IP limit returns HTTP 429, and a repeated question is served from cache
"""

from __future__ import annotations

import re
import time
import hashlib
from typing import Optional


# Prompt injection detection signatures (OWASP LLM01)
_INJECTION_PATTERNS = [
    r"ignore (?:all )?(?:previous|above|system) (?:instructions|rules|prompts)",
    r"disregard (?:all )?(?:previous|system) (?:rules|prompts)",
    r"you are now (?:dan|an unfiltered|a rogue|an evil|jailbroken)",
    r"system prompt override",
    r"reveal (?:your )?(?:system|developer|hidden) (?:prompt|instructions)",
    r"output (?:all )?(?:rules|instructions)",
    r"bypass (?:all )?(?:filters|safety|guardrails)",
    r"drop database",
    r"<script.*?>",
]

_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]

# Limits
MAX_INPUT_CHARS = 1000
MAX_REQUESTS_PER_MINUTE_PER_IP = 15


class GuardrailViolation(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RateLimiter:
    """Sliding-window per-IP rate limiter."""
    def __init__(self, max_requests: int = MAX_REQUESTS_PER_MINUTE_PER_IP, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = {}

    def check(self, ip: str) -> bool:
        now = time.monotonic()
        history = self.requests.get(ip, [])
        # Evict old requests outside window
        valid = [t for t in history if now - t < self.window_seconds]
        if len(valid) >= self.max_requests:
            self.requests[ip] = valid
            return False
        valid.append(now)
        self.requests[ip] = valid
        return True


class AnswerCache:
    """In-memory cache for repeated exact queries to conserve LLM quota."""
    def __init__(self, ttl_seconds: float = 3600.0):
        self.ttl = ttl_seconds
        self.cache: dict[str, tuple[float, dict]] = {}

    @staticmethod
    def _key(query: str, site_filter: Optional[str] = None) -> str:
        norm = query.strip().lower() + "|" + (site_filter or "all")
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def get(self, query: str, site_filter: Optional[str] = None) -> Optional[dict]:
        key = self._key(query, site_filter)
        if key in self.cache:
            ts, val = self.cache[key]
            if time.monotonic() - ts < self.ttl:
                return val
            del self.cache[key]
        return None

    def set(self, query: str, site_filter: Optional[str], response: dict):
        key = self._key(query, site_filter)
        self.cache[key] = (time.monotonic(), response)


def validate_user_input(query: str):
    """Validate query length and check for prompt injection."""
    if not query or not query.strip():
        raise GuardrailViolation("Query cannot be empty.", status_code=422)

    if len(query) > MAX_INPUT_CHARS:
        raise GuardrailViolation(
            f"Query length ({len(query)} characters) exceeds the maximum allowed ({MAX_INPUT_CHARS}).",
            status_code=422
        )

    # Check for obvious prompt injection attempts
    for pattern in _INJECTION_RE:
        if pattern.search(query):
            raise GuardrailViolation(
                "Your request contains blocked instructions or security policy violations.",
                status_code=400
            )


# Global singletons
RATE_LIMITER = RateLimiter()
ANSWER_CACHE = AnswerCache()
