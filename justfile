# Alpha dev environment recipes.
# Run from the repo root: `just <recipe>`.

# List recipes.
default:
    @just --list

# Start the dev environment (Postgres and Redis, both on localhost).
dev-up:
    docker compose -f compose-dev.yml up -d

# Stop the dev environment (preserves the data volumes).
dev-down:
    docker compose -f compose-dev.yml down

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
