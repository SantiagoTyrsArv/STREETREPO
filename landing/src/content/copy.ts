/**
 * Textos de la página (español de Colombia). Solo cifras reales del proyecto: la fórmula U y los
 * radios de 25 m y 500 m (guía 2.2 y 2.3). Nada de métricas de uso inventadas.
 */

export interface ChapterCopy {
  kicker: string;
  title: string;
  lead: string;
  /** Texto alternativo de la escena (ilustración generada). */
  alt: string;
}

export interface Factor {
  symbol: string;
  name: string;
  description: string;
}

export const COPY = {
  header: {
    download: "Descargar",
  },
  apertura: {
    kicker: "Pasto, Nariño",
    title: "Cada calle cuenta.",
    lead: "Street Repo convierte los daños de las vías de Pasto en información que se puede atender, en el orden correcto.",
    alt: "Ilustración: la ciudad de Pasto de noche con el volcán Galeras en el horizonte.",
  },
  problema: {
    kicker: "01 · El problema",
    title: "Los daños se reportan. Pocas veces se priorizan.",
    lead: "Sin un criterio común de urgencia, los reportes se duplican, nadie sabe cuál atender primero y quien reporta no vuelve a saber de su caso.",
    alt: "Ilustración: una calle de Pasto bajo la lluvia, con un bache que refleja la luz del alumbrado.",
  },
  reportar: {
    kicker: "02 · Reportar",
    title: "Una foto, una ubicación y la severidad.",
    lead: "La app toma la evidencia con la cámara y el GPS del celular. Si alguien ya reportó el mismo daño a menos de 25 m, te lo muestra para que lo confirmes en lugar de duplicarlo.",
    alt: "Pantallas reales de la app Street Repo: foto y ubicación, severidad, reporte enviado y mapa.",
  },
  priorizar: {
    kicker: "03 · Priorizar",
    title: "Un modelo transparente decide el orden.",
    lead: "Cada reporte recibe una urgencia de 0 a 10. Los pesos son públicos y la Secretaría de Infraestructura puede ajustarlos.",
    alt: "Ilustración: líneas de luz azul recorren las calles de la ciudad y convergen en puntos de prioridad.",
  },
  formula: "U = 0,5·S + 0,3·F + 0,2·P",
  factors: [
    {
      symbol: "S",
      name: "Severidad",
      description: "La que declara el ciudadano: baja, media o alta.",
    },
    {
      symbol: "F",
      name: "Flujo vehicular",
      description: "Según la jerarquía de la vía en OpenStreetMap.",
    },
    {
      symbol: "P",
      name: "Proximidad",
      description: "A hospitales y escuelas, hasta 500 m.",
    },
  ] satisfies readonly Factor[],
  panel: {
    kicker: "04 · Gestionar",
    title: "La ciudad, ordenada por urgencia.",
    lead: "El panel de la Secretaría muestra el mapa de calor y el ranking con el desglose de cada cálculo. Cada cambio de estado queda en el historial.",
    alt: "Captura real del panel administrativo: mapa de calor de Pasto y ranking de reportes, con datos de demostración.",
  },
  reparado: {
    kicker: "05 · Reparado",
    title: "Y quien reportó, lo ve.",
    lead: "Registrado, evaluado, priorizado, reparado: el ciudadano sigue el estado de su reporte desde la app.",
    alt: "Ilustración: la misma calle, ya reparada, al amanecer.",
  },
} as const satisfies Record<string, unknown>;

export type SequenceCopyKey = "apertura" | "problema" | "priorizar" | "reparado";

export const SEQUENCE_COPY: Record<SequenceCopyKey, ChapterCopy> = {
  apertura: COPY.apertura,
  problema: COPY.problema,
  priorizar: COPY.priorizar,
  reparado: COPY.reparado,
};
