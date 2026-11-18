# REST API Reference

- **Tracked in:** DAR-45
- **Specification:** OpenAPI 3.1 (`openapi.yaml`)
- **Base URL:** `http://localhost:7860` (or live HTTPS deployment URL)

---

## Endpoints

### 1. `POST /api/chat`
Ask a question to the AI property assistant.

**Request Body (`application/json`):**
```json
{
  "query": "What are the starting prices for The Astera?",
  "site": "darglobal"
}
```
- `query` (string, required): Question text (1 to 1,000 characters).
- `site` (string, optional): Portal filter (`darglobal` or `wasalt`).

**Response (`200 OK`):**
```json
{
  "answer": "Starting prices for The Astera, Interiors by Aston Martin begin from AED 2,150,000 [1].",
  "sources": [
    {
      "index": 1,
      "title": "What are the starting prices for The Astera?",
      "url": "https://darglobal.co.uk/the-astera",
      "site": "darglobal",
      "chunk_type": "faq"
    }
  ],
  "model_used": "nvidia/nemotron-3.5-super-vl:free",
  "latency_ms": 1420.5,
  "cached": false
}
```

**Errors:**
- `400 Bad Request`: Prompt injection or security violation detected.
- `422 Unprocessable Entity`: Input is empty or exceeds 1,000 characters.
- `429 Too Many Requests`: Client IP exceeded rate limit (15 requests/minute).
- `502 Bad Gateway`: AI provider quota busy or upstream authentication error.

---

### 2. `GET /health`
System health check endpoint for container and deployment monitoring.

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "service": "DAR AI Property Assistant",
  "version": "1.0.0",
  "prompt_version": "1.0.0",
  "indexed_chunks": 179
}
```

---

### 3. `GET /api/stats`
Returns the verified dataset metrics generated from `data/summary.json`.

---

### 4. `GET /openapi.yaml`
Returns the machine-readable OpenAPI 3.1 specification in YAML format.
