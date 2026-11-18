# Cloud Deployment Guide

- **Tracked in:** DAR-32, DAR-45
- **Primary Platform:** Hugging Face Spaces (Docker SDK) — $0 Free Tier
- **Fallback Platform:** Render.com (Web Service) — $0 Free Tier

---

## Deploying to Hugging Face Spaces (Recommended $0 Platform)

1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space).
2. Select **Space SDK: Docker** (Blank).
3. Clone your Space repo and push this project's files, or add the Space as a git remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/dar-chatbot
   git push space master
   ```
4. Configure Secret:
   - Go to **Settings > Variables and secrets**.
   - Click **New secret**.
   - Name: `OPENROUTER_API_KEY`, Value: your OpenRouter API key.
5. Hugging Face will automatically build the `Dockerfile` and serve the application on standard port `7860`.
6. Access your public HTTPS application at `https://<your-username>-dar-chatbot.hf.space`.

---

## Deploying to Render.com ($0 Fallback)

1. Connect your GitHub repository to [dashboard.render.com](https://dashboard.render.com).
2. Choose **New > Web Service**.
3. Select **Environment: Docker**.
4. Under **Environment Variables**, add:
   - `OPENROUTER_API_KEY`: your OpenRouter API key
   - `PORT`: `7860`
5. Click **Create Web Service**.
6. Render builds the Docker container and serves it at `https://<service-name>.onrender.com`.
