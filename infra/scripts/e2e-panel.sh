#!/usr/bin/env bash
# Pruebas de punta a punta del panel (Playwright) en un stack de Compose aparte:
#   infra/scripts/e2e-panel.sh [argumentos de playwright test]
#
# Usa el proyecto «street-repo-e2e», con su propia base, sus volúmenes y otros puertos. Las
# pruebas cambian estados y guardan pesos (crean versiones que no se borran y recalculan
# todos los reportes activos): así no tocan la base de desarrollo ni sus reportes.
#
# La primera vez descarga las vías y los servicios de OSM (osm-import); después reutiliza
# el volumen. Para borrarlo todo:
#   docker compose -p street-repo-e2e -f infra/docker-compose.yml --env-file .env down -v
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] || { echo "Falta $ENV_FILE (copiar .env.example y completarlo)" >&2; exit 1; }

# Las variables del entorno mandan sobre las de --env-file.
export POSTGRES_DB=streetrepo_e2e
export DB_HOST_PORT="${E2E_DB_PORT:-5434}"
export API_PORT="${E2E_API_PORT:-8001}"
export API_BIND_ADDRESS=127.0.0.1
export ADMIN_WEB_PORT="${E2E_WEB_PORT:-8081}"
export ADMIN_API_BASE_URL="http://localhost:${API_PORT}"
export CORS_ORIGINS="http://localhost:${ADMIN_WEB_PORT}"

COMPOSE=(docker compose -p street-repo-e2e -f "$ROOT/infra/docker-compose.yml" --env-file "$ENV_FILE")
cli() { "${COMPOSE[@]}" exec -T api python -m app.cli "$@"; }

echo "==> Levantando el stack de pruebas (panel en http://localhost:${ADMIN_WEB_PORT})"
"${COMPOSE[@]}" up -d --build --wait db api admin-web
# Al terminar se detienen los contenedores; los volúmenes (OSM ya cargado) se conservan.
trap '"${COMPOSE[@]}" stop >/dev/null 2>&1 || true' EXIT

roads="$("${COMPOSE[@]}" exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "SELECT count(*) FROM via"')"
if [[ "$roads" == "0" ]]; then
  echo "==> Cargando vías y servicios críticos de OSM (solo la primera vez)"
  cli osm-import
fi

echo "==> Datos de demostración recién cargados"
cli seed-demo --remove
cli seed-demo

# Cuenta nueva en cada ejecución, con contraseña aleatoria que no se guarda en ningún archivo.
E2E_ADMIN_EMAIL="e2e-$(date +%s)@example.com"
E2E_ADMIN_PASSWORD="$(openssl rand -hex 16)"
printf '%s\n%s\n' "$E2E_ADMIN_PASSWORD" "$E2E_ADMIN_PASSWORD" |
  cli create-admin --name "Funcionaria E2E" --email "$E2E_ADMIN_EMAIL" >/dev/null 2>&1
export E2E_ADMIN_EMAIL E2E_ADMIN_PASSWORD
export E2E_BASE_URL="http://localhost:${ADMIN_WEB_PORT}"

cd "$ROOT/admin-web"
npx playwright test "$@"
