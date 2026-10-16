import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WeightConfigModel(Base):
    """Versión de pesos del modelo U. Las filas no se editan: cada cambio crea una versión."""

    __tablename__ = "configuracion_pesos"
    __table_args__ = (
        CheckConstraint(
            "w_severidad BETWEEN 0 AND 1 AND w_flujo BETWEEN 0 AND 1 "
            "AND w_proximidad BETWEEN 0 AND 1",
            name="ck_configuracion_pesos_rango",
        ),
        # Suma exacta de 1,00; NUMERIC evita errores de coma flotante (guía 2.2).
        CheckConstraint(
            "w_severidad + w_flujo + w_proximidad = 1.00", name="ck_configuracion_pesos_suma"
        ),
        # Solo una configuración vigente a la vez.
        Index(
            "uq_configuracion_pesos_vigente",
            "vigente",
            unique=True,
            postgresql_where=text("vigente"),
        ),
    )

    id: Mapped[int] = mapped_column("id_config", Integer, primary_key=True)
    # NULL = configuración inicial cargada por el sistema.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        "id_usuario", ForeignKey("usuario.id_usuario", ondelete="SET NULL")
    )
    severity_weight: Mapped[Decimal] = mapped_column("w_severidad", Numeric(3, 2))
    flow_weight: Mapped[Decimal] = mapped_column("w_flujo", Numeric(3, 2))
    proximity_weight: Mapped[Decimal] = mapped_column("w_proximidad", Numeric(3, 2))
    is_current: Mapped[bool] = mapped_column("vigente", Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        "fecha_creacion", DateTime(timezone=True), server_default=func.now()
    )


class PriorityEvaluationModel(Base):
    """Cálculo reproducible de U: guarda S, F, P, la versión de pesos y la fecha (guía 4.5)."""

    __tablename__ = "evaluacion_prioridad"
    __table_args__ = (
        CheckConstraint(
            "s_severidad BETWEEN 0 AND 10 AND f_flujo BETWEEN 0 AND 10 "
            "AND p_proximidad BETWEEN 0 AND 10 AND u_utilidad BETWEEN 0 AND 10",
            name="ck_evaluacion_prioridad_factores_rango",
        ),
        CheckConstraint(
            "distancia_servicio_m >= 0", name="ck_evaluacion_prioridad_distancia_positiva"
        ),
        Index("ix_evaluacion_prioridad_reporte_fecha", "id_reporte", "fecha_calculo"),
        Index("ix_evaluacion_prioridad_id_config", "id_config"),
    )

    id: Mapped[int] = mapped_column("id_evaluacion", BigInteger, primary_key=True)
    report_id: Mapped[uuid.UUID] = mapped_column(
        "id_reporte", ForeignKey("reporte.id_reporte", ondelete="CASCADE")
    )
    config_id: Mapped[int] = mapped_column(
        "id_config", Integer, ForeignKey("configuracion_pesos.id_config", ondelete="RESTRICT")
    )
    # NULL = ningún servicio crítico a menos de 500 m (P = 0).
    service_id: Mapped[int | None] = mapped_column(
        "id_servicio", Integer, ForeignKey("servicio_critico.id_servicio", ondelete="SET NULL")
    )
    service_distance_m: Mapped[Decimal | None] = mapped_column(
        "distancia_servicio_m", Numeric(8, 2)
    )
    severity_score: Mapped[Decimal] = mapped_column("s_severidad", Numeric(4, 2))
    flow_score: Mapped[Decimal] = mapped_column("f_flujo", Numeric(4, 2))
    proximity_score: Mapped[Decimal] = mapped_column("p_proximidad", Numeric(4, 2))
    urgency_score: Mapped[Decimal] = mapped_column("u_utilidad", Numeric(4, 2))
    calculated_at: Mapped[datetime] = mapped_column(
        "fecha_calculo", DateTime(timezone=True), server_default=func.now()
    )
