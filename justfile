# Dev environment recipes.
# Run from the repo root: `just <recipe>`.

# List recipes.
default:
    @just --list

# Start the dev environment (Postgres, Redis, and mechanism on localhost:8001).
dev-up:
    docker compose -f compose-dev.yml up -d

# Stop the dev environment (preserves the data volumes).
dev-down:
    docker compose -f compose-dev.yml down

# Tail container logs. Forwards args, so `just dev-logs -f mechanism` works.
dev-logs *args:
    docker compose -f compose-dev.yml logs {{args}}

# Wipe Postgres AND Redis data volumes, bring services up fresh, restore Postgres from a dump.
dev-init dump:
    docker compose -f compose-dev.yml down -v
    docker compose -f compose-dev.yml up -d
    @echo "(waiting for postgres to accept connections)"
    @until docker compose -f compose-dev.yml exec -T postgres pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
    docker compose -f compose-dev.yml exec -T postgres pg_restore \
        --username=postgres \
        --dbname=postgres \
        --single-transaction \
        --no-owner \
        --no-acl \
        < {{dump}}

# Run the pytest suite. conftest.py spins up ephemeral pgvector + redis
# containers via Testcontainers, loads schema.sql, and tears them down at
# session end. Multiple sessions (e.g. parallel issue-fixer agents) can
# run without colliding because each session gets its own containers on
# random host ports.
test:
    cd mechanism && \
        MECHANISM_TOKEN=test-token-not-a-real-secret \
        LOGFIRE_IGNORE_NO_CONFIG=1 \
        uv run pytest

# Materialize seed.sql by filling embeddings into seed.sql.template via Bifrost.
# Run after editing the template, or after swapping embedding models.
seed-generate:
    ./mechanism/tests/fixtures/generate.py
