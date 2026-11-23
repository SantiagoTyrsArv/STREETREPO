"""Registro de avisos de posible duplicado en PostgreSQL (consultas parametrizadas).

Implementa ``DuplicateWarningRecorder`` del módulo de reportes. No confirma la transacción:
la controla el caso de uso que lo llama.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Session

from app.modules.reports.domain.duplicates import DuplicateCandidate
from app.modules.reports.domain.ports import WarningDecision
from app.modules.validation.domain.warnings import WarningDecision as StoredDecision
from app.shared.domain.geo import GeoPoint

# Se guarda la zona que cubre el punto consultado, no el punto (minimización, guía 7.2).
# id_zona desempata si el punto cae en el borde compartido de dos zonas.
_RECORD = text(
    """
    INSERT INTO aviso_duplicado (id_usuario, id_zona)
    VALUES (
        :user_id,
        (SELECT z.id_zona FROM zona AS z
          WHERE ST_Covers(z.geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
          ORDER BY z.id_zona
          LIMIT 1)
    )
    RETURNING id_aviso
    """
)

# La distancia se mide desde la ubicación exacta del reporte, no desde la pública que vio
# el ciudadano: es un dato solo para el análisis del administrador y así no arrastra el
# error de la cuadrícula. El punto consultado solo se usa aquí y no se guarda.
_CANDIDATES = text(
    """
    INSERT INTO aviso_duplicado_candidato (id_aviso, id_reporte, distancia_m)
    SELECT :warning_id, r.id_reporte,
           round(ST_Distance(
               r.ubicacion::geography,
               ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
           )::numeric, 2)
    FROM reporte AS r
    WHERE r.id_reporte = ANY(:report_ids)
    """
).bindparams(bindparam("report_ids", type_=ARRAY(UUID(as_uuid=True))))

# Solo un aviso del mismo usuario y aún pendiente; para «confirmo», el reporte confirmado
# debe ser uno de los candidatos que se le ofrecieron.
_RESOLVE = text(
    """
    UPDATE aviso_duplicado AS a
       SET decision = CAST(:decision AS decision_aviso),
           id_reporte_resultante = :report_id
     WHERE a.id_aviso = :warning_id
       AND a.id_usuario = :user_id
       AND a.decision = CAST(:pending AS decision_aviso)
       AND (
           CAST(:decision AS decision_aviso) <> CAST(:confirmed AS decision_aviso)
           OR EXISTS (
               SELECT 1 FROM aviso_duplicado_candidato AS c
                WHERE c.id_aviso = a.id_aviso AND c.id_reporte = :report_id
           )
       )
    """
)


class SqlDuplicateWarningRecorder:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self, user_id: uuid.UUID, location: GeoPoint, candidates: Sequence[DuplicateCandidate]
    ) -> uuid.UUID:
        point = {"lon": location.longitude, "lat": location.latitude}
        warning_id: uuid.UUID = self._session.execute(
            _RECORD, {"user_id": user_id, **point}
        ).scalar_one()
        self._session.execute(
            _CANDIDATES,
            {"warning_id": warning_id, "report_ids": [c.id for c in candidates], **point},
        )
        return warning_id

    def resolve(
        self,
        warning_id: uuid.UUID,
        user_id: uuid.UUID,
        decision: WarningDecision,
        report_id: uuid.UUID,
    ) -> bool:
        result = self._session.execute(
            _RESOLVE,
            {
                "warning_id": warning_id,
                "user_id": user_id,
                "decision": StoredDecision(decision).value,
                "report_id": report_id,
                "pending": StoredDecision.PENDING.value,
                "confirmed": StoredDecision.CONFIRMED.value,
            },
        )
        return bool(getattr(result, "rowcount", 0))
