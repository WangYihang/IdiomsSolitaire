# syntax=docker/dockerfile:1
# Build stage
FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev && \
    uv cache clean

# Runtime stage
FROM python:3.12-slim-bookworm
ENV TZ=Asia/Shanghai
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN apt-get update && \
    apt-get install -y --no-install-recommends git npm nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1000 app && \
    useradd -m -u 1000 -g 1000 -s /bin/bash -d /app app && \
    npm install -g @anthropic-ai/claude-code
USER app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app pyproject.toml uv.lock ./
COPY --chown=app:app .git ./.git
COPY --chown=app:app forensics_agent ./forensics_agent
RUN uv run python -m forensics_agent --version
ENTRYPOINT [ "uv", "run", "python", "-m", "forensics_agent" ]
