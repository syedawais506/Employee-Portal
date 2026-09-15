#!/usr/bin/env bash
# Bring up the full local stack, run migrations, and seed demo data.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f docker/.env ]; then
  echo "docker/.env not found — copying docker/.env.example. Review it before deploying beyond local dev."
  cp docker/.env.example docker/.env
  # Replace each CHANGE-ME placeholder with its own freshly generated random
  # value — docker-compose.yml refuses to start with these unset, and running
  # local dev with the literal placeholder string as a real password/secret
  # would be a needlessly weak default even though nothing here is exposed
  # off this machine by default (see the MinIO port-binding note in README.md).
  while grep -q "CHANGE-ME-generate-with-openssl-rand-base64-32" docker/.env; do
    generated="$(openssl rand -base64 32 | tr -d '/+=')"
    # -- edits in place, one placeholder per iteration (they must each get a distinct value)
    perl -0pi -e "s/CHANGE-ME-generate-with-openssl-rand-base64-32/$generated/" docker/.env
  done
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
