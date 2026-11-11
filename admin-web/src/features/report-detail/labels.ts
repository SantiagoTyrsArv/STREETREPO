/** Textos en español para valores que la API entrega tal como están en OSM o en la base. */

const HIGHWAY_LABELS: Record<string, string> = {
  primary: "primaria",
  secondary: "secundaria",
  tertiary: "terciaria",
  residential: "residencial",
  unclassified: "sin clasificar",
  service: "de servicio",
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
