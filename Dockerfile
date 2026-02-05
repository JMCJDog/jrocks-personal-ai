FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# copy requirements and constraints first for layer caching
COPY Resources/constraints.txt Resources/requirements.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir -e . -c Resources/constraints.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy source and resources
COPY src/ ./src/
COPY Resources/ ./Resources/
COPY .env.example .env

RUN useradd -m app || true \
    && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "-b", "0.0.0.0:8000", "--access-logfile", "-", "--workers", "1"]
