
#!/usr/bin/env bash

cd /home/ubuntu/docker/surgery-website/Bomboclat

set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Creating pre-deployment backup..."
./home/ubuntu/docker/open-surgery/scripts/backup.sh


echo "Pulling application changes..."
git pull --ff-only

DEPLOY_COMMIT="$(git rev-parse HEAD)"
OLD_CONTAINER="$(docker compose ps -q app 2>/dev/null || true)"

echo "Deploying commit: $DEPLOY_COMMIT"

echo "Building updated application image..."
docker compose build --pull app

echo "Recreating application container..."
docker compose up -d --no-deps --force-recreate app

NEW_CONTAINER="$(docker compose ps -q app)"

if [[ -z "$NEW_CONTAINER" ]]; then
    echo "The application container was not created."
    docker compose logs --tail=200 app
    exit 1
fi

if [[ "$OLD_CONTAINER" == "$NEW_CONTAINER" ]]; then
    echo "Warning: application container ID did not change."
else
    echo "Application container recreated:"
    echo "  old: ${OLD_CONTAINER:-none}"
    echo "  new: $NEW_CONTAINER"
fi

echo "Verifying deployed frontend files..."
HOST_HASH="$(sha256sum frontend/assets/js/script.js | awk '{print $1}')"
CONTAINER_HASH="$(
    docker compose exec -T app sha256sum /app/frontend/assets/js/script.js |
    awk '{print $1}'
)"

if [[ "$HOST_HASH" != "$CONTAINER_HASH" ]]; then
    echo "Deployment verification failed."
    echo "Host script hash:      $HOST_HASH"
    echo "Container script hash: $CONTAINER_HASH"
    docker compose logs --tail=200 app
    exit 1
fi

echo "Frontend files match the checked-out repository."

echo "Waiting for health check..."
for attempt in {1..30}; do
    status="$(
        docker inspect \
            --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' \
            "$NEW_CONTAINER"
    )"

    if [[ "$status" == "healthy" ]]; then
        echo "Deployment of $DEPLOY_COMMIT is healthy."
        docker compose ps
        exit 0
    fi

    if [[ "$status" == "unhealthy" ]]; then
        echo "Application became unhealthy."
        docker compose logs --tail=200 app
        exit 1
    fi

    sleep 2
done

echo "Application did not become healthy."
docker compose logs --tail=200 app
exit 1
