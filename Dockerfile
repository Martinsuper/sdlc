FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml README.md ./
COPY sdlc/ sdlc/

# Install dependencies
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python .

# Runtime stage
FROM python:3.11-slim

RUN groupadd -r sdlc && useradd -r -g sdlc sdlc

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/sdlc /app/sdlc

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

USER sdlc
WORKDIR /project

ENTRYPOINT ["sdlc"]
CMD ["--help"]
