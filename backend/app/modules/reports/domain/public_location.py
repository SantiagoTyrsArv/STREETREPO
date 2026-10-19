"""Ubicación que se muestra de los reportes ajenos (guía 7.2, propuestas 40 y 43).

Los reportes de otros ciudadanos se muestran con las coordenadas redondeadas a
``PUBLIC_COORDINATE_DECIMALS`` decimales (unos 11 m en Pasto), y cualquier distancia que
se entregue se calcula desde esas coordenadas, nunca desde las exactas: con tres
distancias exactas desde puntos distintos se podría calcular la ubicación real.
El servidor sigue usando la ubicación exacta para deduplicar y priorizar.
"""

from typing import Final

PUBLIC_COORDINATE_DECIMALS: Final = 4
# Lado de la cuadrícula a la que se ajustan las coordenadas públicas (ST_SnapToGrid).
PUBLIC_GRID_DEGREES: Final = 10.0**-PUBLIC_COORDINATE_DECIMALS
