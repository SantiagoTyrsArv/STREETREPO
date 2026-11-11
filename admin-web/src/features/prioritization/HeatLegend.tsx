/** Extremos de la escala de urgencia U (guía 2.2). */
const U_MIN = 0;
const U_MAX = 10;

/** Leyenda del mapa de calor: el color va acompañado de números (guía 10.3). */
export function HeatLegend() {
  return (
    <div className="heat-legend" role="group" aria-label="Escala de urgencia U">
      <span>{U_MIN} · Menor</span>
      <span className="heat-legend__scale" aria-hidden="true" />
      <span>{U_MAX} · Mayor urgencia</span>
    </div>
  );
}
