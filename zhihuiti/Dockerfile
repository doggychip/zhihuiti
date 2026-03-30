FROM python:3.11-slim

WORKDIR /app

# Minimal deps for oracle server (no LLM, no SQLite, no git)
RUN pip install --no-cache-dir httpx rich

# Copy only what the oracle needs
COPY zhihuiti/__init__.py zhihuiti/
COPY zhihuiti/oracle_server.py zhihuiti/
COPY zhihuiti/crypto_oracle.py zhihuiti/
COPY zhihuiti/universal_oracle.py zhihuiti/
COPY zhihuiti/theory_intelligence.py zhihuiti/
COPY zhihuiti/scanner.py zhihuiti/
COPY zhihuiti/market_fetcher.py zhihuiti/
COPY zhihuiti/cross_domain.py zhihuiti/
COPY zhihuiti/oracle_intelligence.py zhihuiti/
COPY zhihuiti/api.py zhihuiti/
COPY client/src/data/ client/src/data/

# Regime history persistence
VOLUME /app/data
ENV HOME=/app/data

EXPOSE 8377
ENV PORT=8377

CMD ["python", "-m", "zhihuiti.oracle_server"]
