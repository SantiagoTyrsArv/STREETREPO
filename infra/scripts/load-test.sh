#!/usr/bin/env bash
# Prueba de carga de la API con Locust (fase 8, decisión 68) en un stack de Compose aparte:
#   infra/scripts/load-test.sh [argumentos de locust, p. ej. -t 30s -u 5]
#
# Usa el proyecto «street-repo-load», con su propia base y otros puertos: no toca la base de
# desarrollo. Las cifras son medidas del sistema en este equipo con datos de demostración, no
# resultados de campo ni del capítulo 4.
#
# Los límites de solicitudes se suben SOLO en este stack (variables de entorno de abajo): con
# 50 usuarios desde una sola IP, los valores por defecto cortarían la prueba en segundos.
# Al terminar, aunque Locust falle, se borran las cuentas de carga y los datos de demostración.
# Los resultados (CSV y HTML de Locust) quedan en .superpowers/carga/<fecha-hora>/, fuera de git.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] || { echo "Falta $ENV_FILE (copiar .env.example y completarlo)" >&2; exit 1; }

USERS="${LOAD_USERS:-50}"
SPAWN_RATE="${LOAD_SPAWN_RATE:-5}"
DURATION="${LOAD_DURATION:-5m}"
ACCOUNTS="${LOAD_ACCOUNTS:-60}"
# Una carpeta por corrida: así no se pisan los resultados de corridas anteriores.
OUT="$ROOT/.superpowers/carga/$(date +%Y%m%d-%H%M%S)"

# Las variables del entorno mandan sobre las de --env-file.
export POSTGRES_DB=streetrepo_load
export DB_HOST_PORT="${LOAD_DB_PORT:-5435}"
export API_PORT="${LOAD_API_PORT:-8002}"
export API_BIND_ADDRESS=127.0.0.1
export LOG_LEVEL=WARNING
export GLOBAL_REQUESTS_PER_IP=1000000
export LOGIN_PER_IP_PER_5_MINUTES=100000
export REPORTS_PER_USER_PER_HOUR=100000
export REPORTS_PER_IP_PER_HOUR=1000000
export MAP_REQUESTS_PER_USER_PER_MINUTE=100000

COMPOSE=(docker compose -p street-repo-load -f "$ROOT/infra/docker-compose.yml" --env-file "$ENV_FILE")
cli() { "${COMPOSE[@]}" exec -T "$@"; }

echo "==> Levantando el stack de carga (API en http://localhost:${API_PORT})"
"${COMPOSE[@]}" up -d --build --wait db api

cleanup() {
  echo "==> Borrando las cuentas de carga y los datos de demostración"
  cli api python -m app.cli loadtest-accounts --remove || true
  cli api python -m app.cli seed-demo --remove || true
  "${COMPOSE[@]}" stop >/dev/null 2>&1 || true
}
trap cleanup EXIT

roads="$("${COMPOSE[@]}" exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "SELECT count(*) FROM via"')"
if [[ "$roads" == "0" ]]; then
  echo "==> Cargando vías y servicios críticos de OSM (solo la primera vez)"
  cli api python -m app.cli osm-import
fi

echo "==> Datos de demostración y cuentas de carga"
cli api python -m app.cli seed-demo --remove >/dev/null
cli api python -m app.cli seed-demo

# Contraseñas aleatorias de esta corrida: no se guardan en ningún archivo.
LOADTEST_PASSWORD="$(openssl rand -hex 16)"
LOADTEST_ADMIN_EMAIL="carga-admin-$(date +%s)@carga.example.com"
LOADTEST_ADMIN_PASSWORD="$(openssl rand -hex 16)"
# `-e VARIABLE` sin valor la toma del entorno: la contraseña no queda en los argumentos del
# proceso (visibles en la lista de procesos).
export LOADTEST_PASSWORD
cli -e LOADTEST_PASSWORD api python -m app.cli loadtest-accounts --count "$ACCOUNTS"
printf '%s\n%s\n' "$LOADTEST_ADMIN_PASSWORD" "$LOADTEST_ADMIN_PASSWORD" |
  cli api python -m app.cli create-admin --name "Funcionario de carga" --email "$LOADTEST_ADMIN_EMAIL" >/dev/null 2>&1
export LOADTEST_PASSWORD LOADTEST_ADMIN_EMAIL LOADTEST_ADMIN_PASSWORD

mkdir -p "$OUT"
echo "==> Locust: ${USERS} usuarios, ${SPAWN_RATE} nuevos por segundo, ${DURATION} (resultados en ${OUT})"
cd "$ROOT/backend"
uv run locust -f loadtests/locustfile.py --headless \
  -u "$USERS" -r "$SPAWN_RATE" -t "$DURATION" \
  --host "http://localhost:${API_PORT}" \
  --csv "$OUT/resultado" --html "$OUT/resultado.html" --only-summary \
  "$@"
