FROM python:3.11-slim

WORKDIR /app

# Install system deps + all Python deps (full package support)
RUN apt-get update && apt-get install -y --no-install-recommends curl git && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY setup.py pyproject.toml ./
COPY zhihuiti/ zhihuiti/
COPY client/src/data/ client/src/data/
RUN test -s client/src/data/theories.json \
    && test -s client/src/data/collisions.json \
    && pip install --no-cache-dir -e .

VOLUME /app/data
ENV HOME=/app/data

EXPOSE 8377
ENV PORT=8377

# When OPENROUTER_API_KEY is set, real agents are enabled automatically
# Set ZHIHUITI_AUTO_EVOLVE=1 to enable background goal execution
ENV ZHIHUITI_DB="/app/data/zhihuiti.db"
ENV ZHIHUITI_DATA="/app/data"
ENV ZHIHUITI_ORACLE_SCAN="1"
ENV ZHIHUITI_ORACLE_SCAN_INTERVAL="1800"

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:${PORT}/healthz', timeout=3).raise_for_status()" || exit 1

CMD ["python", "-m", "zhihuiti.oracle_server"]
