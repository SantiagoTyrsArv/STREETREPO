"""Parámetros geográficos del modelo (guía 2.3).

Son reglas de la tesis, no configuración de despliegue: cambiarlas requiere
aprobación del responsable (guía 16). Se usan siempre por nombre, nunca como
números dentro de las consultas.
"""

from typing import Final

# Reportes activos dentro de este radio se ofrecen como posible duplicado (guía 2.5).
DEDUPLICATION_RADIUS_M: Final = 25.0

# Distancia máxima para asociar un reporte a una vía OSM; si no hay vía, F = 2
# y el reporte se marca "Revisar vía" (guía 2.2).
ROAD_MATCHING_RADIUS_M: Final = 30.0

# A partir de esta distancia a un servicio crítico la proximidad P vale 0 (guía 2.2).
PROXIMITY_MAX_RADIUS_M: Final = 500.0
