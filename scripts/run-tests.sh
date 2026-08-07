#!/usr/bin/env bash
# Run backend lint, type-check, and test suite.
set -euo pipefail
cd "$(dirname "$0")/../backend"

ruff check .
mypy app
pytest --cov=app --cov-report=term-missing
