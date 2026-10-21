"""La API en marcha conoce todas las tablas a las que apuntan sus claves foráneas.

Se prueba en un proceso nuevo: en pytest otras pruebas ya importan `app.models` y ocultarían
el fallo (al crear un reporte, `evaluacion_prioridad` no encontraba `servicio_critico`).
"""

import subprocess
import sys

_CHECK = """
import app.main
from app.core.database import Base

for table in Base.metadata.tables.values():
    for foreign_key in table.foreign_keys:
        foreign_key.column  # NoReferencedTableError si la tabla destino no está registrada
"""


def test_importing_the_app_registers_every_referenced_table() -> None:
    result = subprocess.run(  # noqa: S603  - comando fijo con el intérprete actual
        [sys.executable, "-c", _CHECK], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
