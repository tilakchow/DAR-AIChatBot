"""
DAR-13 · Scraper runner for DarGlobal and Wasalt.

Performs a polite, controlled scrape of:
  - DarGlobal projects, news, press, insights, and FAQs
  - Wasalt city and category pages (bilingual: English and Arabic), extracting JSON-LD offers with ZERO seller PII

Outputs:
  - data/raw/darglobal.jsonl
  - data/raw/wasalt.jsonl
  - data/raw/crawl_log.jsonl
  - data/raw/stats.json
"""

import os
import sys
import json
import time
import logging
from dataclasses import asdict
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath('.'))

from src.scraper.robots_checker import RobotsChecker
from src.scraper.scope import DARGLOBAL_SCOPE, WASALT_SCOPE
from src.scraper.extractor import extract_darglobal, extract_wasalt
import tests.test_robots_checker as tr

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scraper")

RAW_DIR = "data/raw"
os.makedirs(RAW_DIR, exist_ok=True)

DARGLOBAL_JSONL = os.path.join(RAW_DIR, "darglobal.jsonl")
WASALT_JSONL = os.path.join(RAW_DIR, "wasalt.jsonl")
CRAWL_LOG = os.path.join(RAW_DIR, "crawl_log.jsonl")
STATS_FILE = os.path.join(RAW_DIR, "stats.json")

def select_darglobal_urls() -> list[str]:
    """Select a high-value subset of DarGlobal project, insights, press, and about pages."""
    url_file = os.path.join(RAW_DIR, "darglobal_urls.json")
    if os.path.exists(url_file):
        with open(url_file, "r", encoding="utf-8") as f:
            all_urls = json.load(f)
    else:
        all_urls = []

    # Target distinct key projects, press, blogs, and insights
    core_projects = [
        "https://darglobal.co.uk/",
        "https://darglobal.co.uk/the-astera",
        "https://darglobal.co.uk/trump-international-golf-club-oman",
        "https://darglobal.co.uk/aida",
        "https://darglobal.co.uk/w-residences-dubai-downtown",
        "https://darglobal.co.uk/urban-oasis",
        "https://darglobal.co.uk/dg1",
        "https://darglobal.co.uk/da-vinci-tower",
        "https://darglobal.co.uk/les-vagues",
        "https://darglobal.co.uk/marea",
        "https://darglobal.co.uk/tabasheer",
        "https://darglobal.co.uk/about",
        "https://darglobal.co.uk/insights",
        "https://darglobal.co.uk/press"
    ]
    
    selected = []
    seen = set()

    for u in core_projects:
        u_clean = u.rstrip("/")
        if u_clean not in seen:
            selected.append(u)
            seen.add(u_clean)

    # Add other matching project pages up to 25
    priority_keywords = [
        "trump", "astera", "aida", "pagani", "missoni", "residences", "villas", "press"
    ]
    for kw in priority_keywords:
        for u in all_urls:
            if len(selected) >= 25:
                break
            u_clean = u.rstrip("/")
            if kw in u.lower() and u_clean not in seen:
                selected.append(u)
                seen.add(u_clean)

    return selected

def select_wasalt_urls() -> list[str]:
    """Select representative English and Arabic category pages across top Saudi cities."""
    categories_en = [
        "https://wasalt.sa/en/villas-for-sale-in-riyadh",
        "https://wasalt.sa/en/apartments-for-sale-in-riyadh",
        "https://wasalt.sa/en/apartments-for-rent-in-riyadh",
        "https://wasalt.sa/en/villas-for-rent-in-riyadh",
        "https://wasalt.sa/en/villas-for-sale-in-jeddah",
        "https://wasalt.sa/en/apartments-for-sale-in-jeddah",
        "https://wasalt.sa/en/apartments-for-rent-in-jeddah",
        "https://wasalt.sa/en/villas-for-sale-in-al-khobar",
        "https://wasalt.sa/en/apartments-for-sale-in-dammam",
        "https://wasalt.sa/en/properties-for-sale-in-makkah",
        "https://wasalt.sa/en/properties-for-sale-in-madinah",
    ]
    categories_ar = [
        "https://wasalt.sa/ar/فلل-للبيع-في-الرياض",
        "https://wasalt.sa/ar/شقق-للبيع-في-الرياض",
        "https://wasalt.sa/ar/شقق-للايجار-في-الرياض",
        "https://wasalt.sa/ar/فلل-للبيع-في-جدة",
        "https://wasalt.sa/ar/شقق-للبيع-في-جدة",
        "https://wasalt.sa/ar/عقارات-للبيع-في-مكة-المكرمة",
    ]
    return categories_en + categories_ar

