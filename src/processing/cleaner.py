"""
DAR-15 · Text cleaning and PII scrubbing.

Acceptance criteria (from DAR-15):
  ✓ Unit tests show phone numbers and emails removed
  ✓ Unit tests show prices (2,150,000), area ranges and ISO dates kept

Rules:
  - Normalise Unicode (NFKC) and strip extra whitespace
  - Strip common boilerplate (navigation, footer links, cookie disclaimers)
  - Replace phone numbers (international, Saudi 05x, local) with [PHONE_REMOVED]
  - Replace emails with [EMAIL_REMOVED]
  - Preserve all numbers, prices (e.g. SAR 3,200,000 / AED 2,150,000), sqm areas, and ISO dates (2026-11-18)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional


# Email regex (RFC 5322 compliant subset)
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    re.IGNORECASE
)

# Phone number regex:
# Handles Saudi mobile: +966 5x, 05x, international formats, dash/dot/space separated
_PHONE_RE = re.compile(
    r"""(?:\+?966\s*[-.]?\s*|0)(?:5[0-9]{8}|1[1-7][0-9]{7})"""  # Saudi specific formats
    r"""|(?:\+?[1-9]\d{0,2}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}""",  # General international
    re.VERBOSE
)

# Boilerplate substrings to remove
_BOILERPLATE_PATTERNS = [
    r"Accept all cookies.*?(?:Save preferences|Reject all)?",
    r"By continuing to browse this site, you agree to our use of cookies\.",
    r"All rights reserved\.",
    r"Copyright © \d{4}.*?",
    r"Terms of Service\s*\|\s*Privacy Policy",
]

_BOILERPLATE_RE = [re.compile(p, re.IGNORECASE) for p in _BOILERPLATE_PATTERNS]


def scrub_pii(text: str) -> str:
    """Replace phone numbers and email addresses with redaction placeholders."""
    if not text:
        return ""
    
    # 1. Redact emails
    scrubbed = _EMAIL_RE.sub("[EMAIL_REMOVED]", text)
    
    # 2. Redact phone numbers (ensure we don't accidentally redact standalone numbers or prices)
    # Only match if it looks like a phone pattern
    def _replace_phone(m: re.Match) -> str:
        s = m.group(0).strip()
        # Protect currency numbers and dates: if purely 4 digits or contains comma/dot for decimal, keep
        if re.match(r"^\d{4}$", s): # e.g. year 2026
            return s
        if re.match(r"^\d{1,3}(,\d{3})+(\.\d+)?$", s): # e.g. 2,150,000
            return s
        # If length of digits in string is between 9 and 15, redact
        digits = [c for c in s if c.isdigit()]
        if len(digits) >= 9:
            return "[PHONE_REMOVED]"
        return s

    scrubbed = _PHONE_RE.sub(_replace_phone, scrubbed)
    return scrubbed


def clean_text(text: str) -> str:
    """Clean and normalise document text, scrubbing PII and preserving prices/dates."""
    if not text:
        return ""

    # Normalise Unicode (NFKC)
    normalised = unicodedata.normalize("NFKC", text)

    # Strip boilerplate
    for b_re in _BOILERPLATE_RE:
        normalised = b_re.sub(" ", normalised)

    # Scrub PII (emails, phone numbers)
    scrubbed = scrub_pii(normalised)

    # Collapse multiple spaces and blank lines
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in scrubbed.splitlines()]
    clean_lines = [l for l in lines if l]
    
    return "\n".join(clean_lines)
