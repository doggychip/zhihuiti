FROM python:3.11-slim

WORKDIR /app

# Install curl and git for tool execution
RUN apt-get update && apt-get install -y --no-install-recommends curl git && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY setup.py pyproject.toml ./
COPY zhihuiti/ zhihuiti/
RUN pip install --no-cache-dir -e .

# Zeabur injects PORT; default to 8377
ENV PORT=8377
EXPOSE 8377

# Persist data in a volume
VOLUME /app/data

# Default: start dashboard with optional auto-trading
# Set ALPHAARENA_AUTO_TRADE=1 to enable automatic trading
# Set ALPHAARENA_TRADE_INTERVAL to control frequency in seconds (default: 7200 = 2h)
ENV CRITICAI_URL=""
ENV MONITOR_INTERVAL="30m"
ENV ALPHAARENA_AUTO_TRADE=""
ENV ALPHAARENA_TRADE_INTERVAL="7200"
ENV ALPHAARENA_URL=""
ENV ALPHAARENA_API_KEY=""
ENV ALPHAARENA_AGENT_ID=""

CMD python -m zhihuiti.cli dashboard --db /app/data/zhihuiti.db --port ${PORT}
