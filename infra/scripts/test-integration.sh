#!/usr/bin/env bash
# Pruebas del backend contra PostGIS en Docker (decisión 46b), desde cualquier carpeta:
#   infra/scripts/test-integration.sh [argumentos de pytest]
# Levanta la base de Compose, espera a que esté lista y corre pytest contra streetrepo_test
# con las credenciales del .env de la raíz (la API solo lee backend/.env, que no existe).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] || { echo "Falta $ENV_FILE (copiar .env.example y completarlo)" >&2; exit 1; }

COMPOSE=(docker compose -f "$ROOT/infra/docker-compose.yml" --env-file "$ENV_FILE")
"${COMPOSE[@]}" up -d --wait db >/dev/null

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
# 127.0.0.1 y no localhost: en Windows localhost prueba primero IPv6 y Docker publica en IPv4.
export POSTGRES_HOST=127.0.0.1
export POSTGRES_PORT="${DB_HOST_PORT:-5433}"
export POSTGRES_DB=streetrepo_test

cd "$ROOT/backend"
exec uv run pytest "$@"
