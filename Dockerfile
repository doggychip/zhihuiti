FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY setup.py pyproject.toml ./
COPY zhihuiti/ zhihuiti/
RUN pip install --no-cache-dir -e .

# Zeabur injects PORT; default to 8377
ENV PORT=8377
EXPOSE 8377

# Persist data in a volume
VOLUME /app/data

# Default: start dashboard with CriticAI monitoring
# Set CRITICAI_URL to enable cross-system monitoring
# Set MONITOR_INTERVAL to control check frequency (default: 30m)
ENV CRITICAI_URL=""
ENV MONITOR_INTERVAL="30m"

# Start script: optionally set up CriticAI monitor, then launch dashboard
CMD sh -c '\
  if [ -n "$CRITICAI_URL" ]; then \
    echo "Setting up CriticAI monitor at $CRITICAI_URL (interval: $MONITOR_INTERVAL)"; \
    python -m zhihuiti.cli criticai watch --url "$CRITICAI_URL" --interval "$MONITOR_INTERVAL" --db /app/data/zhihuiti.db; \
  fi; \
  python -m zhihuiti.cli dashboard --db /app/data/zhihuiti.db --port ${PORT}'
