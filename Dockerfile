# Production image for mechanism.

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Cache deps separately from source so source-only edits don't
# rebuild the deps layer. The uv cache mount persists downloaded
# wheels across builds, so a lockfile change re-resolves but
# doesn't re-download from PyPI.
COPY mechanism/pyproject.toml mechanism/uv.lock /app/mechanism/
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    cd /app/mechanism && uv sync --frozen --no-install-project --no-dev

# Now the source.
COPY mechanism/ /app/mechanism/
RUN cd /app/mechanism && uv sync --frozen --no-dev

ENV PATH="/app/mechanism/.venv/bin:${PATH}"

WORKDIR /app/mechanism

EXPOSE 8000

# Bind to 0.0.0.0 inside the container; the compose port-mapping
# restricts external reach to 127.0.0.1 on the host.
CMD ["uvicorn", "mechanism.app:app", "--host", "0.0.0.0", "--port", "8000"]
