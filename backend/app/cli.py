"""Comandos de operación: ``python -m app.cli <comando>``.

osm-import [--bbox sur,oeste,norte,este]   Carga vías y servicios críticos de OSM.
create-admin --name NOMBRE --email CORREO  Crea un administrador (pide la contraseña sin eco).
"""

import argparse
import getpass
import json
import sys
from collections.abc import Sequence

from app.core.config import get_settings
from app.core.database import create_session
from app.core.logging import configure_logging
from app.modules.admin.application.import_osm_data import ImportOsmData, OsmSourceError
from app.modules.admin.infrastructure.overpass import create_overpass_client
from app.modules.auth.application.create_admin import CreateAdmin
from app.modules.auth.domain.passwords import WeakPasswordError
from app.modules.auth.infrastructure.passwords import Argon2PasswordHasher
from app.modules.critical_services.infrastructure.repository import SqlCriticalServiceRepository
from app.modules.roads.infrastructure.repository import SqlRoadRepository
from app.modules.users.domain.ports import EmailAlreadyRegisteredError
from app.modules.users.infrastructure.repository import SqlUserRepository
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


def _create_admin(name: str, email: str) -> int:
    # La contraseña nunca va en los argumentos: quedaría en el historial de la terminal.
    password = getpass.getpass("Contraseña del administrador: ")
    if password != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 2
    with create_session() as session:
        try:
            user = CreateAdmin(SqlUserRepository(session), Argon2PasswordHasher(), session).execute(
                name, email, password
            )
        except WeakPasswordError as exc:
            print(f"{exc}.", file=sys.stderr)
            return 2
        except EmailAlreadyRegisteredError:
            print("Ya existe una cuenta con ese correo.", file=sys.stderr)
            return 1
    print(json.dumps({"administrador": str(user.id)}))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    osm = commands.add_parser("osm-import", help="Cargar vías y servicios críticos de OSM")
    osm.add_argument("--bbox", help="Área sur,oeste,norte,este (por defecto OSM_BBOX)")
    admin = commands.add_parser("create-admin", help="Crear una cuenta de administrador")
    admin.add_argument("--name", required=True, help="Nombre del administrador")
    admin.add_argument("--email", required=True, help="Correo con el que iniciará sesión")

    args = parser.parse_args(argv)
    configure_logging(get_settings().log_level)
    if args.command == "osm-import":
        return _osm_import(args.bbox)
    if args.command == "create-admin":
        return _create_admin(args.name, args.email)
    return 2  # pragma: no cover - argparse ya valida el comando


if __name__ == "__main__":
    sys.exit(main())
