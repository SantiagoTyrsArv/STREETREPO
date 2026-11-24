"""Comandos de operación: ``python -m app.cli <comando>``.

osm-import [--bbox sur,oeste,norte,este]   Carga vías y servicios críticos de OSM.
create-admin --name NOMBRE --email CORREO  Crea un administrador (pide la contraseña sin eco).
create-evaluator --name NOMBRE --email CORREO  Crea un evaluador (igual que create-admin).
purge-orphan-photos                       Borra las fotos que ninguna evidencia referencia.
seed-demo [--remove]                      Carga (o borra) los datos de demostración del panel.
zones-import RUTA                         Carga las zonas de validación desde un GeoJSON.
"""

import argparse
import getpass
import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import create_session
from app.core.logging import configure_logging
from app.modules.admin.application.demo_seed import SeedDemo
from app.modules.admin.application.import_osm_data import ImportOsmData, OsmSourceError
from app.modules.admin.application.loadtest_accounts import LoadTestAccounts
from app.modules.admin.domain.demo import NotEnoughOsmDataError
from app.modules.admin.domain.loadtest import LOADTEST_EMAIL_DOMAIN
from app.modules.admin.infrastructure.demo_data import SqlDemoData, load_demo_photos
from app.modules.admin.infrastructure.demo_points import PostgisDemoPointPicker
from app.modules.admin.infrastructure.overpass import create_overpass_client
from app.modules.auth.application.create_staff import CreateStaffAccount
from app.modules.auth.domain.passwords import WeakPasswordError
from app.modules.auth.infrastructure.passwords import Argon2PasswordHasher
from app.modules.critical_services.infrastructure.repository import SqlCriticalServiceRepository
from app.modules.priority.presentation.dependencies import build_report_evaluator
from app.modules.reports.application.photo_cleanup import PhotoFileCleanup, PurgeOrphanPhotos
from app.modules.reports.infrastructure.evidence import SqlEvidenceKeys
from app.modules.reports.infrastructure.local_photo_storage import LocalPhotoStorage
from app.modules.reports.infrastructure.pillow_photos import PillowPhotoProcessor
from app.modules.reports.infrastructure.repository import SqlReportRepository
from app.modules.reports.infrastructure.status_history import SqlStatusHistoryRecorder
from app.modules.roads.infrastructure.repository import SqlRoadRepository
from app.modules.users.domain.ports import EmailAlreadyRegisteredError
from app.modules.users.domain.role import UserRole
from app.modules.users.infrastructure.repository import SqlUserRepository
from app.modules.validation.application.import_zones import ImportZones
from app.modules.validation.domain.zones import InvalidZonesError
from app.modules.validation.infrastructure.zone_repository import SqlZoneRepository
from app.shared.application.clock import SystemClock
from app.shared.domain.geo import BoundingBox, InvalidGeometryError

# Contraseña común de las cuentas de carga (fase 8): solo por variable de entorno.
LOADTEST_PASSWORD_ENV = "LOADTEST_PASSWORD"  # noqa: S105 - nombre de la variable y no su valor


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


def _create_staff(name: str, email: str, role: UserRole, label: str, output_key: str) -> int:
    # La contraseña nunca va en los argumentos: quedaría en el historial de la terminal.
    password = getpass.getpass(f"Contraseña del {label}: ")
    if password != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 2
    with create_session() as session:
        try:
            user_id = CreateStaffAccount(
                SqlUserRepository(session), Argon2PasswordHasher(), session
            ).execute(name, email, password, role)
        except WeakPasswordError as exc:
            print(f"{exc}.", file=sys.stderr)
            return 2
        except EmailAlreadyRegisteredError:
            print("Ya existe una cuenta con ese correo.", file=sys.stderr)
            return 1
    print(json.dumps({output_key: str(user_id)}))
    return 0


def _create_admin(name: str, email: str) -> int:
    return _create_staff(name, email, UserRole.ADMIN, "administrador", "administrador")


def _create_evaluator(name: str, email: str) -> int:
    return _create_staff(name, email, UserRole.EVALUATOR, "evaluador", "evaluador")


def _purge_orphan_photos() -> int:
    storage = LocalPhotoStorage(get_settings().photo_storage_dir)
    with create_session() as session:
        deleted = PurgeOrphanPhotos(
            inventory=storage,
            evidence=SqlEvidenceKeys(session),
            cleanup=PhotoFileCleanup(storage),
            clock=SystemClock(),
        ).execute()
    print(json.dumps({"fotos_borradas": deleted}))
    return 0


def _build_seed_demo(session: Session, settings: Settings) -> SeedDemo:
    storage = LocalPhotoStorage(settings.photo_storage_dir)
    return SeedDemo(
        users=SqlUserRepository(session),
        points=PostgisDemoPointPicker(session),
        reports=SqlReportRepository(session),
        statuses=SqlStatusHistoryRecorder(session),
        evaluator=build_report_evaluator(session),
        photo_processor=PillowPhotoProcessor(),
        photo_storage=storage,
        photo_files=PhotoFileCleanup(storage),
        demo_data=SqlDemoData(session),
        photos=load_demo_photos(),
        service_area=settings.report_area,
        transaction=session,
    )


