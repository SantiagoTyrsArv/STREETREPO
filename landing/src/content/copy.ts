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
  skipLink: "Saltar a la descarga",
  scrollCue: "Desliza",
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
    screens: [
      {
        src: "/media/app/captura-foto.webp",
        alt: "Captura real de la app, paso 1: foto del daño y ubicación por GPS sobre la vía.",
      },
      {
        src: "/media/app/captura-severidad.webp",
        alt: "Captura real de la app, paso 2: elegir la severidad (baja, media o alta) y describir el daño.",
      },
      {
        src: "/media/app/captura-enviado.webp",
        alt: "Captura real de la app: reporte registrado y ya evaluado por el modelo de prioridad.",
      },
      {
        src: "/media/app/captura-mapa.webp",
        alt: "Captura real de la app: mapa de reportes de Pasto con su estado, con datos de demostración.",
      },
    ],
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
  calculadora: {
    kicker: "04 · Pruébalo",
    title: "Calcula una urgencia.",
    lead: "Mueve los valores y mira cómo el modelo ordena un daño. Es la misma fórmula que usa el sistema.",
    severityLabel: "Severidad (S)",
    severities: [
      { value: "baja", label: "Baja" },
      { value: "media", label: "Media" },
      { value: "alta", label: "Alta" },
    ],
    roadLabel: "Tipo de vía (F)",
    roads: [
      { value: "principal", label: "Principal" },
      { value: "secundaria", label: "Secundaria" },
      { value: "terciaria", label: "Terciaria" },
      { value: "residencial", label: "Residencial o de servicio" },
      { value: "sin-via", label: "Sin vía a menos de 30 m" },
    ],
    distanceLabel: "Distancia a un hospital o una escuela (P)",
    resultLabel: "Urgencia",
    reviewRoad: "Revisar vía",
    note: "Con los pesos por defecto; la Secretaría de Infraestructura puede ajustarlos.",
  },
  panel: {
    kicker: "05 · Gestionar",
    title: "La ciudad, ordenada por urgencia.",
    lead: "El panel de la Secretaría muestra el mapa de calor y el ranking con el desglose de cada cálculo. Cada cambio de estado queda en el historial.",
    alt: "Captura real del panel administrativo: mapa de calor de Pasto y ranking de reportes, con datos de demostración.",
  },
  reparado: {
    kicker: "06 · Reparado",
    title: "Y quien reportó, lo ve.",
    lead: "Registrado, evaluado, priorizado, reparado: el ciudadano sigue el estado de su reporte desde la app.",
    alt: "Ilustración: la misma calle, ya reparada, al amanecer.",
  },
  descarga: {
    kicker: "07 · Descarga",
    title: "Lleva Street Repo en tu bolsillo.",
    lead: "La app ciudadana es para Android y se descargará desde esta página.",
    soon: "Próximamente",
    soonNote: "La app está en pruebas. Cuando la versión esté lista, la podrás descargar aquí.",
    cta: "Descargar Street Repo para Android",
    qrAlt: "Código QR con el enlace de descarga de la app",
    qrHint: "Escanéalo con la cámara del celular.",
    stepsLabel: "Pasos para instalar",
    steps: [
      "Si Android lo pide, permite instalar apps desconocidas desde tu navegador.",
      "Abre el archivo descargado.",
      "Toca «Instalar» y abre Street Repo.",
    ],
    checksumLabel: "Suma SHA-256",
  },
  footer: {
    project:
      "Proyecto de grado · Ingeniería de Software · Universidad Cooperativa de Colombia, campus Pasto",
    aiNotice: "Imágenes y videos ilustrativos generados con IA",
  },
} as const satisfies Record<string, unknown>;

export type SequenceCopyKey = "apertura" | "problema" | "priorizar" | "reparado";

export const SEQUENCE_COPY: Record<SequenceCopyKey, ChapterCopy> = {
  apertura: COPY.apertura,
  problema: COPY.problema,
  priorizar: COPY.priorizar,
  reparado: COPY.reparado,
};
