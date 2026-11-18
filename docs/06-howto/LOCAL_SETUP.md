# Local Development Setup Guide

- **Tracked in:** DAR-45
- **Verified on:** Windows 11 / Python 3.11+ / PowerShell

---

## Prerequisites
- Python 3.10+ (Verified on Python 3.11 / 3.14)
- Git

## Step-by-Step Setup

```bash
# 1. Clone repository
git clone https://github.com/dar-project/dar-chatbot.git
cd dar-chatbot

# 2. Create virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
# source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment configuration
cp .env.example .env
# Edit .env and insert your OPENROUTER_API_KEY

# 5. Run test suite to verify installation
pytest
```

## Running the Web Server Locally

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 7860 --reload
```

- Open the chat UI in your browser: `http://127.0.0.1:7860`
- Interactive Swagger documentation: `http://127.0.0.1:7860/docs`
- OpenAPI Specification: `http://127.0.0.1:7860/openapi.yaml`