def _seed_demo(*, remove: bool) -> int:
    settings = get_settings()
    with create_session() as session:
        seed = _build_seed_demo(session, settings)
        if remove:
            print(f"Datos de demostración: {seed.remove()} reportes borrados.")
            return 0
        try:
            created = seed.execute()
        except NotEnoughOsmDataError as exc:
            print(f"{exc}", file=sys.stderr)
            return 1
    if created == 0:
        print(
            "Ya hay datos de demostración; no se creó nada. "
            "Para rehacerlos, bórralos antes con: seed-demo --remove"
        )
    else:
        print(f"Datos de demostración: {created} reportes creados. No son datos de campo.")
    return 0


def _build_loadtest_accounts(session: Session, settings: Settings) -> LoadTestAccounts:
    storage = LocalPhotoStorage(settings.photo_storage_dir)
    return LoadTestAccounts(
        users=SqlUserRepository(session),
        hasher=Argon2PasswordHasher(),
        data=SqlDemoData(session, email_domain=LOADTEST_EMAIL_DOMAIN),
        photo_files=PhotoFileCleanup(storage),
        transaction=session,
        clock=SystemClock(),
        policy_version=settings.privacy_policy_version,
    )


def _loadtest_accounts(*, count: int | None, remove: bool) -> int:
    """Cuentas de la prueba de carga (fase 8). La contraseña llega solo por variable de
    entorno, nunca por argumento: quedaría en el historial de la terminal."""
    settings = get_settings()
    with create_session() as session:
        accounts = _build_loadtest_accounts(session, settings)
        if remove:
            print(f"Cuentas de carga: {accounts.remove()} reportes borrados.")
            return 0
        password = os.environ.get(LOADTEST_PASSWORD_ENV, "")
        if not password:
            print(
                f"Define {LOADTEST_PASSWORD_ENV} con la contraseña de las cuentas.", file=sys.stderr
            )
            return 1
        if count is None:
            print("Indica cuántas cuentas con --count N.", file=sys.stderr)
            return 1
        emails = accounts.create(count, password)
    print(f"Cuentas de carga listas: {len(emails)} ({emails[0]} … {emails[-1]}).")
    return 0


def _build_import_zones(session: Session) -> ImportZones:
    return ImportZones(SqlZoneRepository(session), session)


def _zones_import(path: Path) -> int:
    try:
        geojson = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"No se pudo leer el archivo de zonas: {exc.strerror or exc}", file=sys.stderr)
        return 1
    except ValueError:
        print("El archivo de zonas no es un JSON válido.", file=sys.stderr)
        return 1
    with create_session() as session:
        try:
            result = _build_import_zones(session).execute(geojson)
        except InvalidZonesError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    print(f"Zonas cargadas: {result.zones} · reportes asignados: {result.reports_assigned}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    osm = commands.add_parser("osm-import", help="Cargar vías y servicios críticos de OSM")
    osm.add_argument("--bbox", help="Área sur,oeste,norte,este (por defecto OSM_BBOX)")
    admin = commands.add_parser("create-admin", help="Crear una cuenta de administrador")
    admin.add_argument("--name", required=True, help="Nombre del administrador")
    admin.add_argument("--email", required=True, help="Correo con el que iniciará sesión")
    evaluator = commands.add_parser("create-evaluator", help="Crear una cuenta de evaluador")
    evaluator.add_argument("--name", required=True, help="Nombre del evaluador")
    evaluator.add_argument("--email", required=True, help="Correo con el que iniciará sesión")
    commands.add_parser("purge-orphan-photos", help="Borrar las fotos huérfanas de más de una hora")
    demo = commands.add_parser("seed-demo", help="Cargar los datos de demostración del panel")
    demo.add_argument("--remove", action="store_true", help="Borrar los datos de demostración")

    load = commands.add_parser(
        "loadtest-accounts",
        help="Crear o borrar las cuentas de la prueba de carga (@carga.example.com)",
        description=(
            f"Crea las cuentas carga-001…carga-N con la contraseña de {LOADTEST_PASSWORD_ENV}, "
            "o las borra con sus reportes y fotos. Solo para el entorno de carga local."
        ),
    )
    load_action = load.add_mutually_exclusive_group(required=True)
    load_action.add_argument("--count", type=int, help="Cuántas cuentas crear")
    load_action.add_argument("--remove", action="store_true", help="Borrar las cuentas de carga")

    zones = commands.add_parser(
        "zones-import",
        help="Cargar las zonas de validación desde un GeoJSON",
        description=(
            "Carga zonas (Polygon con name y concentration alta|baja). Las zonas con el mismo "
            "nombre se actualizan; las que están en la base y no vienen en el archivo no se "
            "tocan. Luego recalcula la zona de todos los reportes."
        ),
    )
    zones.add_argument("path", metavar="RUTA", type=Path, help="Archivo GeoJSON de zonas")

    args = parser.parse_args(argv)
    configure_logging(get_settings().log_level)
    handlers: dict[str, Callable[[], int]] = {
        "osm-import": lambda: _osm_import(args.bbox),
        "create-admin": lambda: _create_admin(args.name, args.email),
        "create-evaluator": lambda: _create_evaluator(args.name, args.email),
        "purge-orphan-photos": _purge_orphan_photos,
        "seed-demo": lambda: _seed_demo(remove=args.remove),
        "zones-import": lambda: _zones_import(args.path),
        "loadtest-accounts": lambda: _loadtest_accounts(count=args.count, remove=args.remove),
    }
    return handlers[args.command]()


if __name__ == "__main__":
    sys.exit(main())
