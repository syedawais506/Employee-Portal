#!/usr/bin/env bash
# Run Alembic migrations against the configured DATABASE_URL.
set -euo pipefail
cd "$(dirname "$0")/../backend"
alembic upgrade head
