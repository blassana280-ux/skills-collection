FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    OMNI_HOST=0.0.0.0 \
    OMNI_PORT=8000

WORKDIR /srv/omni

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY docs ./docs
COPY tests ./tests
COPY pyproject.toml README.md ./

RUN mkdir -p data/backups && \
    adduser --disabled-password --gecos '' --uid 10001 omni && \
    chown -R omni:omni /srv/omni
USER omni

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
