#!/usr/bin/env bash
# Safe local configuration generation: creates .env with random local-only
# secrets if it doesn't already exist. Never overwrites an existing .env.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  echo ".env already exists, leaving it untouched."
  exit 0
fi

rand() { python - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
}

cp .env.example .env
POSTGRES_PW=$(rand)
RABBIT_PW=$(rand)
JWT=$(rand)
GRAFANA_PW=$(rand)

# Portable in-place sed for both GNU and BSD sed.
sedi() { if sed --version >/dev/null 2>&1; then sed -i "$@"; else sed -i '' "$@"; fi; }

sedi "s#^POSTGRES_PASSWORD=.*#POSTGRES_PASSWORD=${POSTGRES_PW}#" .env
sedi "s#^RABBITMQ_DEFAULT_PASS=.*#RABBITMQ_DEFAULT_PASS=${RABBIT_PW}#" .env
sedi "s#^JWT_SECRET=.*#JWT_SECRET=${JWT}#" .env
sedi "s#^GRAFANA_ADMIN_PASSWORD=.*#GRAFANA_ADMIN_PASSWORD=${GRAFANA_PW}#" .env

echo "Generated .env with random local-only secrets."
