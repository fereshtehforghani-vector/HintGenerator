FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gunicorn with a single worker and no request timeout — the RAG rebuild
# can take several minutes, so we rely on Cloud Run's --timeout setting.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "0", "main:app"]
