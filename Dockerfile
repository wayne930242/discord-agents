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
# Try to read from environment first, then fallback to ARG
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://localhost:8080/api/v1}
RUN echo "Building with VITE_API_BASE_URL: $VITE_API_BASE_URL" && pnpm build

# Backend stage with optimized Playwright support
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PLAYWRIGHT_BROWSERS_PATH=/app/browsers

# Install minimal system dependencies for Playwright (reduced set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy and install Python dependencies first (for better caching)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Copy application code
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Install Playwright with optimizations for cloud deployment
ENV PATH="/app/.venv/bin:$PATH"
# Set browser path to avoid permission issues
ENV PLAYWRIGHT_BROWSERS_PATH=/app/browsers
# Only install chromium (not all browsers) to save space and memory
RUN mkdir -p /app/browsers && \
    playwright install chromium --with-deps && \
    # Clean up unnecessary files to reduce image size
    rm -rf /root/.cache/ms-playwright && \
    rm -rf /tmp/* && \
    # Set proper permissions
    chmod -R 755 /app/browsers

# Copy built frontend from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

VOLUME ["/app/data"]

EXPOSE ${PORT}

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/v1/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
