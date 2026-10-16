import uuid
from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_types import pg_enum, point
from app.modules.reports.domain.status import ReportStatus

REPORT_STATUS_TYPE = "estado_reporte"


class ReportModel(Base):
    __tablename__ = "reporte"
    __table_args__ = (
        CheckConstraint("severidad BETWEEN 1 AND 3", name="ck_reporte_severidad_valida"),
        CheckConstraint(
            "puntaje_prioridad BETWEEN 0 AND 10", name="ck_reporte_puntaje_prioridad_rango"
        ),
        Index("ix_reporte_ubicacion", "ubicacion", postgresql_using="gist"),
        # Deduplicación a 25 m sobre geography (ADR 0003).
        Index("ix_reporte_ubicacion_geog", text("(ubicacion::geography)"), postgresql_using="gist"),
        # Ranking (guía 11): por estado y puntaje.
        Index("ix_reporte_estado_puntaje", "estado", text("puntaje_prioridad DESC")),
        Index("ix_reporte_fecha_creacion", "fecha_creacion"),
        Index("ix_reporte_id_usuario", "id_usuario"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        "id_reporte", primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        "id_usuario", ForeignKey("usuario.id_usuario", ondelete="RESTRICT")
    )
    zone_id: Mapped[int | None] = mapped_column(
        "id_zona", Integer, ForeignKey("zona.id_zona", ondelete="SET NULL")
    )
    # NULL = sin vía asociada a 30 m: F = 2 y marca "Revisar vía" (guía 2.2).
    road_id: Mapped[int | None] = mapped_column(
        "id_via", Integer, ForeignKey("via.id_via", ondelete="SET NULL")
    )
    location: Mapped[Geometry] = mapped_column("ubicacion", point())
    # Nominatim puede no devolver dirección.
    address: Mapped[str | None] = mapped_column("direccion", String(255))
    severity: Mapped[int] = mapped_column("severidad", SmallInteger)
    description: Mapped[str | None] = mapped_column("descripcion", Text)
    status: Mapped[ReportStatus] = mapped_column(
        "estado",
        pg_enum(ReportStatus, REPORT_STATUS_TYPE),
        server_default=ReportStatus.REGISTERED.value,
    )
    # Copia de la U vigente para ordenar el ranking sin JOIN (guía 11).
    priority_score: Mapped[Decimal | None] = mapped_column("puntaje_prioridad", Numeric(4, 2))
    created_at: Mapped[datetime] = mapped_column(
        "fecha_creacion", DateTime(timezone=True), server_default=func.now()
    )


class EvidenceModel(Base):
    __tablename__ = "evidencia"
    __table_args__ = (
        CheckConstraint("tamano_bytes > 0", name="ck_evidencia_tamano_positivo"),
        Index("ix_evidencia_id_reporte", "id_reporte"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        "id_evidencia", primary_key=True, server_default=text("gen_random_uuid()")
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        "id_reporte", ForeignKey("reporte.id_reporte", ondelete="CASCADE")
    )
    photo_url: Mapped[str] = mapped_column("url_foto", String(255))
    file_format: Mapped[str] = mapped_column("formato", String(10))
    size_bytes: Mapped[int] = mapped_column("tamano_bytes", Integer)
    uploaded_at: Mapped[datetime] = mapped_column(
        "fecha_subida", DateTime(timezone=True), server_default=func.now()
    )


class StatusHistoryModel(Base):
    __tablename__ = "historial_estado"
    __table_args__ = (Index("ix_historial_estado_reporte_fecha", "id_reporte", "fecha_cambio"),)

    id: Mapped[int] = mapped_column("id_historial", BigInteger, primary_key=True)
    report_id: Mapped[uuid.UUID] = mapped_column(
        "id_reporte", ForeignKey("reporte.id_reporte", ondelete="CASCADE")
    )
    # NULL = transición automática del motor de priorización (Registrado -> Evaluado).
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        "id_usuario", ForeignKey("usuario.id_usuario", ondelete="SET NULL")
    )
    # NULL solo en el registro inicial del reporte.
    previous_status: Mapped[ReportStatus | None] = mapped_column(
        "estado_anterior", pg_enum(ReportStatus, REPORT_STATUS_TYPE)
    )
    new_status: Mapped[ReportStatus] = mapped_column(
        "estado_nuevo", pg_enum(ReportStatus, REPORT_STATUS_TYPE)
    )
    note: Mapped[str | None] = mapped_column("observacion", Text)
    changed_at: Mapped[datetime] = mapped_column(
        "fecha_cambio", DateTime(timezone=True), server_default=func.now()
    )
