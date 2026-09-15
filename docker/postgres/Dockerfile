FROM postgres:16-alpine

# Baked in at build time rather than bind-mounted at runtime: this repo lives
# under ~/Desktop on macOS, and Docker Desktop's runtime bind-mount sharing
# refuses that path outside its own file-sharing allowlist even though build
# contexts (this COPY) are unaffected — and baking it in is the more portable
# choice for a real deploy host anyway, not just a workaround.
COPY postgres-initdb/*.sh /docker-entrypoint-initdb.d/
