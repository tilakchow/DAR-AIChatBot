"""
Tests for DAR-9: sitemap discovery (plain XML and gzip).

Acceptance criteria:
  ✓ Parses urlset and sitemapindex, plain and gzipped
  ✓ Sitemap entries with spaces or &apos; resolve to fetchable URLs
"""

import sys
import os
import gzip
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.scraper.sitemap import (
    parse_sitemap,
    normalise_url,
    SitemapDiscovery,
    SitemapEntry,
)


# ---------------------------------------------------------------------------
# Fixtures: minimal sitemap XML strings
# ---------------------------------------------------------------------------

URLSET_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://darglobal.co.uk/the-astera/</loc>
    <lastmod>2026-11-10</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://darglobal.co.uk/trump&apos;s-corner/</loc>
    <lastmod>2026-11-10</lastmod>
  </url>
  <url>
    <loc>https://darglobal.co.uk/the astera luxury/</loc>
  </url>
</urlset>
"""

SITEMAPINDEX_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://cdn.wasalt.sa/sitemap-en-villas.xml.gz</loc>
  </sitemap>
  <sitemap>
    <loc>https://cdn.wasalt.sa/sitemap-ar-apartments.xml.gz</loc>
  </sitemap>
</sitemapindex>
"""

CHILD_URLSET_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://wasalt.sa/en/villas-for-sale-in-riyadh</loc>
    <lastmod>2026-11-15</lastmod>
  </url>
