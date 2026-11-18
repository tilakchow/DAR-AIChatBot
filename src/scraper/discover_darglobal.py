import sys
import os
import json

sys.path.insert(0, os.path.abspath('.'))

from playwright.sync_api import sync_playwright
from src.scraper.robots_checker import RobotsChecker
from src.scraper.scope import DARGLOBAL_SCOPE
import tests.test_robots_checker as tr

dg_robots = tr.dg_checker()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://darglobal.co.uk/sitemap.xml', wait_until='domcontentloaded')
    locs = page.evaluate("() => Array.from(document.querySelectorAll('loc')).map(e => e.textContent.trim())")
    browser.close()

allowed_robots = [u for u in locs if dg_robots.is_allowed(u)]
in_scope = [u for u in allowed_robots if DARGLOBAL_SCOPE.is_in_scope(u)]

print(f"Total sitemap URLs: {len(locs)}")
print(f"Allowed by robots.txt: {len(allowed_robots)}")
print(f"In crawl scope: {len(in_scope)}")

# Save discovered URLs
os.makedirs("data/raw", exist_ok=True)
with open("data/raw/darglobal_urls.json", "w", encoding="utf-8") as f:
    json.dump(in_scope, f, indent=2)

print("Saved in-scope URLs to data/raw/darglobal_urls.json")
