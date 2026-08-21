#!/bin/sh
set -eu

echo "Applying database migrations..."
alembic upgrade head

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    echo "Loading idempotent fictional development data..."
    python -m app.seed
fi

exec "$@"
