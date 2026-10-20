FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WORKSPACE_DIR=/data/workspace

WORKDIR /app

# build-essential keeps sdist-only dependencies (e.g. sgmllib3k) installable.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-live.txt ./
ARG INSTALL_GPT_RESEARCHER=0
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_GPT_RESEARCHER" = "1" ]; then pip install --no-cache-dir -r requirements-live.txt; fi

COPY spectrascholar ./spectrascholar
COPY web ./web

RUN groupadd --system app \
    && useradd --system --gid app --create-home app \
    && mkdir -p /data/workspace \
    && chown -R app:app /app /data

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1

CMD ["uvicorn", "spectrascholar.main:app", "--host", "0.0.0.0", "--port", "8000"]
