/** Textos en español para valores que la API entrega tal como están en OSM o en la base. */

/** Cubre las etiquetas `highway` que carga la API (propuesta 7). */
const HIGHWAY_LABELS: Record<string, string> = {
  trunk: "troncal",
  trunk_link: "enlace de troncal",
  primary: "primaria",
  primary_link: "enlace de primaria",
  secondary: "secundaria",
  tertiary: "terciaria",
  residential: "residencial",
  unclassified: "sin clasificar",
  service: "de servicio",
  living_street: "de prioridad peatonal",
};

/** Jerarquía vial de OSM (`highway`); un valor no previsto se muestra tal cual. */
export function highwayLabel(highway: string): string {
  return HIGHWAY_LABELS[highway] ?? highway;
}

export function confirmationsSentence(count: number): string {
  if (count === 0) {
    return "Nadie ha confirmado este daño todavía";
  }
  const who = count === 1 ? "1 persona confirmó" : `${count} personas confirmaron`;
  return `${who} este daño (no modifica el puntaje)`;
}
