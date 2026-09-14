#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="/srv/backups/opensurgery"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

cd "$PROJECT_DIR"

app_was_running=false

cleanup() {
    if [[ "$app_was_running" == "true" ]]; then
        docker compose start app >/dev/null
    fi
}

trap cleanup EXIT

if docker compose ps --status running --services | grep -qx app; then
    app_was_running=true
    docker compose stop app
fi

echo "Backing up PostgreSQL..."
docker compose exec -T db \
    pg_dump \
    --username=opensurgery \
    --dbname=opensurgery \
    --format=custom \
    --no-owner \
    > "${BACKUP_DIR}/database.dump"

test -s "${BACKUP_DIR}/database.dump"

echo "Validating PostgreSQL archive..."
docker compose exec -T db \
    pg_restore --list \
    < "${BACKUP_DIR}/database.dump" \
    > "${BACKUP_DIR}/database-contents.txt"

echo "Backing up uploaded media..."
docker compose run --rm --no-deps \
    --entrypoint tar app \
    -C /data/media -czf - . \
    > "${BACKUP_DIR}/media.tar.gz"

echo "Recording application version..."
git rev-parse HEAD > "${BACKUP_DIR}/git-commit.txt"
git status --short > "${BACKUP_DIR}/git-status.txt"
docker compose config > "${BACKUP_DIR}/compose-config.yml"

echo "Backing up environment configuration..."
install -m 600 .env "${BACKUP_DIR}/environment.env"

sha256sum \
    "${BACKUP_DIR}/database.dump" \
    "${BACKUP_DIR}/media.tar.gz" \
    "${BACKUP_DIR}/git-commit.txt" \
    > "${BACKUP_DIR}/SHA256SUMS"

echo "Backup completed: ${BACKUP_DIR}"
