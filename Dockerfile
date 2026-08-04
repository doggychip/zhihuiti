FROM python:3.11-slim

WORKDIR /app

COPY zhihuiti/setup.py zhihuiti/pyproject.toml ./
COPY zhihuiti/zhihuiti/ zhihuiti/
RUN pip install --no-cache-dir -e .

COPY zhihuiti/client/src/data/ client/src/data/

VOLUME /app/data
ENV HOME=/app/data

EXPOSE 8377
ENV PORT=8377

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:${PORT}/healthz', timeout=3).raise_for_status()" || exit 1

CMD ["python", "-m", "zhihuiti.oracle_server"]