</urlset>
"""


def _gzip(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write(data)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# URL normalisation tests
# ---------------------------------------------------------------------------

class TestNormaliseUrl:
    def test_apos_entity_decoded(self):
        url = normalise_url("https://darglobal.co.uk/trump&apos;s-corner/")
        assert "&apos;" not in url
        assert "'" in url

    def test_amp_entity_decoded(self):
        url = normalise_url("https://example.com/page&amp;section=1")
        assert "&amp;" not in url
        assert "&" in url

    def test_space_percent_encoded(self):
        url = normalise_url("https://darglobal.co.uk/the astera luxury/")
        assert " " not in url
        assert "%20" in url

    def test_normal_url_unchanged(self):
        url = normalise_url("https://darglobal.co.uk/the-astera/")
        assert url == "https://darglobal.co.uk/the-astera/"

    def test_leading_whitespace_stripped(self):
        url = normalise_url("  https://example.com/page  ")
        assert url == "https://example.com/page"

    def test_hash39_entity(self):
        url = normalise_url("https://example.com/it&#39;s-fine/")
        assert "&#39;" not in url


# ---------------------------------------------------------------------------
# parse_sitemap: urlset
# ---------------------------------------------------------------------------

class TestParseUrlset:
    def test_entries_count(self):
        entries, children = parse_sitemap(URLSET_XML, "test")
        assert len(entries) == 3
        assert children == []

    def test_first_entry_loc(self):
        entries, _ = parse_sitemap(URLSET_XML, "test")
        assert entries[0].loc == "https://darglobal.co.uk/the-astera/"

    def test_first_entry_lastmod(self):
        entries, _ = parse_sitemap(URLSET_XML, "test")
        assert entries[0].lastmod == "2026-11-10"

    def test_first_entry_priority(self):
        entries, _ = parse_sitemap(URLSET_XML, "test")
        assert entries[0].priority == 0.8

    def test_apos_in_url_decoded(self):
        entries, _ = parse_sitemap(URLSET_XML, "test")
        # second entry had &apos; — should be decoded to '
        assert "&apos;" not in entries[1].loc
        assert "trump" in entries[1].loc

    def test_space_in_url_encoded(self):
        entries, _ = parse_sitemap(URLSET_XML, "test")
        # third entry had a space
        assert " " not in entries[2].loc

    def test_gzipped_urlset(self):
        gz_content = _gzip(URLSET_XML)
        entries, children = parse_sitemap(gz_content, "test.gz")
        assert len(entries) == 3
        assert children == []

    def test_no_namespace_urlset(self):
        """Some sitemaps omit the xmlns attribute."""
        xml = b"""<urlset>
          <url><loc>https://example.com/page</loc></url>
        </urlset>"""
        entries, _ = parse_sitemap(xml, "test")
        assert len(entries) == 1
        assert entries[0].loc == "https://example.com/page"


# ---------------------------------------------------------------------------
# parse_sitemap: sitemapindex
# ---------------------------------------------------------------------------

class TestParseSitemapIndex:
    def test_child_sitemaps_found(self):
        entries, children = parse_sitemap(SITEMAPINDEX_XML, "test")
        assert entries == []
        assert len(children) == 2

    def test_child_sitemap_urls(self):
        _, children = parse_sitemap(SITEMAPINDEX_XML, "test")
        assert "https://cdn.wasalt.sa/sitemap-en-villas.xml.gz" in children
        assert "https://cdn.wasalt.sa/sitemap-ar-apartments.xml.gz" in children

    def test_gzipped_sitemapindex(self):
        gz = _gzip(SITEMAPINDEX_XML)
        _, children = parse_sitemap(gz, "index.xml.gz")
        assert len(children) == 2


# ---------------------------------------------------------------------------
# SitemapDiscovery: recursive fetch
# ---------------------------------------------------------------------------

class TestSitemapDiscovery:
    def test_simple_urlset_discovery(self, monkeypatch=None):
        """Discovery of a plain urlset returns all entries."""
        import unittest.mock as mock

        class FakeResponse:
            def __init__(self, body): self._body = body
            def read(self): return self._body
            def __enter__(self): return self
            def __exit__(self, *a): pass

        disco = SitemapDiscovery(user_agent="DarBot/1.0")
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(URLSET_XML)):
            entries = disco.discover("https://darglobal.co.uk/sitemap.xml")

        assert len(entries) == 3

    def test_sitemapindex_followed(self):
        """Discovery of a sitemapindex fetches and parses all child sitemaps."""
        import unittest.mock as mock

        url_map = {
            "https://wasalt.sa/sitemap_index.xml": SITEMAPINDEX_XML,
            "https://cdn.wasalt.sa/sitemap-en-villas.xml.gz": _gzip(CHILD_URLSET_XML),
            "https://cdn.wasalt.sa/sitemap-ar-apartments.xml.gz": _gzip(CHILD_URLSET_XML),
        }

        def fake_urlopen(req, timeout):
            body = url_map.get(req.full_url, b"<urlset></urlset>")
            class R:
                def read(self): return body
                def __enter__(self): return self
                def __exit__(self, *a): pass
            return R()

        disco = SitemapDiscovery(user_agent="DarBot/1.0")
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            entries = disco.discover("https://wasalt.sa/sitemap_index.xml")

        # 2 child sitemaps × 1 entry each = 2 entries
        assert len(entries) == 2
        assert all(e.loc == "https://wasalt.sa/en/villas-for-sale-in-riyadh" for e in entries)

    def test_max_depth_respected(self):
        """Should not recurse beyond max_depth."""
        import unittest.mock as mock

        # Always return a sitemapindex pointing to itself — would loop without depth limit.
        infinite_index = b"""<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <sitemap><loc>https://example.com/sitemap.xml</loc></sitemap>
        </sitemapindex>"""

        call_count = {"n": 0}

        def fake_urlopen(req, timeout):
            call_count["n"] += 1
            class R:
                def read(self): return infinite_index
                def __enter__(self): return self
                def __exit__(self, *a): pass
            return R()

        disco = SitemapDiscovery(user_agent="DarBot/1.0", max_depth=2)
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            entries = disco.discover("https://example.com/sitemap.xml")

        # With max_depth=2: depth 0 → depth 1 → depth 2 → depth 3 stops
        assert call_count["n"] <= disco.max_depth + 1
        assert entries == []

    def test_unreachable_sitemap_returns_empty(self):
        """If the sitemap URL is unreachable, return an empty list (don't raise)."""
        disco = SitemapDiscovery(user_agent="DarBot/1.0", timeout=1.0)
        entries = disco.discover("http://localhost:1/sitemap.xml")
        assert entries == []

    def test_malformed_xml_returns_empty(self):
        """Malformed XML should return an empty list (don't raise)."""
        import unittest.mock as mock

        class FakeResponse:
            def read(self): return b"<not valid xml ><"
            def __enter__(self): return self
            def __exit__(self, *a): pass

        disco = SitemapDiscovery()
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()):
            entries = disco.discover("https://example.com/broken.xml")

        assert entries == []
