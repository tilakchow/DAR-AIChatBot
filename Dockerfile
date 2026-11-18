# ==============================================================================
# Dockerfile · DAR — DarGlobal AI Property Assistant
# Complies with DAR-27: slim Python image, non-root user, health check
# ==============================================================================

FROM python:3.11-slim

# Set environment flags
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and baked retrieval index
COPY src/ /app/src/
COPY data/processed/ /app/data/processed/
COPY data/summary.json /app/data/summary.json
COPY openapi.yaml /app/openapi.yaml

# Security constraint (DAR-27): Run as a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose server port (7860 matches Hugging Face Spaces default & Render)
EXPOSE 7860

# Health check (DAR-27)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start Uvicorn server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
