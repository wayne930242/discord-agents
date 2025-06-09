# Frontend build stage
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Install frontend dependencies
RUN npm install -g pnpm && \
    pnpm install --frozen-lockfile

# Copy frontend source and build
COPY frontend/ ./
RUN pnpm build

# Backend stage (keeping original uv setup)
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Copy built frontend from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

VOLUME ["/app/data"]

EXPOSE ${PORT}

ENV PATH="/app/.venv/bin:$PATH"
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
