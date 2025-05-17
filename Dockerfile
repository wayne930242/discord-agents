FROM ghcr.io/astral-sh/uv\:python3.13-bookworm-slim

WORKDIR /app

ENV UV\_COMPILE\_BYTECODE=1 \
    UV\_LINK\_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

VOLUME ["/app/data"]

EXPOSE ${PORT}

ENTRYPOINT []

CMD ["sh", "-c", "uv run python discord_agents/main.py"]
