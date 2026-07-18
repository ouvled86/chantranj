# syntax=docker/dockerfile:1
# Build context = repo root. Debian's stockfish package installs to /usr/games/stockfish.

FROM python:3.12-slim AS base
RUN apt-get update \
 && apt-get install -y --no-install-recommends stockfish \
 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    STOCKFISH_PATH=/usr/games/stockfish
WORKDIR /app
COPY engine/pyproject.toml engine/uv.lock* ./

FROM base AS dev
RUN uv sync
COPY engine/ .
EXPOSE 9000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000", "--reload"]

FROM base AS prod
RUN uv sync --no-dev
COPY engine/ .
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 9000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:9000/healthz')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
