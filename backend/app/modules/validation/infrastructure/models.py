import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Los tipos los crea la migración 0009; los modelos solo los referencian. Se mapean como texto
# (los valores del piloto no se usan fuera de esta infraestructura hasta la tarea 2).
ROUND_STATE_TYPE = ENUM("abierta", "cerrada", name="estado_ronda", create_type=False)
WARNING_DECISION_TYPE = ENUM(
    "pendiente", "confirmo", "creo_igual", name="decision_aviso", create_type=False
)


class EvaluationRoundModel(Base):
    """Ronda del piloto: muestra congelada de reportes que los evaluadores ordenan a ciegas."""

    __tablename__ = "ronda_evaluacion"
    __table_args__ = (
        CheckConstraint("tamano_muestra > 0", name="ck_ronda_evaluacion_tamano_positivo"),
        # Una sola ronda abierta a la vez.
        Index(
            "uq_ronda_abierta",
            "estado",
            unique=True,
            postgresql_where=text("estado = 'abierta'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        "id_ronda", primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column("nombre", String(100))
    state: Mapped[str] = mapped_column("estado", ROUND_STATE_TYPE, server_default="abierta")
    sample_size: Mapped[int] = mapped_column("tamano_muestra", SmallInteger)
    # Semilla del sorteo de la muestra: permite reproducirla.
    seed: Mapped[int] = mapped_column("semilla", BigInteger)
    config_id: Mapped[int] = mapped_column(
        "id_config", ForeignKey("configuracion_pesos.id_config", ondelete="RESTRICT")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        "id_usuario", ForeignKey("usuario.id_usuario", ondelete="RESTRICT")
    )
    opened_at: Mapped[datetime] = mapped_column(
        "fecha_apertura", DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column("fecha_cierre", DateTime(timezone=True))


class RoundReportModel(Base):
    """Reporte de la muestra con su zona, el puntaje U y la posición que le dio el motor."""

    __tablename__ = "ronda_reporte"
    __table_args__ = (
        UniqueConstraint("id_ronda", "id_zona", "orden_motor", name="uq_ronda_reporte_zona_orden"),
    )

    round_id: Mapped[uuid.UUID] = mapped_column(
        "id_ronda", ForeignKey("ronda_evaluacion.id_ronda", ondelete="CASCADE"), primary_key=True
    )
    # RESTRICT: un reporte que está en una ronda no se borra (la evidencia debe poder reproducirse).
    report_id: Mapped[uuid.UUID] = mapped_column(
        "id_reporte", ForeignKey("reporte.id_reporte", ondelete="RESTRICT"), primary_key=True
    )
    zone_id: Mapped[int] = mapped_column("id_zona", ForeignKey("zona.id_zona", ondelete="RESTRICT"))
    priority_score: Mapped[Decimal] = mapped_column("puntaje_u", Numeric(4, 2))
    engine_order: Mapped[int] = mapped_column("orden_motor", SmallInteger)


class EvaluatorOrderModel(Base):
    """Posición que un evaluador le dio a un reporte de la muestra."""

    __tablename__ = "orden_evaluador"
    # La unicidad (ronda, usuario, zona, posición) no cabe aquí porque la zona vive en
    # ronda_reporte: la garantiza la aplicación.
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_ronda", "id_reporte"],
            ["ronda_reporte.id_ronda", "ronda_reporte.id_reporte"],
            ondelete="CASCADE",
        ),
    )

    round_id: Mapped[uuid.UUID] = mapped_column("id_ronda", primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "id_usuario", ForeignKey("usuario.id_usuario", ondelete="RESTRICT"), primary_key=True
    )
    report_id: Mapped[uuid.UUID] = mapped_column("id_reporte", primary_key=True)
    position: Mapped[int] = mapped_column("posicion", SmallInteger)
    submitted_at: Mapped[datetime] = mapped_column(
        "fecha_envio", DateTime(timezone=True), server_default=func.now()
    )


class DuplicateWarningModel(Base):
    """Registro de cada aviso de posible duplicado mostrado y lo que decidió el ciudadano."""

    __tablename__ = "aviso_duplicado"

    id: Mapped[uuid.UUID] = mapped_column(
        "id_aviso", primary_key=True, server_default=text("gen_random_uuid()")
    )
    # RESTRICT: las cuentas se anonimizan, no se borran (decisión 23a); como las confirmaciones.
    user_id: Mapped[uuid.UUID] = mapped_column(
        "id_usuario", ForeignKey("usuario.id_usuario", ondelete="RESTRICT")
    )
    zone_id: Mapped[int | None] = mapped_column(
        "id_zona", Integer, ForeignKey("zona.id_zona", ondelete="SET NULL")
    )
    shown_at: Mapped[datetime] = mapped_column(
        "fecha", DateTime(timezone=True), server_default=func.now()
    )
    decision: Mapped[str] = mapped_column(
        "decision", WARNING_DECISION_TYPE, server_default="pendiente"
    )
    resulting_report_id: Mapped[uuid.UUID | None] = mapped_column(
        "id_reporte_resultante", ForeignKey("reporte.id_reporte", ondelete="SET NULL")
    )


class DuplicateWarningCandidateModel(Base):
    """Reporte cercano que el aviso ofreció confirmar, con su distancia en metros."""

    __tablename__ = "aviso_duplicado_candidato"

    warning_id: Mapped[uuid.UUID] = mapped_column(
        "id_aviso", ForeignKey("aviso_duplicado.id_aviso", ondelete="CASCADE"), primary_key=True
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        "id_reporte", ForeignKey("reporte.id_reporte", ondelete="CASCADE"), primary_key=True
    )
    distance_m: Mapped[Decimal] = mapped_column("distancia_m", Numeric(6, 2))
