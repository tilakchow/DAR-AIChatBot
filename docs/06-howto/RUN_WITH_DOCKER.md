# Running DAR with Docker and Docker Compose

- **Tracked in:** DAR-27, DAR-28, DAR-30
- **Base image:** `python:3.11-slim`
- **Security:** Non-root execution (`appuser`, UID 1000)
- **Healthcheck:** `curl -f http://localhost:7860/health` (30s interval)

## Quick Start (3 Commands)

```bash
# 1. Clone repository
git clone https://github.com/tilakchow/DAR-AIChatBot.git
cd DAR-AIChatBot

# 2. Configure environment (add your OpenRouter key)
cp .env.example .env
# Edit .env and insert: OPENROUTER_API_KEY=your_key_here

# 3. Launch container with Docker Compose
docker compose up --build -d
```

Access the chat interface at: **`http://localhost:7860`**  
Access the interactive OpenAPI Swagger docs at: **`http://localhost:7860/docs`**  
Access the OpenAPI spec at: **`http://localhost:7860/openapi.yaml`**  

## Standalone Docker Build

```bash
# Build the image
docker build -t dar-chatbot:v1.0.0 .

# Run container with injected environment secret
docker run -d \
  -p 7860:7860 \
  -e OPENROUTER_API_KEY="your_key_here" \
  --name dar-chatbot \
  dar-chatbot:v1.0.0
```

## Image Specifications
- **Base OS:** Debian GNU/Linux 12 (bookworm) / Python 3.11-slim
- **Exposed Port:** `7860`
- **Estimated Image Size:** ~185 MB (Lightweight, zero Torch/CUDA dependencies)
- **Data baked into image:** `data/processed/chunks.json`, `data/processed/bm25_index.json`, `data/summary.json`
- **Runtime downloads required:** 0 MB (Self-contained instant cold start)
