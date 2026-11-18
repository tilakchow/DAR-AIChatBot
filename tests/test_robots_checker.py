"""
Tests for DAR-8: wildcard-aware robots.txt checker.

Acceptance criteria (from DAR-8):
  ✓ Unit tests pass against the recorded DarGlobal and Wasalt robots.txt rules
  ✓ /search on Wasalt is rejected
  ✓ ?utm_source= URLs on DarGlobal are rejected
"""

import pytest
import sys
import os

# Allow running from any working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.scraper.robots_checker import RobotsChecker, _rule_to_regex


# ---------------------------------------------------------------------------
# DarGlobal robots.txt (recorded 18 Nov 2026, section 5 of the plan)
# ---------------------------------------------------------------------------

DARGLOBAL_ROBOTS = """
User-agent: *
Disallow: /sitemap_index.xml
Disallow: /*utm_source=
Disallow: /*utm_medium=
Disallow: /*utm_campaign=
Disallow: /*sfmc_id=
Disallow: /*sfmc_activityid=
Disallow: /*dealercode=
Disallow: /*ltclid=
Disallow: /*trk=
Disallow: /*?wc-ajax=
Disallow: /*?post_type=
Disallow: /*?s=
Allow: /$
Allow: /blog/
Allow: /press/
Allow: /projects/
""".strip()

WASALT_ROBOTS = """
User-agent: *
Allow: /
Disallow: /search
Disallow: /cdn-cgi/rum
""".strip()


# ---------------------------------------------------------------------------
# Helper: build a checker from inline text
# ---------------------------------------------------------------------------

def dg_checker() -> RobotsChecker:
    return RobotsChecker.from_text(DARGLOBAL_ROBOTS, user_agent="DarBot/1.0")


def wa_checker() -> RobotsChecker:
    return RobotsChecker.from_text(WASALT_ROBOTS, user_agent="DarBot/1.0")


# ---------------------------------------------------------------------------
# DAR-8 acceptance criterion: DarGlobal wildcard rules
# ---------------------------------------------------------------------------

class TestDarGlobalRobots:
    """DarGlobal uses * wildcards; stdlib robotparser would mis-read them."""

    def test_home_page_allowed(self):
        assert dg_checker().is_allowed("https://darglobal.co.uk/") is True

    def test_project_page_allowed(self):
        assert dg_checker().is_allowed("https://darglobal.co.uk/the-astera/") is True

    def test_blog_allowed(self):
        assert dg_checker().is_allowed("https://darglobal.co.uk/blog/") is True

    def test_press_allowed(self):
        assert dg_checker().is_allowed("https://darglobal.co.uk/press/some-article") is True

    def test_projects_index_allowed(self):
        assert dg_checker().is_allowed("https://darglobal.co.uk/projects/") is True

    # Critical: wildcard disallows
    def test_utm_source_rejected(self):
        """/*utm_source= must block any URL containing utm_source= anywhere."""
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/the-astera/?utm_source=google"
        ) is False

    def test_utm_medium_rejected(self):
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/?utm_medium=email"
        ) is False

    def test_utm_campaign_rejected(self):
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/projects/?utm_campaign=spring"
        ) is False

    def test_sfmc_rejected(self):
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/?sfmc_id=123"
        ) is False

    def test_dealercode_rejected(self):
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/?dealercode=abc"
        ) is False

    def test_ltclid_rejected(self):
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/?ltclid=xyz"
        ) is False

    def test_trk_rejected(self):
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/?trk=123"
        ) is False

    def test_wc_ajax_rejected(self):
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/shop/?wc-ajax=get_refreshed_fragments"
        ) is False

    def test_post_type_rejected(self):
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/?post_type=product"
        ) is False

    def test_search_query_rejected(self):
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/?s=apartment"
        ) is False

    def test_sitemap_index_rejected(self):
        assert dg_checker().is_allowed(
            "https://darglobal.co.uk/sitemap_index.xml"
        ) is False

    def test_allow_wins_over_disallow_at_root(self):
        """Allow: /$ should beat a less specific Disallow that also matches /."""
        # / is explicitly Allow: /$
        assert dg_checker().is_allowed("https://darglobal.co.uk/") is True


