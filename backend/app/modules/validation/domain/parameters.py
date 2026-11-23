"""Parámetros del estudio de comparación con el panel de referencia (objetivo 4)."""

from typing import Final

# Mínimo de reportes activos para que una zona sea elegible.
MIN_REPORTS_PER_ZONE: Final = 5
# Máximo de zonas por ronda de evaluación.
MAX_ZONES: Final = 3
# Nivel de significancia de las pruebas estadísticas entre zonas.
SIGNIFICANCE_ALPHA: Final = 0.05
