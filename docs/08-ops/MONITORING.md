# Monitoring and Logging Specification

- **Tracked in:** DAR-35
- **Standard:** Privacy-by-design & OWASP LLM logging controls

## What IS Logged

1. **HTTP Access Logs:** Standard Uvicorn request log: timestamp, client IP, HTTP method, path, response status code.
2. **Model Invocations:** The model identifier that answered each request (e.g. `nvidia/nemotron-3.5-super-vl:free` or fallback), and the completion latency in milliseconds.
3. **Retrieval Metrics:** Number of chunks retrieved, top retrieval scores, and whether an answer was served from the in-memory cache.
4. **Security & Guardrail Events:** Triggered prompt injection attempts (logged as security warnings with client IP), rate limit violations, and payload length violations.
5. **Crawl Outcome Counts:** Total pages attempted, HTTP status codes, and counts of extracted records saved to `data/raw/crawl_log.jsonl`.

## What IS NOT Logged (Strict Privacy & Compliance)

1. **API Keys / Secrets:** The `OpenRouterClient` sanitizes all log outputs and exception messages to ensure `OPENROUTER_API_KEY` never appears in logs.
2. **Personal Identifiable Information (PII):** In compliance with Wasalt's `llms.txt`, no seller names, personal telephone numbers, or WhatsApp links are logged or stored.
3. **Raw Conversation Transcripts:** Full user prompts and assistant outputs are not persistently written to disk or third-party telemetry to protect user privacy.
