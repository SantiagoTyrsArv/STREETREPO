"""Comandos de operación: ``python -m app.cli <comando>``.

osm-import [--bbox sur,oeste,norte,este]   Carga vías y servicios críticos de OSM.
"""

import argparse
import json
import sys
from collections.abc import Sequence

from app.core.config import get_settings
from app.core.database import create_session
from app.core.logging import configure_logging
from app.modules.admin.application.import_osm_data import ImportOsmData, OsmSourceError
from app.modules.admin.infrastructure.overpass import create_overpass_client
from app.modules.critical_services.infrastructure.repository import SqlCriticalServiceRepository
from app.modules.roads.infrastructure.repository import SqlRoadRepository
from app.shared.domain.geo import BoundingBox, InvalidGeometryError


def _osm_import(bbox: str | None) -> int:
    settings = get_settings()
    try:
        area = BoundingBox.parse(bbox or settings.osm_bbox)
    except InvalidGeometryError as exc:
        print(f"Área inválida: {exc}", file=sys.stderr)
        return 2

    source = create_overpass_client(
        settings.overpass_url, settings.osm_user_agent, settings.osm_timeout_s
    )
    with create_session() as session:
        try:
            result = ImportOsmData(
                source=source,
                roads=SqlRoadRepository(session),
                critical_services=SqlCriticalServiceRepository(session),
                transaction=session,
            ).execute(area)
        except OsmSourceError as exc:
            print(f"No se pudo descargar OSM: {exc}", file=sys.stderr)
            return 1

    print(json.dumps({"vias": result.roads, "servicios_criticos": result.critical_services}))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    osm = commands.add_parser("osm-import", help="Cargar vías y servicios críticos de OSM")
    osm.add_argument("--bbox", help="Área sur,oeste,norte,este (por defecto OSM_BBOX)")

    args = parser.parse_args(argv)
    configure_logging(get_settings().log_level)
    if args.command == "osm-import":
        return _osm_import(args.bbox)
    return 2  # pragma: no cover - argparse ya valida el comando


if __name__ == "__main__":
    sys.exit(main())
