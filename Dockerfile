FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx rich

COPY zhihuiti/ zhihuiti/
COPY client/src/data/ client/src/data/

VOLUME /app/data
ENV HOME=/app/data

EXPOSE 8377
ENV PORT=8377

CMD ["python", "-m", "zhihuiti.oracle_server"]
