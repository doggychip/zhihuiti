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

# Start dashboard — uses $PORT, connects to DeepSeek via DEEPSEEK_API_KEY env var
CMD python -m zhihuiti.cli dashboard --db /app/data/zhihuiti.db --port ${PORT}
