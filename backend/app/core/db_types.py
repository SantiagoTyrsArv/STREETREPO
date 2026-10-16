"""Tipos de columna compartidos por los modelos ORM."""

from enum import Enum

from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import ENUM

# Todo dato geográfico se guarda en WGS 84 (guía 5, diagrama ER).
SRID_WGS84 = 4326


def pg_enum(enum_cls: type[Enum], name: str) -> ENUM:
    """ENUM de PostgreSQL que guarda los *valores* (en español) del Enum de dominio.

    El tipo lo crea la migración; el modelo solo lo referencia.
    """
    return ENUM(
        enum_cls,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        create_type=False,
    )


def point() -> Geometry:
    # spatial_index=False: los índices GiST se declaran explícitamente en cada tabla.
    return Geometry("POINT", srid=SRID_WGS84, spatial_index=False)


def polygon() -> Geometry:
    return Geometry("POLYGON", srid=SRID_WGS84, spatial_index=False)
