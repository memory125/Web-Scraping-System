FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir crawl4ai && \
    pip install --no-cache-dir fastapi uvicorn pydantic python-dotenv psutil

RUN python -c "import crawl4ai; crawl4ai.install()" || true

ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8001

EXPOSE 8001

COPY backend/main.py /app/main.py

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
