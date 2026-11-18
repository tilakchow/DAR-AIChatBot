"""
DAR-11 · Crawl scope and per-site URL caps.

Acceptance criteria (from DAR-11):
  ✓ Include and exclude rules exist for both sites (no form, thank-you, payment pages)
  ✓ Per-category caps are set and documented

Design (section 5 of the plan):
  - DarGlobal: use the sitemap; crawl project, blog, press, insights pages.
    Exclude tracking-param URLs (handled by robots_checker), /rayana/, /amaya/ etc.
    are sub-pages of projects and ARE crawlable.
  - Wasalt: crawl city/category pages (e.g. /en/villas-for-sale-in-riyadh)
    NOT individual listing pages. Each category page has ~20 offers in JSONLD.
    Moderate crawl rate (robots says ≥ 1.5 s delay). Cap per-category to avoid
    deep pagination.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class CrawlConfig:
    """Per-site crawl rules and caps."""

    site: str                       # "darglobal" or "wasalt"
    allowed_path_prefixes: list[str]
    disallowed_path_patterns: list[str]  # regex patterns
    max_pages: int                  # hard cap across all pages for this site
    max_pages_per_category: int     # cap per category URL group


# ---------------------------------------------------------------------------
# DarGlobal scope
# ---------------------------------------------------------------------------

DARGLOBAL_CONFIG = CrawlConfig(
    site="darglobal",
    allowed_path_prefixes=[
        "/the-astera",
        "/one-of-one",
        "/rayana",
        "/amaya",
        "/trump-plaza",
        "/projects",
        "/blog",
        "/press",
        "/insights",
        # top-level project slug pages (any path not explicitly disallowed)
        "/",
    ],
    disallowed_path_patterns=[
        r".*\?.*",           # any query-string URL (tracking, search, etc.)
        r".*/thank-you.*",   # thank-you pages
        r".*/contact.*",     # contact forms
        r".*/payment.*",     # payment pages
        r".*/checkout.*",    # checkout pages
        r".*/cart.*",        # cart pages
        r".*/register.*",    # registration
        r".*/login.*",       # login
        r".*/wp-admin.*",    # WordPress admin
        r".*/wp-json.*",     # WordPress JSON API
        r".*/feed.*",        # RSS feeds
        r".*\.xml$",         # sitemaps and XML files
        r".*\.pdf$",         # PDFs
    ],
    max_pages=200,
    max_pages_per_category=50,
)


# ---------------------------------------------------------------------------
# Wasalt scope
# ---------------------------------------------------------------------------

# City/category URL patterns (English and Arabic)
# Examples: /en/villas-for-sale-in-riyadh, /ar/شقق-للبيع-في-جدة
_WASALT_CATEGORY_PATTERNS = [
    r"^/(en|ar)/(villas|apartments|townhouses|duplexes|studios|penthouses|"
    r"office-spaces|land|farmhouses|chalets|warehouses|shops|clinics|"
    r"hotels|floors|buildings)-for-(sale|rent)(?:-in-[\w-]+)?/?$",
    r"^/(en|ar)/[\w%-]+-(?:for-sale|for-rent|للبيع|للإيجار)(?:-في-[\w%-]+)?/?$",
]

WASALT_CONFIG = CrawlConfig(
    site="wasalt",
    allowed_path_prefixes=[
        "/en/",
        "/ar/",
    ],
    disallowed_path_patterns=[
        r".*/search.*",          # search pages (robots.txt: Disallow /search)
        r".*/cdn-cgi/.*",        # Cloudflare internals (robots.txt: Disallow /cdn-cgi/rum)
        r".*/property/.*",       # individual listing pages (too many; use category pages)
        r".*/listing/.*",        # individual listing pages
        r".*/agent/.*",          # agent profile pages (PII)
        r".*/developer/.*",      # developer pages (not in scope)
        r".*/contact.*",
        r".*/login.*",
        r".*/register.*",
        r".*/profile.*",
        r".*/favourite.*",
        r".*/saved.*",
    ],
    max_pages=150,               # ~10 categories × ~15 pages each
    max_pages_per_category=15,
)


# ---------------------------------------------------------------------------
# URL filter
# ---------------------------------------------------------------------------

class CrawlScope:
    """Decide whether a URL is in scope for crawling."""

    def __init__(self, config: CrawlConfig) -> None:
        self._config = config
        self._compiled_disallowed = [
            re.compile(p, re.IGNORECASE) for p in config.disallowed_path_patterns
        ]

    def is_in_scope(self, url: str) -> bool:
        """Return True if the URL is within the crawl scope for this site."""
        parsed = urlparse(url)
        full_path = parsed.path
        if parsed.query:
            full_path = f"{full_path}?{parsed.query}"

        # Check disallowed patterns first (they override allowed prefixes).
        for pattern in self._compiled_disallowed:
            if pattern.search(full_path):
                return False

        # For DarGlobal: allow anything not explicitly disallowed (sitemap is ground truth).
        if self._config.site == "darglobal":
            return True

        # For Wasalt: only allow category-shaped paths.
        return self._is_wasalt_category(parsed.path)

    @staticmethod
    def _is_wasalt_category(path: str) -> bool:
        for pattern in _WASALT_CATEGORY_PATTERNS:
            if re.match(pattern, path, re.IGNORECASE | re.UNICODE):
                return True
        return False

    def filter_urls(
        self, urls: list[str], cap: int | None = None
    ) -> list[str]:
        """Filter a list of URLs to in-scope ones, with an optional overall cap."""
        in_scope = [u for u in urls if self.is_in_scope(u)]
        if cap is not None:
            in_scope = in_scope[:cap]
        return in_scope


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------

DARGLOBAL_SCOPE = CrawlScope(DARGLOBAL_CONFIG)
WASALT_SCOPE = CrawlScope(WASALT_CONFIG)