# ---------------------------------------------------------------------------
# DAR-8 acceptance criterion: Wasalt robots.txt rules
# ---------------------------------------------------------------------------

class TestWasaltRobots:
    """/search on Wasalt MUST be rejected."""

    def test_category_page_allowed(self):
        assert wa_checker().is_allowed("https://wasalt.sa/en/villas-for-sale-in-riyadh") is True

    def test_root_allowed(self):
        assert wa_checker().is_allowed("https://wasalt.sa/") is True

    def test_search_rejected(self):
        """Disallow: /search must block /search and anything under it."""
        assert wa_checker().is_allowed("https://wasalt.sa/search") is False

    def test_search_with_query_rejected(self):
        assert wa_checker().is_allowed(
            "https://wasalt.sa/search?q=riyadh+villa"
        ) is False

    def test_cdn_cgi_rum_rejected(self):
        assert wa_checker().is_allowed("https://wasalt.sa/cdn-cgi/rum") is False


# ---------------------------------------------------------------------------
# _rule_to_regex unit tests (internal helper)
# ---------------------------------------------------------------------------

class TestRuleToRegex:
    def test_plain_prefix(self):
        r = _rule_to_regex("/blog/")
        assert r.match("/blog/post") is not None
        assert r.match("/other/") is None

    def test_wildcard_star(self):
        r = _rule_to_regex("/*utm_source=")
        assert r.match("/?utm_source=google") is not None
        assert r.match("/page/?utm_source=google") is not None
        assert r.match("/noutm/") is None

    def test_end_anchor(self):
        r = _rule_to_regex("/$")
        assert r.match("/") is not None
        assert r.match("/page") is None

    def test_wildcard_and_end_anchor(self):
        r = _rule_to_regex("/*.pdf$")
        assert r.match("/files/brochure.pdf") is not None
        assert r.match("/files/brochure.pdf?v=1") is None  # $ anchors


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_robots_allows_everything(self):
        checker = RobotsChecker.from_text("", user_agent="DarBot/1.0")
        assert checker.is_allowed("https://example.com/anything") is True

    def test_unreachable_robots_allows_everything(self):
        """RFC 9309 §2.3.1: if robots.txt is unreachable, treat as allowed."""
        # from_url with an invalid URL — should catch the error and return allow-all
        checker = RobotsChecker.from_url(
            "http://localhost:1/robots.txt", user_agent="DarBot/1.0", timeout=1.0
        )
        assert checker.is_allowed("http://localhost:1/anything") is True

    def test_allow_beats_disallow_same_length(self):
        """When Allow and Disallow have the same specificity, Allow wins."""
        robots = "User-agent: *\nDisallow: /page\nAllow: /page"
        checker = RobotsChecker.from_text(robots, user_agent="bot")
        assert checker.is_allowed("https://example.com/page") is True

    def test_longer_match_wins_over_shorter(self):
        """Longer pattern beats shorter even if shorter is Allow."""
        robots = "User-agent: *\nAllow: /private\nDisallow: /private/secret"
        checker = RobotsChecker.from_text(robots, user_agent="bot")
        assert checker.is_allowed("https://example.com/private/secret") is False
        assert checker.is_allowed("https://example.com/private/ok") is True

    def test_specific_agent_overrides_wildcard(self):
        robots = (
            "User-agent: *\nDisallow: /admin\n\n"
            "User-agent: DarBot\nAllow: /admin"
        )
        checker = RobotsChecker.from_text(robots, user_agent="DarBot/1.0")
        assert checker.is_allowed("https://example.com/admin") is True

    def test_crawl_delay_parsed(self):
        robots = "User-agent: *\nCrawl-delay: 2\nDisallow:"
        checker = RobotsChecker.from_text(robots, user_agent="bot")
        assert checker.crawl_delay == 2.0

    def test_filter_urls(self):
        checker = wa_checker()
        urls = [
            "https://wasalt.sa/en/villas-for-sale-in-riyadh",
            "https://wasalt.sa/search?q=villa",
            "https://wasalt.sa/en/apartments-in-jeddah",
        ]
        allowed = checker.filter_urls(urls)
        assert "https://wasalt.sa/search?q=villa" not in allowed
        assert len(allowed) == 2
