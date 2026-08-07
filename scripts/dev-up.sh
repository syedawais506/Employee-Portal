#!/usr/bin/env bash
# Bring up the full local stack, run migrations, and seed demo data.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f docker/.env ]; then
  echo "docker/.env not found — copying docker/.env.example. Review it before deploying beyond local dev."
  cp docker/.env.example docker/.env
fi

docker compose -f docker/docker-compose.yml up -d --build

echo "Waiting for Postgres to become healthy..."
until docker compose -f docker/docker-compose.yml exec -T postgres pg_isready -U "${POSTGRES_USER:-portal}" >/dev/null 2>&1; do
  sleep 1
done

docker compose -f docker/docker-compose.yml exec -T backend alembic upgrade head
docker compose -f docker/docker-compose.yml exec -T backend python -m scripts.seed

echo ""
echo "Stack is up:"
echo "  App (frontend + API via gateway): http://localhost:8080"
echo "  API docs:                         http://localhost:8080/docs"
echo "  MailHog (dev email capture):      http://localhost:8025"
echo "  MinIO console:                    http://localhost:9001"
