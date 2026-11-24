# Datos de OSM para las pruebas de punta a punta

`osm-pasto.sql.gz` es un volcado (`pg_dump --data-only`) de las tablas `via` y `servicio_critico`
con las vías y los servicios críticos de Pasto que carga `python -m app.cli osm-import` en el área
`OSM_BBOX` (1.16,-77.33,1.25,-77.23). Lo usan las pruebas de punta a punta del panel en GitHub
Actions (`.github/workflows/e2e.yml`) para no depender de Overpass, que no responde desde los
servidores de GitHub y no debe consultarse en cada ejecución (guía 3.1; fila 152 de la bitácora).

**Datos © colaboradores de OpenStreetMap**, disponibles bajo la
[Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). Este volcado es una
base de datos derivada y se distribuye bajo la misma licencia. Más información:
<https://www.openstreetmap.org/copyright>.

## Regenerarlo

Cuando cambie el esquema de `via` o `servicio_critico` (una migración) o se quieran datos más
recientes, con Docker en marcha y Git Bash:

```bash
docker compose -p street-repo-e2e -f infra/docker-compose.yml --env-file .env down -v
E2E_OSM_DUMP="$PWD/infra/e2e/osm-pasto.sql.gz" infra/scripts/e2e-panel.sh
```

Con la base de E2E vacía y el archivo borrado, el script importa de OSM y vuelve a escribir el
volcado. Si el archivo existe, lo carga en vez de importar.
