# Configuration Reference

- **Tracked in:** DAR-29
- **Standard:** Twelve-Factor App configuration via environment variables only

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** | None | Secret Bearer key for OpenRouter API. Kept in host secrets manager or local `.env` only. Never hardcoded or committed. |
| `HOST` | No | `0.0.0.0` | Bind host address for the FastAPI / Uvicorn server. |
| `PORT` | No | `7860` | Server listening port. Port `7860` is selected for universal compatibility (default port for Hugging Face Spaces, Render, and Fly.io). |
| `OPENROUTER_PRIMARY_MODEL` | No | `nvidia/nemotron-3.5-super-vl:free` | Primary model identifier sent to OpenRouter chat completion. |
| `ENVIRONMENT` | No | `production` | Deployment mode: `development` or `production`. |

## Security Rules
1. `.env` is explicitly declared in `.gitignore` and must never be tracked in git.
2. The Docker image does not contain `.env` or any baked credentials.
3. In production deployments (Hugging Face Spaces, Render, etc.), set `OPENROUTER_API_KEY` exclusively via the platform's Secret Management dashboard.
