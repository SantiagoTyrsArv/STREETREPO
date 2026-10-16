from enum import StrEnum


class RoadClass(StrEnum):
    """Jerarquía vial. Valores del ENUM ``jerarquia_vial`` del diagrama ER.

    La correspondencia con la etiqueta ``highway`` de OSM se define en la carga
    de datos (fase 2).
    """

    PRIMARY = "primaria"
    SECONDARY = "secundaria"
    TERTIARY = "terciaria"
    RESIDENTIAL = "residencial"
