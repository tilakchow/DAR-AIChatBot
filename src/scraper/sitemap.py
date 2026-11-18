"""
DAR-9 · Sitemap discovery: XML and gzip-compressed sitemaps.

Acceptance criteria (from DAR-9):
  ✓ Parses urlset and sitemapindex, plain and gzipped
  ✓ Sitemap entries with spaces or &apos; resolve to fetchable URLs

Design notes (section 5 of the plan):
  - DarGlobal: single /sitemap.xml (urlset, lastmod 2026-11-10)
  - Wasalt: 10 gzipped sitemaps on cdn.wasalt.sa listed in robots.txt
  - Some DarGlobal URLs contain spaces or &apos; and must be normalised.
  - Sitemap discovery is preferred over link-following (fewer requests).
"""

from __future__ import annotations

import gzip
import io
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote, unquote, urlparse, urlunparse

logger = logging.getLogger(__name__)

# XML namespace used by the sitemap protocol.
_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


# ---------------------------------------------------------------------------
# URL normalisation
# ---------------------------------------------------------------------------

def normalise_url(raw: str) -> str:
    """Normalise a URL that may contain spaces, XML entities, or other oddities.

    Steps:
      1. Decode XML entities (&apos; → ', &amp; → &, &lt; → <, etc.)
         using a simple regex (not a full XML parser, to handle malformed input).
      2. Strip leading/trailing whitespace.
      3. Percent-encode any bare spaces in the path.
      4. Return the normalised URL string.

    >>> normalise_url("https://darglobal.co.uk/trump&apos;s-corner/")
    "https://darglobal.co.uk/trump's-corner/"
    >>> normalise_url("https://darglobal.co.uk/the astera/")
    'https://darglobal.co.uk/the%20astera/'
    """
    # 1. Decode common XML/HTML entities.
    xml_entities = {
        "&apos;": "'",
        "&quot;": '"',
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&#39;": "'",
        "&#34;": '"',
        "&#38;": "&",
    }
    url = raw.strip()
    for entity, char in xml_entities.items():
        url = url.replace(entity, char)

    # 2. Parse and re-encode.
    parsed = urlparse(url)

    # 3. Encode spaces in path (and other non-ASCII characters).
    # unquote first so we don't double-encode, then re-quote.
    safe_path = quote(unquote(parsed.path), safe="/-._~!$&'()*+,;:@%")

    # Reconstruct.
    normalised = urlunparse(parsed._replace(path=safe_path))
    return normalised


# ---------------------------------------------------------------------------
# Sitemap entry
# ---------------------------------------------------------------------------

@dataclass
class SitemapEntry:
    loc: str              # canonical URL (normalised)
    lastmod: Optional[str] = None  # ISO date string or None
    changefreq: Optional[str] = None
    priority: Optional[float] = None


# ---------------------------------------------------------------------------
# Sitemap parser
# ---------------------------------------------------------------------------

def parse_sitemap(
    content: bytes,
    source_url: str = "",
) -> tuple[list[SitemapEntry], list[str]]:
    """Parse a sitemap (plain XML or gzip-compressed).

    Returns:
      (entries, child_sitemaps)
      - entries: list of SitemapEntry from a <urlset>
      - child_sitemaps: list of sitemap URLs from a <sitemapindex>
    """
    # Decompress if gzip.
    if content[:2] == b"\x1f\x8b":
        try:
            content = gzip.decompress(content)
        except Exception as exc:
            logger.warning("Failed to decompress gzip sitemap from %s: %s", source_url, exc)
            return [], []

    # Strip BOM if present.
    if content.startswith(b"\xef\xbb\xbf"):
        content = content[3:]

    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        logger.warning("Failed to parse sitemap XML from %s: %s", source_url, exc)
        return [], []

    # Strip namespace for tag comparison.
    tag = root.tag
    if tag == f"{{{_SITEMAP_NS}}}sitemapindex" or tag == "sitemapindex":
        return _parse_sitemapindex(root)
    elif tag == f"{{{_SITEMAP_NS}}}urlset" or tag == "urlset":
        return _parse_urlset(root)
    else:
        logger.warning("Unknown sitemap root element <%s> from %s", tag, source_url)
        return [], []


def _ns(tag: str) -> str:
    return f"{{{_SITEMAP_NS}}}{tag}"


def _text(el: ET.Element, tag: str) -> Optional[str]:
    """Find a child element and return its text, or None.

    Uses explicit `is not None` to avoid Element.__bool__ issues
    (in Python 3.14+ using `or` on Element objects raises FutureWarning).
    """
    child = el.find(_ns(tag))
    if child is None:
        child = el.find(tag)  # fallback: no-namespace version
    if child is not None and child.text:
        return child.text.strip()
    return None


def _parse_urlset(root: ET.Element) -> tuple[list[SitemapEntry], list[str]]:
    entries: list[SitemapEntry] = []
    for url_el in root.iterfind(_ns("url")):
        loc_raw = _text(url_el, "loc")
        if not loc_raw:
            continue
        loc = normalise_url(loc_raw)
        lastmod = _text(url_el, "lastmod")
        changefreq = _text(url_el, "changefreq")
        priority_str = _text(url_el, "priority")
        priority = float(priority_str) if priority_str else None
        entries.append(SitemapEntry(loc=loc, lastmod=lastmod, changefreq=changefreq, priority=priority))
    return entries, []


def _parse_sitemapindex(root: ET.Element) -> tuple[list[SitemapEntry], list[str]]:
    child_sitemaps: list[str] = []
    for sitemap_el in root.iterfind(_ns("sitemap")):
        loc_raw = _text(sitemap_el, "loc")
        if loc_raw:
            child_sitemaps.append(normalise_url(loc_raw))
    return [], child_sitemaps


# ---------------------------------------------------------------------------
# High-level discovery
# ---------------------------------------------------------------------------

class SitemapDiscovery:
    """Fetch and parse sitemaps from a site, following sitemapindex pointers.

    Usage::

        disco = SitemapDiscovery(user_agent="DarBot/1.0")
        entries = disco.discover("https://darglobal.co.uk/sitemap.xml")
        # entries is a list of SitemapEntry with normalised .loc URLs
    """

    def __init__(
        self,
        user_agent: str = "DarBot/1.0",
        timeout: float = 20.0,
        max_depth: int = 3,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_depth = max_depth

    def discover(self, sitemap_url: str) -> list[SitemapEntry]:
        """Recursively fetch and parse sitemaps starting from *sitemap_url*."""
        return self._fetch_recursive(sitemap_url, depth=0)

    def _fetch_recursive(self, url: str, depth: int) -> list[SitemapEntry]:
        if depth > self.max_depth:
            logger.warning("Max sitemap depth %d exceeded at %s", self.max_depth, url)
            return []

        content = self._fetch(url)
        if content is None:
            return []

        entries, child_sitemaps = parse_sitemap(content, source_url=url)
        logger.info(
            "Sitemap %s → %d entries, %d child sitemaps",
            url,
            len(entries),
            len(child_sitemaps),
        )

        for child_url in child_sitemaps:
            entries.extend(self._fetch_recursive(child_url, depth=depth + 1))

        return entries

    def _fetch(self, url: str) -> Optional[bytes]:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self.user_agent},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read()
        except Exception as exc:
            logger.warning("Failed to fetch sitemap %s: %s", url, exc)
            return None
