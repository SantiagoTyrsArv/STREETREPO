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

psql_e2e() {
  "${COMPOSE[@]}" exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At'
}

# Las rondas de ejecuciones anteriores retienen sus reportes (RESTRICT): se borran antes de
# recargar los datos de demostración. Solo en esta base aparte.
echo "==> Borrando las rondas de evaluación de ejecuciones anteriores"
psql_e2e <<<"DELETE FROM ronda_evaluacion;" >/dev/null

echo "==> Datos de demostración recién cargados"
cli seed-demo --remove
cli seed-demo

# Dos zonas de prueba (objetivo 4) que parten por la mitad, de oeste a este, los reportes
# activos con urgencia: cada una queda con más de los 5 que exige una ronda. Son rectángulos
# de prueba, no las zonas del estudio.
echo "==> Zonas de prueba del objetivo 4"
psql_e2e >"$ROOT/.e2e-zonas.geojson" <<'SQL'
WITH pts AS (
  SELECT ST_X(ubicacion) AS x, ST_Y(ubicacion) AS y FROM reporte
  WHERE puntaje_prioridad IS NOT NULL AND estado <> 'reparado'
),
ordered AS (SELECT x, row_number() OVER (ORDER BY x) AS rn, count(*) OVER () AS n FROM pts),
cut AS (
  SELECT (max(x) FILTER (WHERE rn = n / 2) + min(x) FILTER (WHERE rn = n / 2 + 1)) / 2 AS cx
  FROM ordered
),
box AS (
  SELECT min(x) - 0.002 AS x0, max(x) + 0.002 AS x1, min(y) - 0.002 AS y0, max(y) + 0.002 AS y1
  FROM pts
)
SELECT json_build_object('type', 'FeatureCollection', 'features', json_build_array(
  json_build_object('type', 'Feature',
    'properties', json_build_object('name', 'E2E Oeste', 'concentration', 'alta'),
    'geometry', ST_AsGeoJSON(ST_MakeEnvelope(x0, y0, cx, y1, 4326))::json),
  json_build_object('type', 'Feature',
    'properties', json_build_object('name', 'E2E Este', 'concentration', 'baja'),
    'geometry', ST_AsGeoJSON(ST_MakeEnvelope(cx, y0, x1, y1, 4326))::json)))
FROM box, cut;
SQL
"${COMPOSE[@]}" exec -T api sh -c 'cat > /tmp/e2e-zonas.geojson' <"$ROOT/.e2e-zonas.geojson"
rm -f "$ROOT/.e2e-zonas.geojson"
# En Git Bash (Windows) MSYS convertiría la ruta del contenedor en una de Windows.
MSYS2_ARG_CONV_EXCL="/tmp/" cli zones-import /tmp/e2e-zonas.geojson

# Cuenta nueva en cada ejecución, con contraseña aleatoria que no se guarda en ningún archivo.
E2E_ADMIN_EMAIL="e2e-$(date +%s)@example.com"
E2E_ADMIN_PASSWORD="$(openssl rand -hex 16)"
printf '%s\n%s\n' "$E2E_ADMIN_PASSWORD" "$E2E_ADMIN_PASSWORD" |
  cli create-admin --name "Funcionaria E2E" --email "$E2E_ADMIN_EMAIL" >/dev/null 2>&1
export E2E_ADMIN_EMAIL E2E_ADMIN_PASSWORD

# Evaluador del panel de referencia (objetivo 4), con las mismas precauciones.
E2E_EVALUATOR_EMAIL="e2e-eval-$(date +%s)@example.com"
E2E_EVALUATOR_PASSWORD="$(openssl rand -hex 16)"
printf '%s\n%s\n' "$E2E_EVALUATOR_PASSWORD" "$E2E_EVALUATOR_PASSWORD" |
  cli create-evaluator --name "Evaluadora E2E" --email "$E2E_EVALUATOR_EMAIL" >/dev/null 2>&1
export E2E_EVALUATOR_EMAIL E2E_EVALUATOR_PASSWORD
export E2E_BASE_URL="http://localhost:${ADMIN_WEB_PORT}"

cd "$ROOT/admin-web"
npx playwright test "$@"
