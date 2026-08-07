#!/usr/bin/env bash
# Populate the database with a Super Admin and two demo companies.
set -euo pipefail
cd "$(dirname "$0")/../backend"
python -m scripts.seed
