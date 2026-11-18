# Data Refresh Guide

- **Tracked in:** DAR-45, Risk R8

---

## When to Refresh
Real estate prices and availability change periodically. Follow this procedure to refresh the indexed dataset from `darglobal.co.uk` and `wasalt.sa`.

## Step-by-Step Refresh Procedure

```bash
# 1. Ensure Playwright browser binaries are installed
playwright install chromium

# 2. Discover new sitemap URLs
python src/scraper/discover_darglobal.py

# 3. Execute polite crawl (respects robots.txt and >= 1.5s rate limits)
python src/scraper/crawl_runner.py

# 4. Clean, chunk, deduplicate, and rebuild search index
python src/processing/index_builder.py

# 5. Run evaluation benchmark to verify quality
python src/eval/runner.py

# 6. Commit updated data/processed/ and rebuild Docker image
git add data/
git commit -m "chore: refresh real estate crawl snapshot"
docker compose up --build -d
```
