FROM python:3.11-slim

WORKDIR /app

# Install system deps + all Python deps (full package support)
RUN apt-get update && apt-get install -y --no-install-recommends curl git && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY setup.py pyproject.toml ./
COPY zhihuiti/ zhihuiti/
RUN pip install --no-cache-dir -e .

# Copy frontend data
COPY client/src/data/ client/src/data/

VOLUME /app/data
ENV HOME=/app/data

EXPOSE 8377
ENV PORT=8377

# When OPENROUTER_API_KEY is set, real agents are enabled automatically
# Set ZHIHUITI_AUTO_EVOLVE=1 to enable background goal execution
ENV ZHIHUITI_DB="/app/data/zhihuiti.db"

CMD ["python", "-m", "zhihuiti.oracle_server"]
