"""
DAR-8 · Wildcard-aware robots.txt checker (RFC 9309 §2.2)

Python's stdlib urllib.robotparser matches rules as plain string prefixes only.
DarGlobal uses patterns such as:
  Disallow: /*utm_source=
  Disallow: /*utm_medium=
  Allow:    /$

RFC 9309 §2.2 specifies:
  * matches any sequence of characters (greedy), including the empty string.
  $ matches the end of the URI.
  Longest-match wins when multiple rules match a URI.
  Allow beats Disallow at the same match length.

This module replaces urllib.robotparser for path-matching, while still using
it for the HTTP fetch (robots.txt download).
"""

from __future__ import annotations

import re
import time
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rule_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert an RFC 9309 robots.txt path pattern to a compiled regex.

    Rules:
      * → .*  (matches any sequence, greedy)
      $ at end → \\Z  (matches end of string only when last character)
      All other regex metacharacters are literal.
    """
    # Escape everything first, then unescape our special chars.
    escaped = re.escape(pattern)

    # re.escape turns * into \\* — replace with .*
    escaped = escaped.replace(r"\*", ".*")

    # re.escape turns $ into \\$ — a trailing \$ means end-of-string anchor.
    # Only treat it as an anchor when it was at the very end of the original.
    if pattern.endswith("$"):
        # Strip the escaped \$ and add a true end anchor.
        escaped = escaped[: -len(r"\$")] + r"\Z"

    return re.compile(escaped)


@dataclass(frozen=True)
class _Rule:
    """A single Allow or Disallow rule."""

    pattern: str          # original pattern string from robots.txt
    allow: bool           # True → Allow, False → Disallow
    regex: re.Pattern[str] = field(compare=False, repr=False)

    @classmethod
    def from_line(cls, directive: str, pattern: str) -> "_Rule":
        return cls(
            pattern=pattern,
            allow=directive.lower() == "allow",
            regex=_rule_to_regex(pattern),
        )

    def matches(self, path: str) -> bool:
        return bool(self.regex.match(path))

    def specificity(self) -> int:
        """Longer patterns are more specific (RFC 9309 §2.2.1)."""
        return len(self.pattern)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class RobotsChecker:
    """RFC 9309-compliant robots.txt checker with wildcard support.

    Usage::

        checker = RobotsChecker.from_url(
            "https://darglobal.co.uk/robots.txt",
            user_agent="DarBot/1.0"
        )
        checker.is_allowed("https://darglobal.co.uk/projects/the-astera/")
        # → True

        checker.is_allowed("https://darglobal.co.uk/?utm_source=google")
        # → False
    """

    def __init__(self, rules: list[_Rule], crawl_delay: Optional[float] = None) -> None:
        self._rules = rules
        self.crawl_delay = crawl_delay  # seconds, or None if not set

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_text(cls, robots_txt: str, user_agent: str) -> "RobotsChecker":
        """Parse robots.txt text and return a checker for *user_agent*."""
        rules: list[_Rule] = []
        crawl_delay: Optional[float] = None

        # We need to find the rule blocks that apply to our agent.
        # Matching is case-insensitive; * is the catch-all agent.
        # Priority: specific agent > * > no match.
        agent_lower = user_agent.lower().split("/")[0]  # strip version

        # Parse all blocks, collect (agent_names, rules_list) pairs.
        blocks: list[tuple[list[str], list[_Rule], Optional[float]]] = []
        current_agents: list[str] = []
        current_rules: list[_Rule] = []
        current_delay: Optional[float] = None
        in_block = False

        for raw_line in robots_txt.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                if in_block and (current_agents or current_rules):
                    blocks.append((list(current_agents), list(current_rules), current_delay))
                    current_agents, current_rules, current_delay = [], [], None
                    in_block = False
                continue

            if ":" not in line:
                continue

            directive, _, value = line.partition(":")
            directive = directive.strip().lower()
            value = value.strip()

            if directive == "user-agent":
                if in_block and current_rules:
                    # New agent block starts; save previous.
                    blocks.append((list(current_agents), list(current_rules), current_delay))
                    current_agents, current_rules, current_delay = [], [], None
                current_agents.append(value.lower())
                in_block = True
            elif directive in ("allow", "disallow") and in_block:
                if value:  # empty Disallow means allow everything
                    current_rules.append(_Rule.from_line(directive, value))
            elif directive == "crawl-delay" and in_block:
                try:
                    current_delay = float(value)
                except ValueError:
                    pass

        if in_block and current_agents:
            blocks.append((current_agents, current_rules, current_delay))

        # Find the best matching block.
        specific_rules: list[_Rule] = []
        wildcard_rules: list[_Rule] = []
        for agents, block_rules, block_delay in blocks:
            if agent_lower in agents:
                specific_rules = block_rules
                crawl_delay = block_delay
                break
            if "*" in agents:
                wildcard_rules = block_rules
                crawl_delay = block_delay

        chosen = specific_rules if specific_rules else wildcard_rules
        return cls(rules=chosen, crawl_delay=crawl_delay)

    @classmethod
    def from_url(
        cls,
        robots_url: str,
        user_agent: str,
        timeout: float = 10.0,
    ) -> "RobotsChecker":
        """Fetch robots.txt from *robots_url* and parse it."""
        req = urllib.request.Request(
            robots_url,
            headers={"User-Agent": user_agent},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
        except Exception:
            # If robots.txt is unreachable, treat everything as allowed (RFC 9309 §2.3.1).
            text = ""
        return cls.from_text(text, user_agent)

    # ------------------------------------------------------------------
    # Core check
    # ------------------------------------------------------------------

    def is_allowed(self, url: str) -> bool:
        """Return True if *url* is allowed for the configured user-agent.

        RFC 9309 §2.2.1 matching algorithm:
          1. Collect all matching Allow and Disallow rules.
          2. The rule with the longest pattern wins.
          3. If two rules are equally long, Allow wins.
          4. If no rule matches, the URL is allowed.
        """
        parsed = urlparse(url)
        path = parsed.path
        if parsed.query:
            path = f"{path}?{parsed.query}"

        best_specificity = -1
        best_allow = True  # default: allowed

        for rule in self._rules:
            if rule.matches(path):
                spec = rule.specificity()
                if spec > best_specificity or (
                    spec == best_specificity and rule.allow
                ):
                    best_specificity = spec
                    best_allow = rule.allow

        return best_allow

    def filter_urls(self, urls: list[str]) -> list[str]:
        """Return only the URLs that are allowed."""
        return [u for u in urls if self.is_allowed(u)]
