# DAR Operations Runbook

- **Tracked in:** DAR-35
- **System:** DAR — DarGlobal AI Property Assistant
- **Port:** `7860`

## Service Verification & Health Check

```bash
# 1. Probe health endpoint
curl -f http://localhost:7860/health
# Expected output: {"status":"ok","service":"DAR AI Property Assistant","version":"1.0.0", ...}

# 2. Check dataset metrics
curl -s http://localhost:7860/api/stats | jq .dataset_summary
```

---

## 5 Common Failure Modes and Operational Fixes

### 1. Failure Mode: Free LLM Quota Exhausted (`HTTP 429`)
- **Symptoms:** Chat API returns `HTTP 429` with message: *"The free AI service quota is currently busy."*
- **Root Cause:** OpenRouter free-tier accounts (< $10 purchased) are capped at 50 requests/day and 20 requests/minute.
- **Immediate Fix:**
  1. Verify answer caching is active (DAR-23 answers repeated queries without spending tokens).
  2. Fallback to secondary model: edit `OPENROUTER_PRIMARY_MODEL` in `.env` or space settings to another free model (e.g. `meta-llama/llama-3.3-70b-instruct:free`).
  3. (Recommended): Purchase $10 in OpenRouter credits to raise the daily limit to 1,000 requests/day while still calling free models.

### 2. Failure Mode: Upstream Free Model Removed or Deprecated (`HTTP 404 / 502`)
- **Symptoms:** Completion requests return `HTTP 502` with *"All candidate models failed"*.
- **Root Cause:** Free model identifiers on OpenRouter frequently rotate or get removed.
- **Immediate Fix:**
  1. Inspect the latest list of working free models at `https://openrouter.ai/models?max_price=0`.
  2. Update the `DEFAULT_MODELS` list in `src/rag/openrouter_client.py` or set `OPENROUTER_PRIMARY_MODEL` in environment variables.
  3. Restart the container: `docker compose restart`.

### 3. Failure Mode: Host Asleep / Cold Start Lag (`504 Gateway Timeout`)
- **Symptoms:** First HTTP request after inactivity takes > 20s or times out.
- **Root Cause:** Free cloud hosts (Render, Hugging Face Spaces) spin down idle instances.
- **Immediate Fix:**
  1. Send a pre-warm `GET /health` request 2-3 minutes before reviewer evaluation.
  2. If using Hugging Face Spaces, configure persistent storage or keep-alive cron probe.

### 4. Failure Mode: Container Failing Health Check (`unhealthy`)
- **Symptoms:** Docker reports container status `unhealthy`; port 7860 unreachable.
- **Root Cause:** Process crashed due to missing files or port collision.
- **Immediate Fix:**
  1. Inspect container logs: `docker compose logs --tail=100 dar-chatbot`.
  2. Verify required data files exist: `data/processed/chunks.json` and `data/processed/bm25_index.json`.
  3. Rebuild and restart: `docker compose up --build -d`.

### 5. Failure Mode: Missing or Invalid API Key (`HTTP 502 / 500`)
- **Symptoms:** API returns *"Authentication failed with the AI service provider"*.
- **Root Cause:** `OPENROUTER_API_KEY` is not set or expired.
- **Immediate Fix:**
  1. Check `.env` file or cloud secrets manager. Ensure key starts with `sk-or-v1-`.
  2. Export key: `export OPENROUTER_API_KEY="sk-or-..."`.
  3. Verify with live test: `curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/auth/key`.