def run_scrape():
    start_time = time.time()
    today = time.strftime("%Y-%m-%d")

    dg_checker = tr.dg_checker()
    wa_checker = tr.wa_checker()

    dg_urls = select_darglobal_urls()
    wa_urls = select_wasalt_urls()

    logger.info("Selected %d DarGlobal URLs and %d Wasalt URLs", len(dg_urls), len(wa_urls))

    stats = {
        "start_time": today,
        "darglobal": {"total_attempted": 0, "ok": 0, "blocked": 0, "robots_disallowed": 0, "http_error": 0, "facts_extracted": 0, "faqs_extracted": 0},
        "wasalt": {"total_attempted": 0, "ok": 0, "blocked": 0, "robots_disallowed": 0, "http_error": 0, "listings_extracted": 0},
    }

    crawl_logs = []
    dg_records = []
    wa_records = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # --- 1. Scrape DarGlobal ---
        logger.info("=== Starting DarGlobal Crawl ===")
        for url in dg_urls:
            stats["darglobal"]["total_attempted"] += 1
            if not dg_checker.is_allowed(url):
                logger.warning("DarGlobal robots disallowed: %s", url)
                stats["darglobal"]["robots_disallowed"] += 1
                crawl_logs.append({"url": url, "site": "darglobal", "status": "robots-disallowed", "timestamp": time.time()})
                continue

            try:
                time.sleep(1.6) # polite rate limiting >= 1.5s
                resp = page.goto(url, wait_until="domcontentloaded", timeout=25000)
                time.sleep(0.8) # allow any inline dynamic hydration
                http_status = resp.status if resp else 200

                html = page.content()
                if "incapsula incident id" in html.lower() or "visid_incap" in html.lower() and len(html) < 2000:
                    stats["darglobal"]["blocked"] += 1
                    crawl_logs.append({"url": url, "site": "darglobal", "status": "blocked", "http_status": http_status, "timestamp": time.time()})
                    logger.warning("DarGlobal BLOCKED on %s", url)
                    continue

                fact = extract_darglobal(html, url)
                # Also get page main text content
                page_text = page.evaluate("() => document.body.innerText")
                fact.raw_text = page_text[:4000] if page_text else ""

                fact_dict = asdict(fact)
                dg_records.append(fact_dict)

                stats["darglobal"]["ok"] += 1
                stats["darglobal"]["facts_extracted"] += 1
                stats["darglobal"]["faqs_extracted"] += len(fact.faq_pairs)
                crawl_logs.append({"url": url, "site": "darglobal", "status": "ok", "http_status": http_status, "faqs": len(fact.faq_pairs), "timestamp": time.time()})
                logger.info("DarGlobal OK [%d]: %s (Name: %s, FAQs: %d)", http_status, url, fact.name or "N/A", len(fact.faq_pairs))

            except Exception as e:
                logger.error("Error fetching %s: %s", url, e)
                stats["darglobal"]["http_error"] += 1
                crawl_logs.append({"url": url, "site": "darglobal", "status": "http-error", "error": str(e), "timestamp": time.time()})

        # --- 2. Scrape Wasalt ---
        logger.info("=== Starting Wasalt Crawl ===")
        for url in wa_urls:
            stats["wasalt"]["total_attempted"] += 1
            if not wa_checker.is_allowed(url):
                logger.warning("Wasalt robots disallowed: %s", url)
                stats["wasalt"]["robots_disallowed"] += 1
                crawl_logs.append({"url": url, "site": "wasalt", "status": "robots-disallowed", "timestamp": time.time()})
                continue

            try:
                time.sleep(1.8) # polite rate limiting >= 1.5s
                resp = page.goto(url, wait_until="domcontentloaded", timeout=25000)
                time.sleep(1.5) # allow hydration of listing offers
                http_status = resp.status if resp else 200

                html = page.content()
                if "just a moment..." in html.lower() and len(html) < 2000:
                    stats["wasalt"]["blocked"] += 1
                    crawl_logs.append({"url": url, "site": "wasalt", "status": "blocked", "http_status": http_status, "timestamp": time.time()})
                    logger.warning("Wasalt BLOCKED on %s", url)
                    continue

                offers = extract_wasalt(html, url, collection_date=today)
                for off in offers:
                    wa_records.append(asdict(off))

                stats["wasalt"]["ok"] += 1
                stats["wasalt"]["listings_extracted"] += len(offers)
                crawl_logs.append({"url": url, "site": "wasalt", "status": "ok", "http_status": http_status, "listings": len(offers), "timestamp": time.time()})
                logger.info("Wasalt OK [%d]: %s (%d listings extracted)", http_status, url, len(offers))

            except Exception as e:
                logger.error("Error fetching %s: %s", url, e)
                stats["wasalt"]["http_error"] += 1
                crawl_logs.append({"url": url, "site": "wasalt", "status": "http-error", "error": str(e), "timestamp": time.time()})

        browser.close()

    # Save outputs
    with open(DARGLOBAL_JSONL, "w", encoding="utf-8") as f:
        for r in dg_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(WASALT_JSONL, "w", encoding="utf-8") as f:
        for r in wa_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(CRAWL_LOG, "w", encoding="utf-8") as f:
        for l in crawl_logs:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")

    stats["duration_seconds"] = round(time.time() - start_time, 2)
    stats["total_pages_crawled"] = stats["darglobal"]["ok"] + stats["wasalt"]["ok"]
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    logger.info("Crawl completed in %.2fs. Stats saved to %s", stats["duration_seconds"], STATS_FILE)

if __name__ == "__main__":
    run_scrape()
